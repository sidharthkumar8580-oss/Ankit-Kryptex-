# Ankit Kryptex AI — AK-Byte-1 (scratch model)

AK-Byte-1 is an experimental language model trained from random initialization. The project does **not** load Qwen, Llama, GPT, Gemini, pretrained checkpoints, or a third-party model-generation API.

## Architecture
- Custom byte-level Transformer: 12 blocks, hidden size 512, 8 attention heads, 256-byte context.
- Vocabulary: 256 UTF-8 byte values.
- Approximate parameter count: about 40 million (verify printed count during training).
- Randomly initialized weights; trained with next-token supervised learning on the repository's prompt/response dataset.
- FastAPI inference service is separate from the model architecture.

## Train on Google Colab
Open `AK-Byte-1_GPU_Training.ipynb` in Colab, choose a GPU runtime, and run the cells. The notebook:
1. Clones/pulls this repository.
2. Checks for a GPU.
3. Trains the scratch model with mixed precision and gradient accumulation.
4. Evaluates validation loss periodically.
5. Saves resumable checkpoints to Google Drive every 500 steps.
6. Resumes from the last checkpoint after a runtime interruption.

The configured run is up to 20,000 optimizer steps, not a guarantee that free Colab will finish it in one session. Google states free GPU availability and usage limits vary; free sessions run for at most 12 hours and may end sooner. See the [official Colab FAQ](https://research.google.com/colaboratory/faq.html).

## Dataset reality
The current dataset is only a starter collection (about 1,000 rows and 378 distinct response texts based on the earlier audit). It is not a million high-quality examples. Repeating rows does not add knowledge. For a stronger model, add many diverse, accurate, original or properly licensed Hindi/Hinglish/English examples, then evaluate on a separate held-out test set. Never add private messages, passwords, API keys, or personal data.

## Internet research capability
Training a model does not automatically give it live internet access or current knowledge. A separate retrieval/search component must fetch web pages, extract relevant passages, and provide source links; the model then needs to synthesize those passages. That capability is not yet implemented in this scratch-training notebook or API. Do not claim AK-Byte-1 can browse the live web until a retrieval feature is built and tested.

## API / deployment status
`api.py` loads `model/weights.pt` on CPU and returns a 503 response when compatible trained weights are absent. The Colab notebook saves the checkpoint to Google Drive; it does not automatically publish it to GitHub or deploy it to Render. A roughly 40M-parameter FP32 checkpoint is around 160 MB before runtime overhead, so a free 512 MB Render service may not have enough memory. Verify hosting capacity and the exact checkpoint before claiming the live API is trained.

## Honest limitations
This is a learning-scale scratch model, not a ChatGPT-scale model. Byte-level tokenization is inefficient for Hindi and English compared with a carefully trained subword tokenizer. With the current small dataset, fluent open-ended conversation and reliable factual answers are not expected yet. Loss going down alone does not prove good answers; evaluate on unseen prompts and verify factual claims.
