import argparse, json, os, random
import torch
from model.config import BLOCK_SIZE
from model.network import AKByteModel

def load_text(path):
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            chunks.append(f"User: {item['prompt']}\nAnkit Kryptex: {item['response']}\n\n")
    if not chunks:
        raise ValueError("Dataset is empty. Add prompt/response JSON lines to data/train.jsonl")
    # UTF-8 bytes: no external tokenizer or pretrained vocabulary.
    return torch.tensor(list("\n".join(chunks).encode("utf-8")), dtype=torch.long)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--data", default="data/train.jsonl")
    parser.add_argument("--save", default="model/weights.pt")
    args = parser.parse_args()

    random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    data = load_text(args.data)
    if len(data) < BLOCK_SIZE + 2:
        raise ValueError("Add more training text; dataset is too short.")

    model = AKByteModel()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    model.train()
    for step in range(1, args.steps + 1):
        starts = torch.randint(0, len(data) - BLOCK_SIZE - 1, (args.batch_size,))
        x = torch.stack([data[s:s + BLOCK_SIZE] for s in starts])
        y = torch.stack([data[s + 1:s + BLOCK_SIZE + 1] for s in starts])
        _, loss = model(x, y)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if step == 1 or step % 50 == 0 or step == args.steps:
            print(f"step {step}/{args.steps} loss={loss.item():.4f}", flush=True)

    os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "steps": args.steps, "format": "ak-byte-1"}, args.save)
    print(f"Saved freshly trained weights to {args.save}")

if __name__ == "__main__":
    main()
