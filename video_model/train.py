import argparse, os, random
import torch
from torch.utils.data import DataLoader
from tqdm import tqdm
from .dataset import CaptionedClips
from .model import AKVideoDenoiser
from .config import NUM_FRAMES, IMAGE_SIZE

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",default="video_model/data")
    p.add_argument("--steps",type=int,default=10000)
    p.add_argument("--batch-size",type=int,default=1)
    p.add_argument("--lr",type=float,default=1e-4)
    p.add_argument("--save",default="video_model/checkpoints/ak-video-1.pt")
    p.add_argument("--save-every",type=int,default=500)
    p.add_argument("--resume",action="store_true")
    a=p.parse_args()
    if a.steps<1 or a.batch_size<1: raise ValueError("steps and batch-size must be positive")
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:",device, torch.cuda.get_device_name(0) if device.type=="cuda" else "(CPU; very slow)",flush=True)
    ds=CaptionedClips(a.data,"train")
    loader=DataLoader(ds,batch_size=a.batch_size,shuffle=True,num_workers=2,pin_memory=device.type=="cuda")
    model=AKVideoDenoiser().to(device)
    optimizer=torch.optim.AdamW(model.parameters(),lr=a.lr,weight_decay=0.01)
    start=0
    if a.resume and os.path.exists(a.save):
        ck=torch.load(a.save,map_location=device,weights_only=False)
        model.load_state_dict(ck["model"]); optimizer.load_state_dict(ck["optimizer"]); start=ck["step"]
        print("Resumed step",start,flush=True)
    steps_per_epoch=len(loader); iterator=iter(loader); model.train()
    for step in range(start+1,a.steps+1):
        try: clean,tokens=next(iterator)
        except StopIteration: iterator=iter(loader); clean,tokens=next(iterator)
        clean,tokens=clean.to(device),tokens.to(device)
        t=torch.randint(0,1000,(clean.shape[0],),device=device)
        alpha=torch.linspace(0.9999,0.0001,1000,device=device)
        abar=torch.cumprod(alpha,dim=0)
        noise=torch.randn_like(clean)
        a_t=abar[t].view(-1,1,1,1,1)
        noisy=a_t.sqrt()*clean+(1-a_t).sqrt()*noise
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type="cuda",dtype=torch.float16,enabled=device.type=="cuda"):
            pred=model(noisy,t,tokens)
            loss=torch.nn.functional.mse_loss(pred,noise)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(),1.0)
        optimizer.step()
        if step==1 or step%25==0: print(f"step={step}/{a.steps} loss={loss.item():.5f}",flush=True)
        if step%a.save_every==0 or step==a.steps:
            os.makedirs(os.path.dirname(a.save) or ".",exist_ok=True)
            tmp=a.save+".tmp"
            torch.save({"model":model.state_dict(),"optimizer":optimizer.state_dict(),"step":step,
                        "frames":NUM_FRAMES,"size":IMAGE_SIZE,"format":"ak-video-1-scratch-v0"},tmp)
            os.replace(tmp,a.save)
            print("Saved",a.save,flush=True)
    print("Training run finished. Evaluate on unseen captions before calling it usable.",flush=True)

if __name__=="__main__": main()
