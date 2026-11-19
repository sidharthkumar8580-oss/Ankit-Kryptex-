# Ankit Kryptex AI — AK-Byte-1

A tiny language model project built from **randomly initialized weights**. It does not call OpenAI, Gemini, Groq, Hugging Face inference, or any other model API, and it does not download pretrained model weights.

## What is included
- A small decoder-only Transformer written in PyTorch.
- A byte-level tokenizer written for this project (all 256 byte values).
- A small, editable Hinglish/English starter dataset in `data/train.jsonl`.
- A training script that initializes the model from scratch.
- A FastAPI server exposing your own `POST /api/chat` endpoint.
- A simple mobile-friendly chat page.
- A manual GitHub Actions workflow that trains on a free GitHub-hosted CPU runner and commits the resulting weights back to this repository.

## Important reality check
This is an educational **tiny language model**, not a ChatGPT-sized model. The starter dataset is small, so early answers will be weak, repetitive, or incorrect. It must be trained on a much larger, legally usable dataset to become more useful. Training from scratch on a phone is not realistic; the included workflow is the intended free starting point. GitHub Actions availability and usage limits are controlled by GitHub.

## Train your own weights
1. Open the repository's **Actions** tab.
2. Select **Train AK-Byte-1 from scratch**.
3. Press **Run workflow**. The default is 300 training steps.
4. When it finishes, the workflow commits `model/weights.pt` to `main`.
5. The API will load those weights when the server starts.

The workflow uses only the code and dataset in this repository. It creates fresh random weights and trains them; no pretrained weights are downloaded.

## Run the API
Python 3.11 is recommended.

```bash
pip install -r requirements.txt
python train.py --steps 300
uvicorn api:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`. The API endpoint is `POST /api/chat` with JSON `{"message":"Namaste","max_new_tokens":80}`.

## Hosting
`render.yaml` is a deployment recipe for a Python web service. A free hosting tier may sleep, have limited RAM/CPU, or change its terms. Deployment is not automatic from this repository and no live public API is claimed until it is actually deployed and tested. The trained `model/weights.pt` file must be present in the deployed source.

## Add training data
Add one JSON object per line to `data/train.jsonl`:
`{"prompt":"your question","response":"your answer"}`
Use text you own or are allowed to use. Do not put passwords, API keys, private messages, or personal data in the dataset.

## Project identity
**Ankit Kryptex AI | AK-Byte-1** — built as an original from-scratch learning project.
