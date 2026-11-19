# Ankit Kryptex AI — AK-Byte-1

An original educational decoder-only Transformer initialized from random weights and trained from scratch. It does not call hosted language-model inference APIs and does not download pretrained weights.

## Current free-CPU profile

- Architecture: decoder-only Transformer
- Tokenizer: byte-level (256 possible byte values)
- Context length: 256 bytes
- Hidden dimensions: 384
- Attention heads: 8 (48 dimensions per head)
- Transformer blocks: 6
- Approximate parameter count: about 11 million (implementation-dependent exact count)
- Initialization: random weights
- Training: 1,000 supervised steps by default, batch size 4, learning rate 0.0002
- Runner: GitHub-hosted Ubuntu CPU, with a 6-hour job timeout

This is a larger experimental profile chosen to stay within a modest free CPU budget. GitHub controls runner availability and account usage limits; a run can still be queued, stopped, or exceed practical time. It is not comparable to ChatGPT.

## Training

A push to the configured training files starts the workflow automatically. To inspect progress, open the repository Actions tab and select **Train AK-Byte-1 from scratch**. On success, the workflow commits `model/weights.pt`. Restart/redeploy the API after new weights are committed.

## Dataset quality

The current `data/train.jsonl` is only a small starter dataset, not one million examples. No duplicate or fabricated rows are added to inflate its size. Add original or properly licensed, reviewed prompt/response pairs, one JSON object per line:

```json
{"prompt":"Your question","response":"Your answer"}
```

Do not include passwords, API keys, private messages, or personal data. A larger model cannot learn broad knowledge from a tiny dataset; high-quality data matters more than an inflated row count.

## API

The FastAPI server exposes `POST /api/chat`. Example body:

```json
{"message":"Namaste","max_new_tokens":80}
```

Install with `pip install -r requirements.txt` and run `uvicorn api:app --host 0.0.0.0 --port 8000`.

## Limitations

AK-Byte-1 is a small learning experiment. Byte-level tokenization and the tiny starter dataset mean replies may be weak, repetitive, or incorrect. Free CPU training is not continuous background training and does not guarantee a successful run.
