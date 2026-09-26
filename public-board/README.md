# Public Matura status board

Public live URL:
- https://orestta.github.io/tarasiuk-lab-matura-status/

Public publishing repo:
- https://github.com/OrestTa/tarasiuk-lab-matura-status

Files:
- `index.html` - static shell that fetches `status.json`
- `status.json` - board content and scores

## Refresh flow

1. Update `public-board/status.json` in this private repo.
2. Copy `public-board/index.html` and `public-board/status.json` to the public repo `OrestTa/tarasiuk-lab-matura-status`.
3. Push to `main` in that public repo.
4. GitHub Pages republishes automatically from the repository root.

Keep the board free of secrets, keys, private IPs, or internal-only links that must not be public.
