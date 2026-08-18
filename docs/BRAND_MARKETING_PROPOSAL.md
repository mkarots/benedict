# Benedict Branding and Marketing Proposal

One-sentence summary:
An initial proposal to start a branding and marketing working session. Options, recommendations, and a decision agenda — not a final plan.

## 1. Overview

**What:**
A working document for branding, positioning, and go-to-market decisions for Benedict.

**Why:**
Benedict is a working Slack bot (v0.3.20) that links channels to local git repositories and answers questions with Claude, semantic search, method files, and thread history. Open-source launch is planned. Communication is currently pending in `.benedict.method.yaml`. Brand and marketing need explicit decisions before that communication ships.

**When to use:**
Use this in a branding/marketing call. Treat each section as a starting point. Leave the call with decisions recorded in the agenda at the end, not with more options.

## 2. Non-Goals

This document is not:

- A final brand book or visual identity system
- A commercial business model or pricing plan
- A replacement for `WHY.md` (that artifact is still missing and would sharpen the story)
- A launch-day announcement draft (write that after positioning is locked)

Out of scope: Teams/Discord expansion, paid ads, trademark filing (flagged, not decided here).

## 3. Key Concepts and Terminology

| Term | Meaning |
| --- | --- |
| Benedict | The product: a self-hosted Slack bot that maps a channel to a git repo and answers questions about that repo |
| Method file | `.benedict.method.yaml` — source of truth for project phase, concerns, and rules |
| Architect channel | A Slack channel marked for cross-project questions across onboarded repos |
| ICP | Ideal customer profile — who we write for first |
| Soft launch | Public repo with no announcement; test with a few friendly users |

## 4. Positioning

### Draft one-liner

**Benedict is the Slack-native repo agent that already knows your codebase, your thread history, and where the project is in its lifecycle.**

### Options to test on the call

| Option | One-liner | Emphasis |
| --- | --- | --- |
| **A — Context** | "The teammate who already read the repo." | Warm, human, Slack-native |
| **B — Method** | "Repo intelligence with project discipline built in." | Differentiator (`.benedict.method.yaml`) |
| **C — Infrastructure** | "Self-hosted Slack agent for teams that live in their repos." | Privacy, control, devops audience |
| **D — Architect** | "One bot per repo — plus an architect across all of them." | Multi-project story |

**Recommendation:** Lead with **A** externally. Support with **B** for technical buyers. C and D are secondary messages, not the headline.

## 5. What Benedict is and is not

Clear boundaries keep branding honest and match the method-file rule: communication is factual, not fluff.

**Benedict is:**

- A Slack bot scoped to a channel ↔ repo mapping
- Self-hosted (runs on your machine or server)
- Context-rich: semantic search, README, metadata, method phase, Slack thread history
- Opinionated about how projects run (method file, phase, concerns)

**Benedict is not:**

- Cursor or Copilot (in-IDE pair programmer)
- Sourcegraph Cody (enterprise code search at scale)
- A hosted SaaS you sign up for
- A GitHub-native reader (local checkout required today)
- General-purpose ChatGPT in Slack

**Implication:** Do not compete on "best AI coding assistant." Compete on "best repo context inside Slack where your team already works."

## 6. Target audience

### Primary ICP — Slack-as-ops-surface engineering teams

- Size: 5–50 engineers, often startup or scale-up
- Behavior: Project channels in Slack (`#widget-api`, `#platform`), not just DMs
- Pain: Context scattered across threads, PRs, docs, and people's heads
- Fit: Already run bots and integrations; comfortable self-hosting Python

### Secondary ICP — Solo and small-team maintainers

- One person wearing many hats
- Uses Slack as a command center for multiple repos
- Architect channel is the hook: cross-project visibility without context switching

### Early adopter profile (open-source launch)

- Python-friendly
- Runs their own Slack workspace
- Has local git checkouts and cares about data staying on-prem
- Will tolerate setup friction for control

### Anti-personas (do not market to yet)

- Teams wanting zero setup or cloud-only
- Non-Slack shops (Teams, Discord)
- Enterprises needing SOC2-certified hosted SaaS on day one

## 7. Value proposition

Build messaging in three layers. Lead with the problem.

```
EMOTIONAL     Stop re-explaining the codebase in every Slack thread.

FUNCTIONAL    Repo-scoped answers + thread memory + semantic search
              + method-aware context

PROOF         Onboard → ask → follow-up thread → gh PR lookup
              → architect cross-repo
```

**Three proof points to demo in every pitch:**

1. **Onboard in one message** — `@benedict onboard repo acme/widget`
2. **Thread continuity** — follow-ups work without re-@mentioning
3. **Method-aware** — Benedict knows phase and concerns from `.benedict.method.yaml`

## 8. Brand identity — the name Benedict

### Why it works

| Association | Brand fit |
| --- | --- |
| St. Benedict / Rule of Benedict | Order, method, discipline — aligns with `.benedict.method.yaml` |
| Formal but approachable | Feels like a named colleague, not "CyberCodeBot 3000" |
| Distinctive in devtools | Memorable vs generic names (RepoBot, CodeAssist) |
| Architect persona | "Benedict Architect" reads naturally |

