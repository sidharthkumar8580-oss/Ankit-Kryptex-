# Ankit Kryptex AI Studio

Ankit Kryptex is a web-based image and video generation interface powered by the Agnes API.

## Features
- Image generation through Agnes Image.
- Video generation through Agnes Video, including text-to-video and reference-image-to-video requests.
- Image/video history stored locally in the browser.
- FastAPI backend with the Agnes API key kept in the hosting environment, not in frontend code.

## Run locally
1. Install dependencies: `pip install -r requirements.txt`
2. Set the environment variable `AGNES_API_KEY`.
3. Optionally set `AGNES_BASE_URL` (defaults to `https://apihub.agnes-ai.com`).
4. Start the server: `uvicorn api:app --host 0.0.0.0 --port 8000`
5. Open the server root in a browser.

## Deploy on Render
Set `AGNES_API_KEY` in the Render service's Environment settings. The service uses:
- Build: `pip install -r requirements.txt`
- Start: `uvicorn api:app --host 0.0.0.0 --port $PORT`
- Health check: `/health`

## Notes
- Image and video generation require a valid Agnes API key and are subject to the Agnes account's model access, quotas, and billing.
- Browser history is local to that browser/device and is not synchronized between devices.
- Multi-shot mode currently sends a structured multi-shot prompt to one video generation task; it does not stitch multiple independently generated clips.
- The former AK-Byte chat model, its weights, dataset, and training pipeline have been removed from this repository.
