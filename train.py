import argparse
import json
import os
import random

import torch

from model.config import BLOCK_SIZE
from model.network import AKByteModel


def load_examples(path):
    examples = []
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            item = json.loads(line)
            prompt = ("User: " + item["prompt"].strip() + "\\nAnkit Kryptex: ").encode("utf-8")
            answer = (item["response"].strip() + "\\n\\n").encode("utf-8")
            # Preserve the question and train the answer continuation.
            answer = answer[: max(1, BLOCK_SIZE - len(prompt))]
            sequence = torch.tensor(list(prompt + answer), dtype=torch.long)
            prompt_length = min(len(prompt), len(sequence) - 1)
            if len(sequence) >= 3 and prompt_length < len(sequence) - 1:
                examples.append((sequence, prompt_length))
    if not examples:
        raise ValueError("No usable prompt/response examples found.")
    return examples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=60000)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--data", default="data/train.jsonl")
    parser.add_argument("--save", default="model/weights.pt")
    args = parser.parse_args()

    random.seed(42)
    torch.manual_seed(42)
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    examples = load_examples(args.data)
    print(f"Loaded {len(examples)} supervised examples; context={BLOCK_SIZE}", flush=True)

    model = AKByteModel()
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    model.train()
    running_loss = 0.0

    for step in range(1, args.steps + 1):
        chosen = random.choices(examples, k=args.batch_size)
        x = torch.zeros((args.batch_size, BLOCK_SIZE), dtype=torch.long)
        y = torch.full((args.batch_size, BLOCK_SIZE), -100, dtype=torch.long)
        for row, (sequence, prompt_length) in enumerate(chosen):
            inputs = sequence[:-1]
            targets = sequence[1:]
            length = min(len(inputs), BLOCK_SIZE)
            x[row, :length] = inputs[:length]
            # Ignore prompt tokens: optimize the answer continuation directly.
            first_answer_target = max(0, prompt_length - 1)
            if first_answer_target < min(len(targets), BLOCK_SIZE):
                y[row, first_answer_target:min(len(targets), BLOCK_SIZE)] = targets[first_answer_target:min(len(targets), BLOCK_SIZE)]

        _, loss = model(x, y)
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        running_loss += float(loss.item())

        if step == 1 or step % 500 == 0 or step == args.steps:
            average = running_loss / (1 if step == 1 else min(500, step))
            print(f"step {step}/{args.steps} loss={loss.item():.4f} avg_loss={average:.4f}", flush=True)
            running_loss = 0.0

    os.makedirs(os.path.dirname(args.save) or ".", exist_ok=True)
    torch.save({
        "state_dict": model.state_dict(),
        "steps": args.steps,
        "examples": len(examples),
        "context_length": BLOCK_SIZE,
        "format": "ak-byte-1-sft-v2",
    }, args.save)
    print(f"Saved {args.steps} freshly trained steps to {args.save}", flush=True)


if __name__ == "__main__":
    main()
