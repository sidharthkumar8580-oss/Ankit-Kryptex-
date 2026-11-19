import argparse
import json
import os
import random
import torch
from model.config import BLOCK_SIZE
from model.network import AKByteModel

def load_examples(path):
    rows=[]
    with open(path,encoding="utf-8") as f:
        for n,line in enumerate(f,1):
            if not line.strip(): continue
            item=json.loads(line)
            prompt=("User: "+str(item["prompt"]).strip()+"\nAnkit Kryptex: ").encode("utf-8")
            answer=(str(item["response"]).strip()+"\n\n").encode("utf-8")
            if len(prompt)>=BLOCK_SIZE-2: continue
            answer=answer[:BLOCK_SIZE-len(prompt)]
            seq=torch.tensor(list(prompt+answer),dtype=torch.long)
            if len(seq)>len(prompt)+1: rows.append((seq,len(prompt)))
    if len(rows)<2: raise ValueError("Need at least two usable prompt/response examples.")
    return rows

def make_batch(rows,batch_size,device):
    chosen=random.choices(rows,k=batch_size)
    x=torch.zeros((batch_size,BLOCK_SIZE),dtype=torch.long)
    y=torch.full((batch_size,BLOCK_SIZE),-100,dtype=torch.long)
    for i,(seq,prompt_len) in enumerate(chosen):
        inp, tgt=seq[:-1],seq[1:]
        n=min(len(inp),BLOCK_SIZE)
        x[i,:n]=inp[:n]
        start=max(0,prompt_len-1)
        end=min(len(tgt),BLOCK_SIZE)
        if start<end: y[i,start:end]=tgt[start:end]
    return x.to(device),y.to(device)

@torch.no_grad()
def evaluate(model,rows,batch_size,device,batches=12):
    model.eval(); vals=[]
    for _ in range(batches):
        x,y=make_batch(rows,batch_size,device)
        with torch.autocast(device_type="cuda",dtype=torch.float16,enabled=device.type=="cuda"):
            _,loss=model(x,y)
        if loss is not None: vals.append(loss.item())
    model.train()
    return sum(vals)/max(1,len(vals))

def save_checkpoint(path,model,optimizer,step,best_val,examples):
    os.makedirs(os.path.dirname(path) or ".",exist_ok=True)
    tmp=path+".tmp"
    torch.save({"state_dict":model.state_dict(),"optimizer":optimizer.state_dict(),
                "step":step,"best_val_loss":best_val,"examples":examples,
                "context_length":BLOCK_SIZE,"format":"ak-byte-1-scratch-v3"},tmp)
    os.replace(tmp,path)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--steps",type=int,default=20000)
    p.add_argument("--batch-size",type=int,default=4)
    p.add_argument("--grad-accum",type=int,default=4)
    p.add_argument("--lr",type=float,default=2e-4)
    p.add_argument("--data",default="data/train.jsonl")
    p.add_argument("--save",default="model/weights.pt")
    p.add_argument("--save-every",type=int,default=500)
    p.add_argument("--eval-every",type=int,default=500)
    p.add_argument("--resume",action="store_true")
    a=p.parse_args()
    random.seed(42); torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)
        torch.backends.cuda.matmul.allow_tf32=True
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:",device,torch.cuda.get_device_name(0) if device.type=="cuda" else "",flush=True)
    rows=load_examples(a.data)
    random.Random(42).shuffle(rows)
    cut=max(1,int(len(rows)*0.9))
    train_rows,val_rows=rows[:cut],rows[cut:]
    if not val_rows: val_rows=train_rows
    print(f"Examples: {len(rows)} | train: {len(train_rows)} | validation: {len(val_rows)} | parameters: ",end="",flush=True)
    model=AKByteModel().to(device)
    print(f"{sum(p.numel() for p in model.parameters()):,}",flush=True)
    optimizer=torch.optim.AdamW(model.parameters(),lr=a.lr,weight_decay=0.1,betas=(0.9,0.95))
    start=0; best=float("inf")
    if a.resume and os.path.exists(a.save):
        ck=torch.load(a.save,map_location=device,weights_only=False)
        model.load_state_dict(ck["state_dict"])
        if "optimizer" in ck: optimizer.load_state_dict(ck["optimizer"])
        start=int(ck.get("step",0)); best=float(ck.get("best_val_loss",best))
        print("Resumed from step",start,flush=True)
    scaler=torch.amp.GradScaler("cuda",enabled=device.type=="cuda")
    model.train(); optimizer.zero_grad(set_to_none=True)
    for step in range(start+1,a.steps+1):
        total=0.0
        for _ in range(a.grad_accum):
            x,y=make_batch(train_rows,a.batch_size,device)
            with torch.autocast(device_type="cuda",dtype=torch.float16,enabled=device.type=="cuda"):
                _,loss=model(x,y)
                loss=loss/a.grad_accum
            scaler.scale(loss).backward()
            total+=loss.item()
        scaler.unscale_(optimizer)
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0)
        scaler.step(optimizer); scaler.update(); optimizer.zero_grad(set_to_none=True)
        if step==1 or step%50==0:
            print(f"step {step}/{a.steps} train_loss={total:.4f}",flush=True)
        if step%a.eval_every==0 or step==a.steps:
            val=evaluate(model,val_rows,a.batch_size,device)
            print(f"VALIDATION step={step} val_loss={val:.4f}",flush=True)
            if val<best: best=val
        if step%a.save_every==0 or step==a.steps:
            save_checkpoint(a.save,model,optimizer,step,best,len(rows))
            print("Checkpoint saved:",a.save,flush=True)
    print("Training finished. Final step:",step,"best validation loss:",best,flush=True)

if __name__=="__main__": main()
