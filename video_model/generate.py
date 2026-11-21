import argparse, torch, cv2, numpy as np
from .model import AKVideoDenoiser, encode_caption
from .config import NUM_FRAMES, IMAGE_SIZE

@torch.no_grad()
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--checkpoint",required=True)
    p.add_argument("--prompt",required=True)
    p.add_argument("--output",default="generated.mp4")
    p.add_argument("--steps",type=int,default=50)
    p.add_argument("--fps",type=int,default=8)
    a=p.parse_args()
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ck=torch.load(a.checkpoint,map_location=device,weights_only=False)
    if ck.get("format")!="ak-video-1-scratch-v0": raise ValueError("Checkpoint is not an AK Video-1 scratch checkpoint.")
    model=AKVideoDenoiser().to(device); model.load_state_dict(ck["model"]); model.eval()
    tokens=torch.tensor([encode_caption(a.prompt)],device=device)
    x=torch.randn(1,3,NUM_FRAMES,IMAGE_SIZE,IMAGE_SIZE,device=device)
    # DDIM-style deterministic reverse update for this baseline.
    schedule=torch.linspace(999,0,a.steps,device=device).long()
    betas=torch.linspace(0.0001,0.02,1000,device=device)
    alphas=1-betas; abar=torch.cumprod(alphas,dim=0)
    for i,tv in enumerate(schedule):
        t=torch.full((1,),int(tv.item()),device=device,dtype=torch.long)
        eps=model(x,t,tokens)
        at=abar[tv]
        x0=(x-(1-at).sqrt()*eps)/at.sqrt()
        if i+1<len(schedule):
            an=abar[schedule[i+1]]
            x=an.sqrt()*x0+(1-an).sqrt()*eps
        else: x=x0
    frames=((x[0].clamp(-1,1).permute(1,2,3,0).cpu().numpy()+1)*127.5).astype(np.uint8)
    writer=cv2.VideoWriter(a.output,cv2.VideoWriter_fourcc(*"mp4v"),a.fps,(IMAGE_SIZE,IMAGE_SIZE))
    for frame in frames: writer.write(cv2.cvtColor(frame,cv2.COLOR_RGB2BGR))
    writer.release()
    print("Wrote",a.output,"(silent video; no trained speech/audio model is included yet)")
if __name__=="__main__": main()
