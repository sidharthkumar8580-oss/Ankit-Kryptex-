# Ankit Kryptex AI — AK-Byte-1

An original educational language-model project with a small decoder-only Transformer initialized from random weights. It does not call OpenAI, Gemini, Groq, Hugging Face inference, or another hosted language-model API, and it does not download pretrained weights.

## Current model configuration

- Architecture: decoder-only Transformer
- Tokenizer: byte-level (256 possible byte values)
- Context length: 256 bytes
- Hidden dimensions: 256
- Attention heads: 8
- Transformer blocks: 4
- Initialization: random weights, trained from scratch
- Training data: the examples currently present in `data/train.jsonl`

This is deliberately a small configuration intended as a realistic starting point for a free CPU runner. It is **not** an 18-layer, 2016-dimension model and is not comparable to ChatGPT. Increasing model size without suitable compute and a large high-quality dataset would make training impractical, not automatically make answers smarter.

## Training

1. Open the repository's **Actions** tab.
2. Select **Train AK-Byte-1 from scratch**.
3. Press **Run workflow** (default: 2,000 training steps).
4. When the job completes successfully, it commits `model/weights.pt`.
5. Restart/redeploy the API so it loads the newly trained weights.

A push that changes the configured training files can also start the workflow automatically. GitHub controls runner availability, execution time, and usage limits.

## Dataset quality

The current dataset is a small starter set, not one million examples. No fake or repeated records are added to claim a larger dataset. Add only original or properly licensed prompt/response pairs to `data/train.jsonl`, one JSON object per line:

```json
{"prompt":"Your question","response":"Your answer"}
```

A useful model needs a much larger, carefully reviewed, diverse dataset. More rows alone do not guarantee quality; duplicates, low-quality answers, and contradictory examples can make it worse. Do not add passwords, API keys, private messages, or personal data.

## API

The project includes a FastAPI server exposing `POST /api/chat`. Example request:

```json
{"message":"Namaste","max_new_tokens":80}
```

Install dependencies with `pip install -r requirements.txt` and run `uvicorn api:app --host 0.0.0.0 --port 8000`.

## Limitations

This is a learning experiment. Expect weak, repetitive, or incorrect answers, especially with a small dataset and byte-level tokenization. Training from scratch on an Android phone is not realistic. The included GitHub Actions workflow is a limited free starting point, not a guarantee of successful or continuous training.
