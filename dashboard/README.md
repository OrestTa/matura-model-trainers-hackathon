# Dashboard maintenance

This directory is a tiny static status site for the project.

## Files

- `status.json` - the bot-editable data source that drives the page
- `index.html`, `styles.css`, `app.js` - the presentation layer
- `.nojekyll` - keeps GitHub Pages from applying Jekyll processing

## Normal refresh flow

1. Update `dashboard/status.json`.
2. Keep every new number grounded in committed repo files (`STATUS.md`, `docs/FINDINGS.md`, `INSIGHTS.md`, committed results, and so on).
3. Push to `main`.

The GitHub Pages workflow publishes the contents of `dashboard/`.
