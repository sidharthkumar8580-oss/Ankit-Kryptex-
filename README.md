# Kryptex Workspace

A mobile-first static web app / PWA for students, shops, small businesses and everyday use.

## Included
- Study notes, task planner, marks percentage and timetable
- Shop bill calculator, discount calculator and print view
- Customer mini-CRM with CSV export
- Calculator, unit converter, text tools and date difference
- Kryptex AI chat shell with configurable HTTPS backend endpoint
- PWA manifest, install prompt and offline service worker
- Local browser storage and JSON backup export

## Publish
This is a static site. Enable GitHub Pages for this repository from **Settings → Pages → Deploy from a branch → main → /(root)**. The live URL will be shown by GitHub Pages after its first build.

## Important configuration
- The AI page needs a working HTTPS backend URL entered in Settings. Do not expose secret API keys in frontend code.
- The ads.txt file contains the publisher declaration supplied for the publisher account. Actual web ads still need the approved ad network's site approval and ad-unit code. AdMob mobile SDK ads require a native Android wrapper/app and approved app/ad-unit IDs; this PWA alone does not install the AdMob SDK.
- Customer data and notes stay in this browser only. Export backups regularly; no cloud sync or authentication is included.
