# Kryptex Studio 3.0

Mobile-first PWA toolbox with 50 listed tools and 10 mini-games. Desktop uses a wide workspace and multi-column cards; phones use compact two-column cards and a bottom navigation.

## Included tools
The catalogue includes the 39 requested items plus 11 everyday extras. Some are browser-local (password generator, QR display, calculators, word counter, CSV preview, Markdown preview, timers, notes); AI-assisted tools call `/api/ai` and require a live backend. Media conversion, background/object removal, photo restoration, video generation and OCR require compatible provider services and are not claimed as active unless configured.

## Games
Tic-tac-toe uses minimax. Math challenge, Word Master, Sudoku solver/player, memory match, typing speed, GK quiz, basic chessboard demo, 2048 and Snake are included. Chess is a basic board interaction demo (not full tournament chess rules); Snake & Ludo menu currently provides Snake. A full multiplayer Ludo implementation and server leaderboard are not included yet.

## AI backend
Netlify Function: `netlify/functions/ai.mjs`, route `/api/ai`. Set `GEMINI_API_KEY` or `KRYPTEX_HUB_API_URL` in the hosting provider's environment variables. The existing Kryptex Hub server's `/chat` endpoint can be used as the upstream URL if it is deployed and publicly reachable. Never place secrets in browser code.

**Hosting limitation:** GitHub Pages serves the static PWA but cannot execute Netlify Functions. For AI tools to work, deploy this repository to Netlify (or host the function separately and configure the frontend API route). The current GitHub Pages workflow does not deploy the server function. The previous Netlify project connection is read-only in this session, so a live backend deployment and secret configuration are not verified.

## PWA and data
Installable web app, not a native APK or Play Store app. Local notes/tasks are stored in the current browser only; there is no account or cloud sync. Ads require approval and configured web ad units; the ads.txt declaration alone does not activate ads.
