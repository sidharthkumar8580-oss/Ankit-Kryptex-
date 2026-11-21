# AK Video-1 — scratch video-generation research prototype

This directory is a separate experimental video model. It does not use a pretrained checkpoint or a hosted video-generation API. All model parameters are randomly initialized.

## What this first milestone is
A small conditional video diffusion research baseline that learns to denoise short RGB clips from paired captions. It is intended to prove the data/training/inference pipeline, not to produce polished 15–30 second realistic videos. The starter configuration is deliberately tiny (16 frames at 64x64); quality will be limited.

## Data format
Put your own videos that you created or are licensed to use in `video_model/data/videos/`. Create `video_model/data/captions.csv` with columns:
`filename,caption`
Example:
`clip001.mp4,"A red bicycle moving along a quiet road"`

Do not use private footage, copyrighted clips without permission, or personal data. Keep a held-out validation set separate. The loader samples and resizes short clips; every training clip must have a caption.

## Install and train
Use a GPU runtime (for example, a Colab GPU you explicitly start). A CPU or a free web-service instance is not a practical training environment.

```bash
pip install -r video_model/requirements.txt
python -m video_model.train --data video_model/data --steps 10000 --save video_model/checkpoints/ak-video-1.pt
```

Training saves checkpoints periodically and can resume with `--resume`. The default configuration is for experimentation; adjust batch size downward if GPU memory is insufficient.

## Generate a test clip
```bash
python -m video_model.generate --checkpoint video_model/checkpoints/ak-video-1.pt --prompt "A small sailboat on a calm lake at sunrise" --output sample.mp4
```

Generation requires a trained checkpoint. The script refuses to pretend that an untrained random model is a working video generator.

## Honest limitations / next milestones
- This is a low-resolution, short-clip proof of concept, not a Sora/Grok-class model.
- It does not yet generate speech, music, or sound effects. A separate scratch-trained audio model and audio/video synchronization stage are required for the requested 15–30 second audiovisual system.
- Training from zero requires a large, diverse, licensed captioned video corpus and substantial GPU time. A tiny dataset will overfit and will not produce realistic general-purpose video.
- Do not claim a model is trained until a checkpoint exists and held-out prompt tests have been reviewed.
