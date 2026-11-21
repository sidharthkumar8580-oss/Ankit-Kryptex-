import torch
from torch import nn
from torch.nn import functional as F
from .config import NUM_FRAMES, IMAGE_SIZE, TEXT_VOCAB, TEXT_LENGTH, BASE_CHANNELS

def timestep_embedding(t, dim):
    half = dim // 2
    freqs = torch.exp(-torch.arange(half, device=t.device) * (torch.log(torch.tensor(10000.0, device=t.device)) / max(half - 1, 1)))
    args = t.float()[:, None] * freqs[None]
    emb = torch.cat([torch.sin(args), torch.cos(args)], dim=-1)
    return F.pad(emb, (0, dim - emb.shape[-1]))

class ResBlock3D(nn.Module):
    def __init__(self, cin, cout, cond_dim):
        super().__init__()
        self.norm1 = nn.GroupNorm(8, cin)
        self.conv1 = nn.Conv3d(cin, cout, 3, padding=1)
        self.norm2 = nn.GroupNorm(8, cout)
        self.conv2 = nn.Conv3d(cout, cout, 3, padding=1)
        self.skip = nn.Conv3d(cin, cout, 1) if cin != cout else nn.Identity()
        self.cond = nn.Linear(cond_dim, cout)
    def forward(self, x, cond):
        h = self.conv1(F.silu(self.norm1(x)))
        h = h + self.cond(cond)[:, :, None, None, None]
        h = self.conv2(F.silu(self.norm2(h)))
        return self.skip(x) + h

class AKVideoDenoiser(nn.Module):
    """Tiny text-conditioned 3D diffusion denoiser, initialized from scratch."""
    def __init__(self, base=BASE_CHANNELS):
        super().__init__()
        self.text_embedding = nn.Embedding(TEXT_VOCAB, 128, padding_idx=0)
        self.text_proj = nn.Sequential(nn.Linear(128, 256), nn.SiLU(), nn.Linear(256, 256))
        self.time_proj = nn.Sequential(nn.Linear(256, 256), nn.SiLU(), nn.Linear(256, 256))
        self.in_conv = nn.Conv3d(3, base, 3, padding=1)
        self.down = ResBlock3D(base, base*2, 256)
        self.mid1 = ResBlock3D(base*2, base*2, 256)
        self.mid2 = ResBlock3D(base*2, base*2, 256)
        self.up = ResBlock3D(base*2 + base, base, 256)
        self.out_norm = nn.GroupNorm(8, base)
        self.out = nn.Conv3d(base, 3, 3, padding=1)
        self.pool = nn.AvgPool3d((1,2,2))
        self.upsample = nn.Upsample(scale_factor=(1,2,2), mode="trilinear", align_corners=False)
    def forward(self, noisy, timesteps, tokens):
        txt = self.text_embedding(tokens).mean(dim=1)
        temb = timestep_embedding(timesteps, 256)
        cond = self.text_proj(txt) + self.time_proj(temb)
        x0 = self.in_conv(noisy)
        x = self.down(self.pool(x0), cond)
        x = self.mid1(x, cond)
        x = self.mid2(x, cond)
        x = self.upsample(x)
        x = self.up(torch.cat([x, x0], dim=1), cond)
        return self.out(F.silu(self.out_norm(x)))

def encode_caption(text, length=TEXT_LENGTH):
    raw = text.lower().encode("utf-8")[:length]
    ids = [b + 1 for b in raw]
    return ids + [0] * (length - len(ids))