### Risks

| Risk | Mitigation |
| --- | --- |
| Sounds like a person, not a product | Always pair with a descriptor: **Benedict — Slack repo agent** |
| Celebrity association (Cumberbatch) | Ignore. Do not lean into it. |
| Trademark / namespace | GitHub `mkarots/benedict` is fine; check PyPI slug before launch |
| Too formal for startup audience | Keep the name; keep copy warm |

**Call decision:** Keep Benedict as the product name. Recommendation: yes. Lean into the method and discipline story.

### Voice and tone

Aligned with the project's communication concern.

| Do | Don't |
| --- | --- |
| Factual, specific, show the command | Hype ("revolutionary," "10x") |
| Engineer-to-engineer clarity | Corporate marketing speak |
| Acknowledge constraints (local repo, self-host) | Oversell as magic |
| Short Slack-friendly sentences | Long landing-page prose |

**Personality:** Calm, knowledgeable colleague — not a hypey sales bot, not a sycophantic AI.

## 9. Visual identity — initial direction

No assets exist yet. Three directions for the call:

### Direction 1 — Monastic minimal (recommended)

- Colors: Deep navy + warm parchment/off-white + one accent (amber or sage)
- Mark: Abstract "B" or stacked lines suggesting order (not a monk cartoon)
- Typography: Clean serif for the wordmark + sans for UI and docs (Inter or IBM Plex)
- Vibe: Serious tool, subtle nod to method and discipline

### Direction 2 — Slack-native friendly

- Brighter palette, rounded shapes, at home next to Slack emoji culture
- Risk: Looks like another Slack app template

### Direction 3 — Terminal brutalist

- Monospace, green-on-black, hacker aesthetic
- Risk: Narrow audience; fights the "colleague" positioning

### Minimum viable brand kit for open-source launch

1. Wordmark + simple icon (GitHub social preview 1280×640)
2. Slack app icon (512×512)
3. README header graphic
4. One color and one font decision (do not over-design v0)

## 10. Messaging framework

### Elevator pitch (30 seconds)

Benedict is a Slack bot you self-host. You link a channel to a git repo, and Benedict answers questions about that codebase using Claude and semantic search. It remembers the thread, knows your project's current phase from a method file, and can coordinate across repos through an architect channel. It is for teams that already run projects in Slack and want an agent that shows up with context — not a blank chatbot.

### Homepage hero (draft)

**Headline:** Your repo's context, inside Slack.

**Subhead:** Benedict links a channel to a git repository and answers questions with code search, thread history, and project method built in. Self-hosted. You control the data.

**CTA:** View on GitHub · Read the docs

### Feature to benefit map

| Feature | User-facing benefit |
| --- | --- |
| Channel ↔ repo onboarding | One channel, one codebase — no confusion |
| Semantic search + metadata | Finds the right files, not just keyword matches |
| Thread memory | Continue the conversation without repeating context |
| `.benedict.method.yaml` | Knows if you are in sprint vs design — answers match project state |
| Architect channel | Ask across all your repos from one place |
| Self-hosted | Your code and API keys stay on your infrastructure |
| `gh` integration | PRs and issues without leaving Slack |

### Competitive framing (honest)

| Alternative | When they win | When Benedict wins |
| --- | --- | --- |
| Cursor / Copilot | In-editor coding | Slack-first teams, async Q&A |
| Slack AI (native) | Zero setup | Repo-specific depth + method |
| Sourcegraph | Huge monorepos, enterprise | Small teams, self-hosted, method-aware |
| Custom GPT + webhook | Flexibility | Batteries included: indexing, workspaces, method |

## 11. Go-to-market — phased plan

Aligned with open-source readiness (~60%) and the method sprint loop (build → document → communicate).

### Phase 0 — Pre-launch (now until public repo)

**Goal:** Brand foundation and launch-ready repo

- Pick positioning option (A / B / C / D)
- Add LICENSE, SECURITY.md, CONTRIBUTING (blocks credibility)
- README hero + one architecture diagram + 60-second demo GIF
- Decide PyPI name and Slack app display name
- Soft test with 2–3 friendly teams

### Phase 1 — Public open-source launch

**Goal:** First 100 GitHub stars, 5 real deployments

**Channels (priority order):**

1. **Show HN** — lead with self-hosted + Slack-native; expect sharp questions about the local checkout requirement
2. **Reddit** — r/selfhosted, r/Python, r/slack (follow sub rules)
3. **Dev.to / personal blog** — "Why we built a repo agent in Slack instead of the IDE"
4. **Twitter/X / LinkedIn** — demo GIF + thread explaining the method file concept

**Launch asset checklist:**

- 90-second screen recording: onboard → question → thread follow-up
- One architecture-in-one-diagram image
- CHANGELOG-style release note (factual, per method rules)

### Phase 2 — Community and credibility

- GitHub Discussions for support
- "Benedict in production" case study (even if it is your own team)
- Content series: method file philosophy, workspace isolation, architect pattern
- Conference CFP: self-hosted AI agents, Slack as a dev surface

