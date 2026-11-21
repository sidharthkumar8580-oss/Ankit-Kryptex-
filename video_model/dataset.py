import os, random
import cv2
import pandas as pd
import torch
from torch.utils.data import Dataset
from .config import NUM_FRAMES, IMAGE_SIZE, TEXT_LENGTH
from .model import encode_caption

class CaptionedClips(Dataset):
    def __init__(self, root, split="train", val_fraction=0.05):
        self.root = root
        csv_path = os.path.join(root, "captions.csv")
        if not os.path.isfile(csv_path):
            raise FileNotFoundError(f"Missing {csv_path}; create filename,caption columns.")
        df = pd.read_csv(csv_path).dropna(subset=["filename","caption"])
        rows = df.to_dict("records")
        random.Random(1234).shuffle(rows)
        nval = max(1, int(len(rows)*val_fraction)) if len(rows)>1 else 0
        self.rows = rows[nval:] if split=="train" else rows[:nval]
        if not self.rows:
            raise ValueError("No clips in this split. Add more captioned video files.")
    def __len__(self): return len(self.rows)
    def __getitem__(self, idx):
        row = self.rows[idx]
        path = os.path.join(self.root, "videos", str(row["filename"]))
        cap = cv2.VideoCapture(path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if not cap.isOpened() or total < 1:
            cap.release()
            raise RuntimeError(f"Cannot read video: {path}")
        start = random.randint(0, max(0, total-NUM_FRAMES))
        indices = [min(start+i, total-1) for i in range(NUM_FRAMES)]
        frames=[]
        for frame_idx in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ok, frame = cap.read()
            if not ok:
                cap.release()
                raise RuntimeError(f"Bad frame {frame_idx} in {path}")
            frame=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame=cv2.resize(frame,(IMAGE_SIZE,IMAGE_SIZE),interpolation=cv2.INTER_AREA)
            frames.append(torch.from_numpy(frame.copy()).permute(2,0,1).float()/127.5-1.0)
        cap.release()
        video=torch.stack(frames,dim=1) # C,T,H,W
        tokens=torch.tensor(encode_caption(str(row["caption"])),dtype=torch.long)
        return video,tokens
