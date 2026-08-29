# Landing page deploy checklist

What must be true before `landing/index.html` goes on a public URL.

This list is for the marketing page only. Full open-source packaging is in [docs/OPEN_SOURCE_GUIDE_INDEX.md](../docs/OPEN_SOURCE_GUIDE_INDEX.md).

## Blockers

Do not publish until every item here is done.

- [ ] **Add a `LICENSE` file.** The page and README claim MIT. The file is not in the repository. The footer already links to `/LICENSE`.
- [ ] **Make the GitHub repo public** (or update every `github.com/mkarots/benedict` URL on the page to the public remote).
- [ ] **Scan git history for secrets** before traffic hits the repo. `.env` is gitignored; confirm it was never committed.
- [ ] **Audit claims against the current README.** The stage, feature strip, and install steps must match what ships today. Drop or reword anything that is roadmap-only.
- [ ] **Set the version chip** in the product stage to the released package version (`pyproject.toml`).

## Hosting

- [ ] Pick a host. Default: GitHub Pages from `landing/` (or copy `index.html` to `/docs` if Pages is configured there).
- [ ] Decide the public URL (Pages default, custom domain, or something else).
- [ ] If custom domain: DNS, HTTPS, and an apex/www decision.
- [ ] Set `og:url` and a `<link rel="canonical">` to that URL.
- [ ] Add a 1200×630 `og:image`. Social cards currently have title and description only.
- [ ] Set the GitHub repo **Website** field to the public URL.
- [ ] Decide how deploys happen: manual upload, or a Pages workflow on `main`.

## Page content

- [ ] Open-source wording is visible above the fold (kicker, lead, nav).
- [ ] License link resolves (needs `LICENSE` on the default branch).
- [ ] Slack setup link points at a real file on the default branch.
- [ ] Example tokens stay placeholders (`xoxb-…`, `xapp-…`). No live keys.
- [ ] Example thread copy is fictional. No real channel names, users, or commits from private work.
- [ ] Google Fonts is an intentional third-party request, or fonts are self-hosted.

## Verify before DNS goes live

- [ ] Desktop and a ~390px viewport: hero, stage tabs, install, footer.
- [ ] Stage tabs switch Slack / Operator / MCP.
- [ ] Copy button works on **https** (clipboard needs a secure context).
- [ ] In-page anchors: How it works, Surfaces, Local-first, Install.
- [ ] External links return 200: GitHub, README, LICENSE, Slack setup.
- [ ] No leftover `localhost` or `127.0.0.1` URLs in the shipped HTML.

## After first publish

- [ ] Link the live URL from the README documentation table.
- [ ] Recheck the page when the command surface or version changes.
- [ ] Leave analytics off unless you choose a tool and disclose it.
