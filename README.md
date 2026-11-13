# Kryptex Studio

A redesigned mobile-first PWA workspace with AI writing, image-prompt, video-script, social-media, summarizer, translator and study tools, plus calculator, local notes/tasks and printable invoice maker.

## AI backend
A Netlify Function is included at `netlify/functions/ai.mjs` and routed to `/api/ai`. Configure either `GEMINI_API_KEY` (optional `GEMINI_MODEL`) or `KRYPTEX_HUB_API_URL` as a server-side environment variable. The latter should be the base URL of the existing Kryptex Hub Express server; requests are forwarded to its `/chat` route. Never place API keys in browser code or commit them to Git.

**Important:** GitHub Pages only hosts static files and cannot execute server functions. The current Pages workflow publishes the PWA shell; the AI backend will only run after this repository is deployed on Netlify (or the function is hosted on another compatible backend). Provider credentials also need to be configured securely in that host. The Netlify project/deploy could not be updated from the available deployment connection in this session, so live AI is not yet verified.

## App
The PWA can be installed on Android from a supported browser using Install / Add to Home Screen. This is not a native APK or Play Store release. Offline caching covers the app shell; AI requires internet access.

## Data and feature limits
Notes and tasks are saved locally in the current browser/device and are not cloud-synced. Invoice Maker creates a basic printable bill, not GST-compliant accounting software. Image Studio currently creates a detailed image-generation prompt; actual image generation requires an image provider endpoint. Ads.txt is present, but live ads require approval and configured ad units.
