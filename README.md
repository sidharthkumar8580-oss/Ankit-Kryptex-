# Ankit Kryptex AI — AK-Byte-1

AK-Byte-1 is being upgraded from a tiny randomly initialized Transformer to a pretrained instruction model fine-tuned with QLoRA.

## Selected base model

- Base: [Qwen/Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)
- Parameters: approximately 0.49 billion
- License: Apache-2.0 (retain upstream license and attribution)
- Fine-tuning: 4-bit QLoRA on a Colab GPU
- Adapter output: Google Drive folder `MyDrive/AK-Byte-1-Qwen-QLoRA/adapter`

The base model already has instruction-following and multilingual abilities. Fine-tuning adapts it to Ankit Kryptex's preferred behavior and reviewed examples. This is not a ChatGPT-scale model and does not guarantee ChatGPT-level quality.

## Training notebook

Open the updated Colab notebook:

`AK-Byte-1_GPU_Training.ipynb`

It installs the training dependencies, loads the 4-bit base model, tokenizes `data/train.jsonl`, splits training/validation data, trains a LoRA adapter, evaluates it, saves the adapter to Google Drive, and tests a simple greeting.

The notebook requires a Colab GPU. Free GPU availability and session duration are controlled by Colab. The assistant cannot start or monitor a training session inside the user's logged-in Colab account.

## Dataset quality

The repository currently contains 1,000 JSONL rows, but only 378 distinct response texts. It is a small starter dataset, not one million high-quality examples. Repeating or fabricating rows will not create intelligence. Add original, varied, reviewed, properly licensed prompt/response examples; do not add private messages, passwords, API keys, or personal data.

## Current API status — important

The existing Render API code still loads the old custom AK-Byte-1 scratch model from `model/weights.pt`. It has **not yet been switched** to the new Qwen base model plus fine-tuned adapter. The QLoRA notebook only creates the adapter in Google Drive; it does not automatically update the Render deployment.

A 0.5B model may exceed the memory available on a free 512 MB web service. Before changing the live API, select an inference format and hosting plan that can actually hold the model. Do not claim the live API is using Qwen until that deployment is completed and tested.

## Original scratch model

The repository's earlier `model/network.py`, `model/config.py`, and `train.py` remain as the original educational scratch-training experiment. They are not the new QLoRA training path.