### Phase 3 — Expand the story (when the roadmap delivers)

- Remote GitHub reader → unlock "no local checkout" messaging
- Hosted option (if ever) → new ICP, new brand sub-line — decide deliberately

## 12. Channel strategy

| Channel | Role | Effort |
| --- | --- | --- |
| GitHub README | Primary conversion — must stand alone | High |
| Demo video / GIF | Proof for HN and social | High |
| Docs site (GitHub Pages later) | SEO, onboarding | Medium |
| Slack App Directory | Discovery — only after polish and a support story | Low priority initially |
| Newsletter / blog | Method philosophy, builds authority | Medium |
| Paid ads | Skip for now — ICP is too niche and the self-host story needs education | None |

**Content pillars (repeatable themes):**

1. Slack as the missing layer in dev tooling
2. Method files — project discipline for AI agents
3. Self-hosted AI — privacy without sacrificing capability
4. Architect pattern — multi-repo coordination

## 13. Constraints and assumptions

- Product is self-hosted and requires a local git checkout today. Marketing should state this upfront.
- Communication concern in the method file is `pending`. This proposal is the drafting step before publish.
- Open-source packaging is incomplete (LICENSE file missing, community files missing). Credibility of a public launch depends on those.
- No visual assets exist yet.
- `WHY.md` is expected by the method file and does not exist. Brand story is weaker until that is written.

## 14. Alternatives considered

**Rename the product** — rejected as default. Benedict is distinctive and maps to the method story. Revisit only if a hard trademark or namespace conflict appears.

**Lead with "AI coding assistant"** — rejected. That market is crowded and Benedict's surface is Slack, not the editor.

**Lead with hosted SaaS** — rejected until the product is hosted. Do not sell a product that does not exist.

**Launch on Slack App Directory first** — rejected. Setup is self-hosted Socket Mode; Directory listing would overpromise "install and go."

## 15. Decisions for the call (agenda)

Use this as a literal agenda. Aim to leave with answers.

### Brand

1. Keep the name Benedict? (Y/N)
2. Primary tagline — pick A, B, C, or D from section 4
3. Visual direction — Monastic minimal / Slack-friendly / Terminal
4. Descriptor always appended? Example: "Benedict · Slack repo agent"

### Positioning

5. Lead differentiator — context in Slack vs method discipline vs self-hosted vs architect
6. Honest constraint in marketing? State "local checkout required" upfront (recommend: yes)
7. Competitive enemy — "context switching" vs "generic chatbots" vs "IDE lock-in"

### Audience

8. Primary ICP for launch — small eng teams vs solo maintainers vs open-source contributors
9. Geography / language — English-only initially?

### GTM

10. Launch gate — public repo at current readiness, or wait for tests + CI (recommend: soft launch after legal/community files; public announce after basic CI)
11. Launch channel priority — HN first vs blog-first vs friends-and-family only
12. PyPI publish — same day as GitHub public, or later?

### Future (flag, do not need final answers)

13. Commercial path? Open-core, support, hosted, or pure OSS forever
14. Multi-platform (Teams, Discord) — ever, or Slack forever?
15. Trademark registration — now or after traction?

## 16. Open questions

1. **WHO.md / WHY.md missing** — writing `WHY.md` would sharpen the brand story (motivation before messaging).
2. **Is Benedict a personal project, a company, or a foundation?** — affects voice and launch authority.
3. **Relationship to the Cursor ecosystem** — complement ("use both") or alternative?
4. **Slack app name vs repo name** — same "Benedict" or workspace-specific?
5. **Logo budget** — DIY (Figma + AI), freelancer, or defer to an emoji placeholder for v0?

## 17. Recommended defaults (if the call runs short)

| Decision | Recommendation |
| --- | --- |
| Name | Keep **Benedict** |
| Tagline | **The teammate who already read the repo.** |
| Visual | Monastic minimal, navy + parchment + amber |
| Lead message | Slack-native repo context |
| Launch | Soft public after LICENSE + CONTRIBUTING + demo GIF; Show HN after CI green |
| Tone | Factual, engineer-to-engineer — no fluff |

## 18. Suggested 45-minute call flow

| Time | Topic |
| --- | --- |
| 0–5 min | Align on what Benedict is and is not (section 5) |
| 5–15 min | Pick positioning and tagline (sections 4 and 15, items 1–2) |
| 15–25 min | ICP and lead differentiator (sections 6 and 15, items 5–8) |
| 25–35 min | Visual direction and MVP brand kit (section 9) |
| 35–42 min | Launch timeline and channels (sections 11 and 15, items 10–11) |
| 42–45 min | Assign owners: WHY.md, demo video, LICENSE, README hero |

## 19. Appendix — how to use this document after the call

Record decisions by editing this file:

- Strike rejected options.
- Move chosen tagline and visual direction to the top of section 4 and section 9.
- Move remaining open questions to a backlog or `WHY.md`.
- Do not announce until LICENSE, CONTRIBUTING, and a demo GIF exist.
