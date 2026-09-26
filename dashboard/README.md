# Dashboard maintenance

This directory is a tiny static status site for the project.

## Files

- `status.json` - the bot-editable data source that drives the page
- `index.html`, `styles.css`, `app.js` - the presentation layer
- `.nojekyll` - harmless static-host compatibility marker

## Normal refresh flow

1. Update `dashboard/status.json`.
2. Keep every new number grounded in committed repo files (`STATUS.md`, `docs/FINDINGS.md`, `INSIGHTS.md`, committed results, and so on).
3. Push to `main`.
4. Redeploy the `dashboard/` folder to your chosen public host.

## Current public-hosting note

This repo's current GitHub plan rejects GitHub Pages for this repository, so the
dashboard ships as a host-agnostic static folder instead of an always-on Pages site.

For a quick no-secret public preview from this environment, the commands used were:

```bash
cd /workspace/dashboard
python3 -m http.server 4173
npx localtunnel --port 4173
```
