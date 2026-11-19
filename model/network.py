import torch
from torch import nn
from torch.nn import functional as F
from .config import VOCAB_SIZE, BLOCK_SIZE, D_MODEL, N_HEADS, N_LAYERS, DROPOUT

class CausalSelfAttention(nn.Module):
    def __init__(self):
        super().__init__()
        assert D_MODEL % N_HEADS == 0
        self.head_size = D_MODEL // N_HEADS
        self.qkv = nn.Linear(D_MODEL, 3 * D_MODEL)
        self.proj = nn.Linear(D_MODEL, D_MODEL)
        self.dropout = nn.Dropout(DROPOUT)
        self.register_buffer("mask", torch.triu(torch.ones(BLOCK_SIZE, BLOCK_SIZE, dtype=torch.bool), diagonal=1))

    def forward(self, x):
        batch, length, channels = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        def split(t):
            return t.view(batch, length, N_HEADS, self.head_size).transpose(1, 2)
        q, k, v = split(q), split(k), split(v)
        scores = (q @ k.transpose(-2, -1)) * (self.head_size ** -0.5)
        scores = scores.masked_fill(self.mask[:length, :length], float("-inf"))
        weights = self.dropout(F.softmax(scores, dim=-1))
        out = weights @ v
        out = out.transpose(1, 2).contiguous().view(batch, length, channels)
        return self.dropout(self.proj(out))

class Block(nn.Module):
    def __init__(self):
        super().__init__()
        self.ln1 = nn.LayerNorm(D_MODEL)
        self.attn = CausalSelfAttention()
        self.ln2 = nn.LayerNorm(D_MODEL)
        self.ff = nn.Sequential(
            nn.Linear(D_MODEL, 4 * D_MODEL), nn.GELU(),
            nn.Linear(4 * D_MODEL, D_MODEL), nn.Dropout(DROPOUT)
        )

    def forward(self, x):
        x = x + self.attn(self.ln1(x))
        return x + self.ff(self.ln2(x))

class AKByteModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.token_embedding = nn.Embedding(VOCAB_SIZE, D_MODEL)
        self.position_embedding = nn.Embedding(BLOCK_SIZE, D_MODEL)
        self.blocks = nn.Sequential(*[Block() for _ in range(N_LAYERS)])
        self.ln_f = nn.LayerNorm(D_MODEL)
        self.lm_head = nn.Linear(D_MODEL, VOCAB_SIZE, bias=False)
        self.lm_head.weight = self.token_embedding.weight
        self.apply(self._init_weights)

    @staticmethod
    def _init_weights(module):
        if isinstance(module, nn.Linear):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)
            if module.bias is not None:
                nn.init.zeros_(module.bias)
        elif isinstance(module, nn.Embedding):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(self, idx, targets=None):
        _, length = idx.shape
        positions = torch.arange(length, device=idx.device)
        x = self.token_embedding(idx) + self.position_embedding(positions)[None, :, :]
        x = self.blocks(x)
        logits = self.lm_head(self.ln_f(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.reshape(-1, VOCAB_SIZE), targets.reshape(-1))
        return logits, loss

    @torch.no_grad()
    def generate(self, idx, max_new_tokens=80, temperature=0.85, top_k=30):
        self.eval()
        for _ in range(max_new_tokens):
            context = idx[:, -BLOCK_SIZE:]
            logits, _ = self(context)
            logits = logits[:, -1, :] / max(temperature, 0.05)
            k = min(top_k, logits.size(-1))
            values, _ = torch.topk(logits, k)
            logits[logits < values[:, [-1]]] = -float("inf")
            probs = F.softmax(logits, dim=-1)
            next_token = torch.multinomial(probs, num_samples=1)
            idx = torch.cat((idx, next_token), dim=1)
        return idx
