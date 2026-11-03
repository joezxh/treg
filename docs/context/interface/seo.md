---
title: Search surfaces - robots, sitemap, the crawlable catalog, and the social card
status: shipped
sources:
  - src/treg/api.py
  - src/treg/routers/web.py
  - src/treg/agent_pages.py
  - src/treg/web/robots.txt
  - src/treg/web/catalog.css
  - src/treg/web/usecase.css
  - frontend/index.html
  - frontend/src/App.vue
  - frontend/src/components/PublicNavigation.vue
  - frontend/src/state/boot.js
  - src/treg/web/landing.html
  - src/treg/web/media/landing/product-theme.css
  - src/treg/web/media/landing/refinement.css
  - src/treg/web/media/landing/gateway.css
  - src/treg/web/media/landing/hero-opening.js
  - src/treg/web/media/landing/refinement.js
  - src/treg/web/media/landing/catalog-drum.js
  - src/treg/web/media/landing/gateway.js
  - src/treg/web/media/landing/gateway-loader.js
  - src/treg/web/media/landing/gateway-3d.js
  - src/treg/web/media/landing/gateway-model.js
  - src/treg/web/media/landing/gateway-intro.js
  - src/treg/web/media/landing/hero-particles.js
  - src/treg/web/media/landing/command-beam.js
  - src/treg/web/media/landing/SOURCES.md
  - frontend/e2e/landing.spec.ts
  - src/treg/web/terms.html
  - src/treg/web/usecase-seo.html
  - src/treg/web/usecase-company.html
  - src/treg/web/usecase-enrichment.html
  - src/treg/web/usecase-social.html
  - src/treg/web/usecase-ads.html
  - src/treg/web/people-search.html
  - src/treg/web/leads-signals.html
  - src/treg/web/recruit.html
  - src/treg/web/web-access.html
  - src/treg/web/gtm-engineering.html
  - src/treg/web/grokbot.html
  - src/treg/web/fable-gtm.html
  - src/treg/web/ugc.html
  - src/treg/web/aeo.html
  - src/treg/web/rea-growth.html
  - src/treg/web/rea-growth.md
  - src/treg/web/start.html
  - src/treg/web/jev.html
  - src/treg/web/showcase.html
  - src/treg/web/rankings.html
  - src/treg/routers/rankings.py
  - src/treg/web/media/showcase/wall.json
  - src/treg/application/jev_xboost.py
  - src/treg/application/house_calls.py
  - src/treg/web/media/jev/xboost-seed.json
  - src/treg/web/media/jev/triage.json
  - src/treg/web/media/jev/signals.json
  - src/treg/web/astra.html
  - src/treg/web/media/astra/page.css
  - src/treg/web/media/astra/page.js
  - src/treg/web/media/signin-sso.js
  - frontend/src/components/SignInDialog.vue
  - src/treg/web/llms.txt
  - scripts/indexnow_submit.py
  - src/treg/web/support.html
  - assets/brand/og-card.html
related:
  - interface/api.md
  - interface/dashboard.md
  - architecture/catalog.md
---

# Search surfaces

Everything a crawler, a link unfurler or an AI answer engine sees. Signup-credit copy on every page
describes one grant per new verified account, not per team
([money](../architecture/money.md#signup-credit-eligibility)).

## Routes

| Path | Rule worth knowing |
|---|---|
| `/robots.txt` | Bundled, `{BASE}`-templated. Disallows `/app`, `/login`, `/auth/`, `/oauth/`, `/connect-demo`, `/call/`, `/mcp`, `/admin`, `/docs/api`; names the sitemap. `Disallow: /app` is a prefix rule: it also blocks any future public path starting with `/app` (e.g. `/apps`) unless a longer `Allow:` line is added. |
| `/sitemap.xml` | Generated. Static pages take `lastmod` from file mtime, shelves from the newest mtime under `src/treg/catalog/`. |
| `/` | Server-rendered `web/landing.html`; visuals under `web/media/landing/` (`SOURCES.md` pins the design reference and library versions; Three.js and Lenis load from version-pinned jsDelivr URLs). Reduced motion is static; WebGL or module-download failure (`gateway-loader.js`, outside the module graph) reveals the static mark; BFCache `pageshow` resumes animation. Signed-in visitors see **Open dashboard**. Session-dependent HTML is `private, no-store` with `Vary: Cookie`. `frontend/e2e/landing.spec.ts`. |
| `/catalog`, `/catalog/<slug>`, `/catalog/<slug>/<key>` | The dashboard SPA in public mode (below). `<key>` is a capability two or more providers serve on that shelf (`Catalog.compared`, `_comparison_paths`); a single-provider capability is a 404. All are sitemapped and each is fetched for a 200 in `tests/test_catalog_api.py`. |
| `/tools/<service>` | One server-rendered page per provider (`_page`, no SPA), counts and prices live from `catalog_store`. No provider index page. Safe from shadowing the API (`/tools`, `/tools/by-name/...`). A signed-out `GET /app/marketplace/<service>` 302s here. |
| `/agents`, `/agents/<agent>` | Agent pages (below). |
| `/use-cases`, `/use-cases/<job>`, `/resources` | Use-case pages and hubs (below). |
| `/workflows`, `/workflows/<slug>`, `/workflows/<slug>.csv` | Workflow pages (below). |
| `/blog`, `/blog/<post>` | Hand-kept index (`_BLOG_LAUNCHES`, `_BLOG_POSTS`). Posts carry `BlogPosting` (`_blog_posting_ld`) beside breadcrumbs. `/agents/grok-bot` 301s to `/grokbot`. |
| Launch landings (`/people-search`, `/leads-signals`, `/web-access`, `/recruit`, `/grokbot`, `/fable`, `/ugc`, `/aeo`, `/rea-growth`, `/gpt6`, `/jev`) | Bundled files through `_static_page` (placeholders filled, no-cache, ETag revalidation to 304), canonical, OG, sitemapped. `/astra` 301s to `/gpt6` keeping the query (campaign attribution). `ugc.html` uses relative asset paths, which only resolve while the route stays slashless. `/web-access` reads current prices from `/web-arena/api/leaderboard` with a bundled snapshot fallback and deliberately shows no hit-rate board (each vendor sees different traffic; that stays on `/web-arena`). Copy on `/leads-signals` and the Hermes guide must not imply treg schedules or diffs: the agent does. `/rea-growth.md` is `noindex` via `_serve_md`. |
| `/jev` | `/jev/xboost.json` serves the document `treg-worker jev xboost` stores (Ephemeral `jev`/`xboost`), else `media/jev/xboost-seed.json` flagged `snapshot: true`. `POST /jev/xboost/judge` is rate-limited per IP and fleet-wide through ratestore, answers 503 until `jev_treg_token` and `ai_gateway_api_key` are set, and its entries survive the daily run. `application/jev_xboost.py` calls `/call/` with the demo team's token, so the receipt is a real bill. Bundled recipe runs have every email address replaced. `tests/test_jev.py`. |
| `/start` | Paid-traffic landing. Hosted-only, `noindex` (meta and `X-Robots-Tag`), no canonical, not sitemapped. `?job=` picks copy from a fixed table; unknown values (including `constructor`, `__proto__`) get the general page. `sitetrack.js` loads before the page script so `start_viewed` is not dropped; copy events fire only after a fulfilled clipboard write. `tests/test_start_page.py`. |
| `/gtm-engineering` (+ `.md`) | Hand-written (not `_page()`) because only hand-written pages load `sitetrack.js`. Its original studies publish results, never rows: the test fails if a catalog provider is named in a study block, a headline figure leaves its section, or a study FAQ answer drifts from its JSON-LD; raw data stays out of the repo. The `.md` twin is hand-kept and `tests/test_gtm_engineering_page.py` fails on a missing chapter heading. Hosted-only. |
| `/rankings` | Served on every registry (it counts that registry's traffic), sitemapped. Boards come from the row `treg-worker rankings refresh` saves ([catalog](../architecture/catalog.md)). The first board is inlined as JSON plus an `ItemList`; the rest load from `/rankings/data/{board}`. The page hand-copies the dashboard's `SelectMenu` and `SpendBars` because a static page cannot import Vue components: change them together. `tests/test_rankings.py`. |
| `/showcase` | Tiles written in the HTML with `CollectionPage`/`ItemList`. The X wall is a committed snapshot (`media/showcase/wall.json`); the page never fetches from X. Hosted-only. `tests/test_showcase_page.py`. |
| `/docs`, `/docs/api` | Server-rendered reference from `app.openapi()`; Swagger UI moved to `/docs/api` and disallowed. ReDoc is off. |
| `/media/og.png`, `/media/brand/*` | The 1200x630 social card and stable hot-linkable brand files (copies of `assets/brand/twitter/`). |
| `/{INDEXNOW_KEY}.txt` | The IndexNow key, on every host (not a secret: the protocol only checks it is served from the submitted host). `scripts/indexnow_submit.py` pushes the live sitemap to `api.indexnow.org`. Google has no sitemap ping; resubmit through Search Console. |

Hosted-only pages check `_hosted()` (`public_url` against `PUBLIC_HOST_ALIASES`); elsewhere they
404 and the sitemap omits them, because their copy describes treg.to's own listings and grant.
Links to them in bundled files sit inside `<!--hosted-->...<!--/hosted-->`, which `_strip_hosted`
unwraps on the hosted deployment and removes elsewhere, so no served page links a 404.

Every route is registered in `bootstrap.py`'s route-ownership manifest.

## The `_page()` shell and tracking scripts

`_page()` in `routers.web` owns `<title>`, meta description, canonical, og/twitter card, JSON-LD,
`/adtrack.js` and a "Start free" CTA carrying `?ref=<page>` (the boot treats `ref` as a use-case CTA:
no bounce, sign-in opens in place, and the page that produced the signup is recorded). A page
without `adtrack.js` silently loses paid attribution: no `treg_ad` cookie, so `org.ad_gclid` stays
NULL and `adsconv.queue()` no-ops.
`test_pages_off_the_shared_shell_carry_adtrack` asserts one `adtrack.js` on a `_page()` caller. Pages outside the shell (`_static_page` files, `/docs/api`) carry their tags by
hand; nothing sweeps every route, so a new standalone ad destination must add the tag itself.

`/sitetrack.js` is deliberately **not** in the shell. It loads PostHog, and `web/privacy.html`
promises no analytics or session-replay scripts on the signed-in dashboard; broadening it across
the programmatic pages is a product/legal decision, not a side effect of an attribution fix.
Hand-written marketing pages take the opposite default and do load it, or they emit no pageview at
all. `tests/test_sitetrack.py` enforces that any `web/*.html` carrying an ad script also carries
`sitetrack.js`. Script paths are root-absolute
(`/sitetrack.js`); the test forbids the relative form.

Public sign-in dialogs share `media/signin-sso.js`: email code first, company SSO as an alternate
mode. Company discovery picks the verified team route and never grants access itself.

## The public catalog is the dashboard

`/catalog` and its sub-routes serve the compiled dashboard entry, so the public page and the member
view render the same per-job comparison and cannot drift into two implementations. The catalog API
is unauthenticated; `publicCatalog` (`frontend/src/state/data.js`) is set from `catalogFromPath()`
before the `/auth/me` check, so the first paint is already public. Public mode swaps the app chrome
for a marketing nav, hides session-only views and connection badges, and routes every action
(Try-it, Connect, BYOK, Start free) to the sign-in modal in place.

- **Never point a public CTA at `/app`.** A signed-out `/app` visit `location.replace('/')`s to the
  landing with no modal, losing the page. Call `openSignin()`. The modal is a sibling of both the
  signed-out and app branches so public mode can open it.
- `platProviders`, `provName` and `mkKnown` fall back to the open response's `providers` map (their
  normal source, `/connections`, needs a session). `mkOauth` has none (no `auth_kind` in the open
  response), so public mode offers BYOK, true for every provider.
- `/catalog/<slug>` asks for `include_hidden=1`, matching `loadPlatform`; a different population
  would put two endpoint counts on one URL.
- `frontend/e2e/dashboard.spec.ts` covers public navigation and reachable sign-in.

**No-JS fallback.** Vue replaces `#app` on mount, so prerendered markup is a sibling `#prerender`,
visually hidden (`_PRERENDER_HIDDEN`) and removed on boot; it stays for readers that run no script
(most AI crawlers and agent fetchers). It carries text (names, summaries, providers, prices), not
the ledger's client-side row merging, which would recreate the duplicate implementation. The
response also embeds `/catalog/platforms` as `<script id="catalog-platforms">`, read by
`loadPlatforms` instead of fetching. `/search` instead paints a full-viewport ground so it opens
with no loading step.

**Adding a platform** needs no code: everything reads one `catalog_store.load()`. It does need a
`platforms:` entry in `capabilities.yaml`; without one the shelf is `category: "Other"`, which the
app grid skips while the sitemap still publishes it
(`test_no_shelf_is_published_that_the_app_grid_hides`).

**Changing shared UI** reaches the public pages automatically, except: elements built on
member-only state (`providers`, `connCount`, `billing`, `sessionMode`) render blank publicly; a new
member-only action is visible to signed-out visitors until gated on `authed` or `publicCatalog`;
and the `#prerender` text and SEO head are server-built (`_spa_catalog_page`), so changing what the
page says means updating them too. Anything added to the `App.vue` shell (a promo banner) lands on
every crawlable shelf unless gated on `!publicCatalog`, with a test that `#prerender` never carries
it.

## Things that will bite you

- **`{BASE}`, never a hardcoded `treg.to`.** Self-hosted registries serve these pages; a hardcoded
  canonical tells their crawler the page lives elsewhere (`test_no_page_ships_an_unsubstituted_base`). `landing.html` and
  `_static_page` files are substituted; the dashboard's `index.html` is **not**, so hardcode
  absolute URLs on the app side.
- **HEAD.** FastAPI's `APIRoute` never adds HEAD, and crawlers probe with it first. The composition
  root widens GET-only routes after registration while the OpenAPI wrapper hides the implied HEAD
  operations ([composition](../architecture/composition.md)).
- **`/catalog/<slug>` sits in front of the JSON routes.** `/catalog/platforms`, `/catalog/search`,
  `/catalog/endpoints/...` and `/catalog/examples/...` match only because they register first;
  `_CATALOG_RESERVED` is the second guard (`test_the_json_catalog_routes_still_answer_json`). Swallowing one
  breaks the dashboard and every installed CLI.
- **Structured data must match the visible page.** Google treats schema claiming something the page
  does not say as a violation. The landing's `Offer` figures are asserted against the rendered
  HTML, every FAQ in `support.html`'s schema must appear in its body, FAQPage questions on agent and
  use-case pages appear verbatim, and a HowTo mirrors the visible setup steps in order. Edit both in
  one commit.
- **Prices need `_usd_short`, not `%g`** (scientific notation below `1e-4`). Sub-hundredth-cent
  renders `<$0.0001`, which must be HTML-escaped at every use site.
- **Title matches H1**, and a price label carries its billing unit ("/result", "/call"), so copy
  never says "per call" beside it. Titles fit `_TITLE_MAX`; descriptions go through `_serp_desc`.
- **Sitemap.** `_SITEMAP_PAGES` spreads `_USE_CASES` (defined above it) so a routed page cannot be
  forgotten. List bare paths only: `/use-cases/<slug>/` 307s and listing a redirect is worse than
  nothing. `test_every_sitemap_url_answers_200` walks it.
- **A sitemap is not a crawl path.** Pages in the sitemap but linked from nothing stay unknown to
  Google. The `_page()` footer, the landing footer and the `/catalog` prerender link the hubs;
  `/tools/<provider>` links every job page it answers (`_jobs_by_provider`) and each job page links
  workflows that chain it (`_workflows_by_capability`), both derived from the rendered tables.
- **`catalog.css` is stamped `?v=<mtime>`**; it has a real `max-age`.
- **Counts are never typed.** Headline numbers come from `catalog_store.headline_counts` through
  `_fill_headline` (`{ENDPOINTS}`/`{PROVIDERS}`); `marketing/landing/build_html.py` emits the
  placeholders. Untemplated copy (`tutorial.js` and mirrors, `README.md`, the CLI) states no count.
  `test_no_page_types_the_catalog_size` holds this.
  Catalog tiles count only their browse surface (`catalog_store.HIDDEN_KINDS`).
- **Routed rows and a vendor named "treg" never appear publicly.** Every public projection filters
  through `_pub` (`catalog_store.browsable`: hidden kinds and `kind: routed` out); `/tools/treg`
  404s (`test_routed_rows_never_surface_a_provider_named_treg`).

## The social card

`assets/brand/og-card.html` is the **source**; `src/treg/web/media/og.png` is the render. Open the
HTML at exactly 1200×630 in a headless browser and screenshot it. The provider favicons are fetched
at render time and baked into the PNG, so the shipped card has no runtime network dependency.

Every brand on the card is a real provider — checked against `catalog_store.load()`, after an early
draft showed Ahrefs, which treg does not carry. LinkedIn's mark is inlined because its Google s2
favicon only resolves at 16px and falls back to a generic globe at 64.

Per-platform cards (`/media/og/<slug>.png`) are a deliberate follow-up. Until then every catalog page
points at the shared one.

## The agent pages — `/agents/<agent>`, and the hub at `/agents`

"I use ChatGPT — what can it do now?" answered on one server-rendered URL per client. The first is
`/agents/chatgpt`; the set is the keys of `agent_pages.AGENTS`, and nothing else (an unknown agent
404s). They came out of the programmatic-SEO plan in `https://github.com/superdesigndev/treg-internal/blob/main/docs/marketing/pseo-build-spec.md`: the measured
demand is for the *agent* ("chatgpt connectors") and the *platform* ("linkedin api pricing"), never
for "how to <job> in chatgpt", so the job list lives on the agent page as rows, not as URLs.

**The hub at `/agents`** (2026-08-31) is one card per client off `AGENTS` — name, the `definition`
sentence with the counts formatted in, a link. It exists because the discovery pass gave every
surface an "Agents" nav link with nowhere to point it: the link went to `/agents/claude-code` (one
client's page standing in for all of them) while the bare `/agents` URL 404ed. The nav now points
at the hub, the agent pages' breadcrumb carries it as the parent (treg.to / Agents / <name>), and
the sitemap lists it at 0.8 beside the other two hubs. Hosted-only and adtrack'd like everything
else off `_page()`; no `.md` mirror, matching `/use-cases` and `/workflows`.

**One skin for both page types.** The agent and use-case pages render with `usecase.css`, the
landing-page skin the five outcome pages already use, passed to `_page(css=...)`: centered hero with
a kicker pill and CTAs, `seclab` labels above each `h2`, real `<table>` comparisons in a `tablewrap`,
the dark `promptbox` with a copy button, `steplabel` numbered steps, `cards` grids, `pricewall` for
the money, and the dark `final` band. The stack of `.ep` rows the first cut used is gone: a job menu
and a provider comparison are tables, and the endpoint inventory belongs on the catalog shelf, which
the pages link to rather than reprint.

**The economics block** (`pricewall`) anchors a per-call price against a subscription: "instead of
$34/mo (Hunter, at list) → you pay $0.89 for 100". Plan prices come only from
`agent_pages.PLAN_PRICES`, which mirrors `marketing/landing/_facts.md` F-20..F-23 and records where
each figure was sourced; a page names a provider's plan price only if it is listed there. With none
listed the anchor falls back to the catalog's own spread (dearest vs cheapest for the same 100
calls), because an invented subscription number is worse than no anchor.

**Two halves, one rule each.** The hand-written half lives in `src/treg/agent_pages.py` — a module
with no heavy imports so it costs the light CLI nothing and can be reviewed without reading routing
code. It holds `ROLES` (the rotating "for *SEO experts / social media managers / SDRs*…" line; the
H1 itself is the keyword and the promise — "The ChatGPT Connector: call {n} APIs without keys" —
because a persona in the H1 read as the page's audience, and the first role is server-rendered on
the roleline so a crawler still gets a full phrase), the install
steps and screenshot, one example prompt per category, the FAQ, and `USE_CASES`: the buyer's menu —
plain-words jobs ("Find professional emails", "Find creators by keyword") under fourteen buyer
categories, each mapped to the capability ids that do it. That taxonomy is the map of the whole
site, and it is re-cut whenever the catalog grows, so **it is metadata and never a URL** (see the
use-case pages below). A row links to its page once one exists. The route projects
the rest from `catalog_store.load()` per request — the union of providers, the lowest USD price
via `cost_view`, verified counts, one chip per platform — and the counts in the title are computed.
`tests/test_agent_pages.py` asserts every capability id in `USE_CASES` exists in the catalog, so a
job the catalog cannot do cannot be advertised and a renamed capability fails the suite instead of
silently dropping a row. Never a row per endpoint — that is the banned page-per-endpoint in list form.

**One axis per category, and sub-headings where the buyer needs depth.** The first cut mixed two
axes: "Connect your own accounts" named an *access mode*, so Google Analytics sat beside Business
Profile reviews for the only reason that both authenticate with the team's own key, while the buyer
looking for either was reading a different page. A category now names one thing only: what the job
is about. `test_one_axis_only_no_access_mode_categories` holds that, and two more tests hold that no
job appears in two categories and no two jobs share a capability set (which is how a genuine
duplicate was found).

Data enrichment is the killer use case, so it carries twenty-five of the ninety jobs, and its four
stages — find companies, find people, contact details, enrich a record — render as sub-headings
inside the one section, driven by `CATEGORY_GROUPS`. They are **not** categories: they are stages of
one motion, and promoting them would have committed four URL segments to a distinction that only
exists in a practitioner's head. The section builder orders rows by group and prints a divider row
before each; the `.md` mirror sorts by the same order.

**Hosted only.** The copy describes treg.to's own listings — the ChatGPT Connectors entry, the $1.00
grant — none of which is true of a self-hosted registry. `_hosted()` checks `public_url` against
`PUBLIC_HOST_ALIASES`; elsewhere the route 404s and the sitemap omits the rows, rather than lie.

**One spelling per page.** Lookups are case-insensitive, but both routes resolve the slug to the
table's own key and 301 any other casing to it (`/agents/ChatGPT` → `/agents/chatgpt`). Two
reasons: a differently-cased URL would otherwise serve a 200 whose canonical points at itself, a
duplicate page; and the slug reaches the canonical, the `rel=alternate` href and the JSON-LD
breadcrumb unescaped, so it must come from the table, never from the request (CodeQL
`py/reflective-xss` flagged exactly this).

**`Disallow: /app` is a prefix rule** and would have blocked `/agents/…` too. `robots.txt` carries an
explicit `Allow: /apps/`; the longer match wins. The test asserts the Allow line exists.

**The shell's CTA now carries `?ref=<page>`.** `_page()`'s "Start free" used to link bare `/app`,
which bounces a logged-out visitor to the landing with nothing open — the dead end this fragment
already documents for the catalog pages. The app boot treats `ref` as a use-case CTA (no bounce,
sign-in opens in place), so every server-rendered page now gets that behaviour and the page that
produced the signup is recorded. Schema on the page: `SoftwareApplication`, `BreadcrumbList`, and
a `FAQPage` whose questions are asserted to appear verbatim in the body.

The public sign-in dialogs, including Astra's native dialog, share `media/signin-sso.js`: email
code is the primary action, with company SSO below it as an alternate mode. Selecting SSO
keeps the email field, makes **Continue with SSO** primary, and offers a return to email code. Company
discovery chooses the verified team
route and never grants access itself. The direct employee link remains available when discovery
cannot disambiguate teams. The dashboard dialog uses the same mode switch.

**An agent page has to be its own page, not the template with a name swapped** (2026-10-06). The
first four were 95-98% identical word for word, and Google indexed `/agents/chatgpt` and left
`/agents/claude-code`, `/agents/cursor` and `/agents/claude` "Discovered - currently not indexed" or
unknown. Three optional keys on an `AGENTS` entry fix that without forking the route:

- `h1` replaces the generic "The <name> <noun>: call {n} APIs without keys".
- `guide` is a list of hand-written sections (`id`, `seclab`, `h2`, `html`) rendered between the
  install steps and the menu, and as Markdown in the `.md` twin (`_guide_md`, which maps the small
  fixed vocabulary the fragments use: p, pre/code, ul/li, a, b, code).
- `focus` names the categories printed in full, in that order. The other categories collapse into
  one "Everything else" table, a row each linking to `/use-cases#<category>`, so the page still
  reaches every job. Reprinting all fourteen tables is what made the pages identical.

`/agents/claude-code` uses them to lead with lead enrichment (the four routed calls, the 23 Sep lead-list receipt, MCP vs CLI vs skill, the work-email
bench). `/agents/hermes` is new: the `~/.hermes/config.yaml` block from Hermes's documented MCP config
(`treg mcp install` detects Hermes but only prints manual instructions; it does not write YAML), then a weekly buying-signal check on Hermes's own
scheduler; treg.to answers the calls and neither schedules nor delivers. An agent without these keys
renders exactly as before. Tests hold the overlap with the template page under 75%, every
`treg call <id>` in a guide to an existing endpoint, every guide link to a 200, every category
reachable from a focused page, and the Hermes block to the same shape as `mcp_install`'s hint.

## The use-case pages — `/use-cases/<job>`, and the hub at `/use-cases`

The spokes. **The reader does one thing, the prompt; everything else is what the agent sees before
it calls.** Above the fold: the setup line, one prompt with a copy button, four "why this prompt
works" cards, an optional screenshot. Then "Why go through treg.to" (`WHY_TREG`, six cards).

The page then takes one of **three forms, chosen from the catalog rather than by hand** — this is
what makes it a template rather than one page's prose:

| Form | Condition | Renders |
|---|---|---|
| `short` | one provider | "How it works": the one call. Own-account copy when the cost is `free`; otherwise the rate and the $0.000 markup. No comparison |
| `platforms` | the job spans several platforms | providers grouped per platform, cheapest claimed per platform |
| `compare` | several providers, one platform | the full comparison |

Of the 90 jobs on the menu, roughly a third are single-provider and a third span several platforms,
so two thirds of the eventual pages are not the plain comparison the first page was built for.

**The URL is flat, and the category is metadata.** `/use-cases/<job>`, with the category carried only
in the breadcrumb, the hub heading and the agent-page section. This is the whole point: the taxonomy
gets re-cut as providers arrive, and **a re-cut must never move a page Google has indexed**. The
nested form that shipped first (`/use-cases/<category>/<job>`) is live and indexed, so it 301s to the
flat form rather than 404s, and `test_use_case_urls_are_flat_so_a_recut_never_moves_them` holds the
shape. Composio's pSEO does the same thing for the same reason. The category breadcrumb points at
`/use-cases#<category>`, so the hub is the parent of its own cluster rather than the ChatGPT page.

**Cheapest is claimed per billing unit, never overall.** Most jobs mix per-call, per-result
and per-success endpoints, and ranking those by USD per chargeable event names the wrong winner: one
call returning a thousand rows is not dearer than one row. The page prints "cheapest per found",
"cheapest per call" and so on, and says the units are not interchangeable when more than one appears.

**Providers are keyed by (provider, platform), not provider.** ScrapeCreators serves Instagram and
YouTube for the same job; collapsing on provider alone silently dropped a whole platform from a
multi-platform page.

**The reliability section renders only when there is traffic.** `endpoint_stats.observed` is empty
for most endpoints, and an empty promise is worse than no section. When it does render it names
per-vendor success rate, median latency and sample size (publication approved by Jason 2026-08-21)
with the "live traffic, not a controlled benchmark" caveat.

**Nothing job-specific or agent-specific is in the route.** The example client is
`agent_pages.DEFAULT_AGENT`; the job's own words, result noun, "what is X" heading, notes, FAQ and
`voices` all come from `USE_CASE_PAGES`, keyed by the job slug alone. A spec's `label` must
match a row of `USE_CASES` exactly (tested), which is how the agent page knows to link the row to
its page. `tests/test_agent_pages.py` asserts the route source contains no job-specific string.

**`voices`** is the section that cannot be regenerated: real questions from Reddit and X, quoted
verbatim with a link, each followed by what the page can honestly do about it (including "no
comparison table can answer this"). That research runs with `agent-reach` before any page is
written, and has to spot the vendor astroturf that dominates these searches. It is not decoration: on the YouTube pass roughly half the corpus was
vendor-written, thirteen distinguishable clusters, one posting the same body to three subreddits
seven seconds apart. `voices` renders in HTML and in the `.md` mirror, and is optional in the spec
(two of the first seven pages ship without it), so `test_no_use_case_page_ships_with_an_empty_section`
requires `voices` and `voices_intro` together rather than requiring either.

**The section order is comparison, then voices, then notes, then background, then FAQ**, with an
optional "Where it goes wrong" block (`failure_modes`, the workflow pages' shape, at least four)
between background and FAQ on the pages that carry one. Copy inside `voices`,
`notes` and `faq` that says "the comparison below" is pointing backwards; the first written pages
say it anyway. Write position-neutral ("the comparison above", "the prices here") or the sentence
is wrong for every reader who scrolls.

**Written so far: 42 of the 90 jobs, and the measured-demand worklist is complete** (2026-08-29). From 2026-08-24 the remaining set was no longer "all of them": every unwritten job was measured against Google Ads keyword volume that day; the 34 clearing 50 US searches a month became a worklist ordered by volume, written five a day, and the rest are parked as rows on the menu with no page. A page nobody searches for is the scaled-content shape the risk audit says to avoid, so the 48 parked jobs are a decision rather than a backlog.

The YouTube & video cluster (transcript, video stats, channel stats, search, comments) landed
2026-08-21 and is the first `compare`-form cluster where one row is
free: the official Data API on the reader's own connected Google account, at $0.00 with a 10,000
unit daily quota. The free row is deliberately excluded from the "cheapest per unit" claim, because
`_uc_providers` only ranks rows with a truthy USD price, and a free-but-rationed row is not a
cheaper version of a metered one. Those pages carry the quota arithmetic instead, which is what the
research said people actually get stuck on.

**A single provider on a trial pool is a third `short` state** (2026-08-26). The `short` form
branched on the row's `free` flag: own-account copy, else `metered_single`. Finnhub's company news
is one provider, not free, with no USD and a 50-call daily allowance, so it would have rendered
"metered from your team's balance". `trial_single` now states the allowance and the own-key
fallback in the description, the `.md` and the "How it works" section; the hero and `{cheapest}`
already handled it through `free_words`. Found the usual way, by rendering the page after 88 green
tests.

**A platform label is catalog vocabulary, and a page cannot override it.** The ads page groups
SerpApi's Ads Transparency Center engine under the `google` platform, whose catalog label is
"Google Keyword Data"; the heading is wrong for that job and right for the SERP jobs. Fixing it
means renaming the platform in the catalog, not the page, so it is flagged rather than patched.

**Demand keeps outrunning the worklist term** (2026-08-26). `slack mcp` 4,400 and `slack mcp
server` 1,900 against `slack bot api` 260, the fifth time `mcp` has beaten `api`; `google index
checker` 590 against `google indexing api` 260, and the Indexing API is the wrong API for the
job, so the page carries the checker term and says so; `financial news api` 170 sits beside
`stock news api` 210.

**`{cheapest}` expands to a bare price, so the lede must carry the preposition** (2026-08-27).
On a metered page it becomes `$0.002`, on a trial-pool page the `free_words` phrase, so "one key,
{cheapest}, at the provider's rate" reads "one key, $0.002, at". Write "from {cheapest}" and let
the phrase follow. Three of the 2026-08-27 pages shipped the bare form past 116 green tests and
were caught by reading the `.md`; the same pass caught a note calling Majestic unpriced while the
table printed $0.0008 per result for it, because `cost_view` converts index item units to USD.

**Demand keeps outrunning the worklist term, sixth time** (2026-08-27). `coingecko api` 1,300
against `crypto price api` 170, so the crypto page's H1 leads with CoinGecko; `reddit api` 5,400
and `reddit mcp` 590 against `reddit search api` 140; `free backlink checker` 2,900 and `ahrefs
api` 320 against `backlink api` 140, with Ahrefs not in the catalog, which the page says in its
first paragraph; `competitor keyword research` 1,300 and `semrush api` 720 against `competitor
ppc keywords` 140. The Glassdoor term held: `glassdoor api` 210, `glassdoor scraper` 110.

**A `related` card resolves by label, not inside the current category.** Four categories carry
fewer than five jobs (advertising and market research three, e-commerce and local businesses four),
so their pages have to point at least one of their four cards outside the category. The card used to
look the label up in the current page's category and, on a miss, fall back to that category's anchor
under a caption naming that category: a wrong link nothing failed on, because the test only asks
whether the label exists somewhere on the menu. The 66 labels are unique, so `_related_link` finds
the owner from the label alone.

**A row with no dollar price is not a free row.** The price cell had one `else` branch and it read
"free, your own account" in green. Semrush prices both SERP jobs in API units bought up front, so
its `cost_view` carries no USD and the page labelled the dearest option on it as free on the
reader's own account. Free is now read off the cost's own `type`; anything else without a figure
prints "no dollar rate published", which is what the pages say about Semrush in prose too. It was
found by reading the rendered page, which is the argument for that step in the skill.

**A trial-pool row is a fourth state, and a metered single provider is not an own-account one**
(2026-08-25). Finnhub, Tiingo and Twelve Data are served at $0 on treg.to's own free-tier keys with
a per-team daily allowance (`catalog.trial_pools`); `cost_view` gives them `usd == 0`, so they fell
through to "free, your own account", and with no priced row on the page the hero and the `{cheapest}`
placeholder said the same. `_uc_providers` now carries `trial` (calls per team per day) and the
cell, the `.md` table, the hero and `{cheapest}` state the allowance ("free, 50 calls a day on
treg.to's key, then your own key"). Separately, the `short` form assumed its one provider was an
OAuth connection; the AI-mentions job has one provider, DataForSEO, and it is metered, so the form
branches on the row's `free` flag: `metered_single` states the rate and the markup, and the meta
description does not claim "never metered". Both were found the same way as the Semrush one: by
reading the stock and AI-visibility pages after the tests went green.

**`{cheapest}` is the cheapest of ONE unit, not of the page** (2026-08-28). `_uc_providers` groups
rows by billing unit and `{cheapest}` expands to `cheapest_by_unit[units[0]]`, whichever unit is
found first. On a mixed-unit page that is not the lowest number the reader can see: the keyword
volume job printed "from $0.09" (DataForSEO's flat per-request row) above a table whose first line
is Serpstat at $0.0005 per keyword, and the LinkedIn profile job printed "from $0.0015" above a
$0.001 row. The comparison block itself is correct, because it prints a cheapest per unit with the
units-are-not-interchangeable caveat; only the interpolated lede lies. Both ledes now state the
rate in prose instead. **Do not write "from {cheapest}" on a page whose providers meter in more
than one unit**, and read the rendered lede against the rendered table before shipping. Found the
same way as the two above.

**A provider whose only row has no cost took the page down** (2026-08-29). `_uc_providers` built the
trial allowance with `max()` over the rows that have a `cost_view`; TikHub's LinkedIn comments v2 row
carries no cost at all, so on the comments job the generator was empty and the page 500ed past every
green test (the tests render other jobs). `default=0` now; the cell prints "no dollar rate published".

**Routed rows are off every public surface, not just comparison tables** (2026-08-31). PR #242's
first-party routed endpoints (`treg.<capability>`, `kind: routed`) were leaking into `_uc_providers`
as a fake "treg" provider row — and, found while fixing that, into every other public projection of
the catalog: the agent-page menu counted "treg" as an extra provider on every routed job, the
use-case hub's card metas did the same, `_provider_rows` published a self-referential `/tools/treg`
page into the sitemap, and `_catalog_census` counted the 76 meta-rows on top of the children they
delegate to. `_pub()` in `routers.web` is now the one filter every public page reads (hidden kinds
plus routed), `/tools/treg` 404s (the all-rows-hidden fallback in `tools_provider` no longer
resurrects routed rows), and the advertised tool count dropped accordingly (2,745 → 2,669). The
public name is treg.to; a bare "treg" vendor row must never appear on any page —
`test_routed_rows_never_surface_a_provider_named_treg` pins it.

**Pages with a free own-account row use a filtered WHY_TREG** (2026-08-31). `WHY_TREG` contains
cards like "One key, not 9 accounts" and "Already pay Hunter? Register it..." that are false
wherever the reader's own connected account does the job. That is the short own-account pages (GA4,
Search Console) — and also the YouTube comparison pages whose official Data API row is a $0.00
own-account row, so the condition is `any(p["free"] for p in provs)`, not "short form only" (the
first cut missed the YouTube pages). Those pages render `WHY_TREG_OWN_KEY` instead, keeping only the
cards that stay true ("No code to write", "Nothing to integrate").

**Possessive slugs 301 to clean slugs** (2026-08-31). Five use-case pages shipped with possessive slugs
containing `-s-` (e.g. `get-a-video-s-transcript`, `a-company-s-email-format`). Before GSC indexed them,
the keys in `USE_CASE_PAGES` were renamed to clean slugs (`youtube-transcript-api`, `company-email-format`,
etc.) and `USE_CASE_REDIRECTS` maps old to new. The flat route checks `USE_CASE_REDIRECTS` first and 301s, and the nested legacy route resolves
through the same map before its own lookup (it used to reject a renamed slug first, turning the
promised 301 into a 404 on the nested shape);
the old slugs are not in the sitemap (only `USE_CASE_PAGES` keys appear) and the canonical is on the
new slug. Redirects: `get-a-video-s-transcript` -> `youtube-transcript-api`,
`a-channel-s-profile-and-lifetime-stats` -> `youtube-channel-stats`, `a-video-s-comments` ->
`youtube-video-comments`, `a-business-s-reviews` -> `business-reviews`, `a-company-s-email-format` ->
`company-email-format`.

**The related-card test hard-coded the agent-page anchor** (2026-08-29). It asserted the email-finder
page links to `/agents/chatgpt#`, which was only ever the fallback for a related label with no page;
the day "A company's email format" got one, the assertion had nothing to match. It accepts a
`/use-cases/` sibling now.

**Demand outran the worklist term again, seventh time** (2026-08-29): `company email format` 140 and
`email format checker` 1,300 (which is validity checking, the verify page) against `email pattern
finder` 90; `social listening tool` 4,400 and `instagram comment export` 260 against `social listening
api` 70; `companies by industry` 2,400, `apollo api` 1,000 and `crunchbase api` 390 against `company
list by industry` 70; `indeed api` 720 and `jobs api` 590 against `job board api` 50, with no Indeed
row in the catalog, which the page says in its first paragraph; `yahoo finance api` 2,900, `polygon
api` and `alpha vantage api` 1,600 each against `historical stock data api` 50, with neither Yahoo
nor Alpha Vantage in the catalog, said in the lede.

The five flat ad pages predate all of this, keep their URLs and their `build_html.py` ownership, and
are served first by the same flat handler; `test_legacy_flat_use_case_pages_still_answer` proves a
rendered job page cannot shadow one. `/use-cases` is the crawlable hub they hang from; before it existed the only link into a spoke
was one row on one agent page. All hosted-only and sitemapped; the RENDERED job pages are `.md`-mirrored like the agent pages, but the five flat ad pages are not — their route serves no `.md`, which is why the build stopped advertising alternates for them.

### The five campaign hub pages (2026-08-31 rewrite)

The five Google Ads landing pages (`/use-cases/seo-data-for-ai-agents`, `/use-cases/lead-enrichment-for-ai-agents`,
`/use-cases/social-trend-research-for-ai-agents`, `/use-cases/competitor-ad-research-for-ai-agents`,
`/use-cases/company-research-for-ai-agents`) are built from markdown sources in `marketing/landing/` via
`build.py` and `build_html.py`, served as static HTML with `{BASE}` templating applied at request time.

**Title matches H1, and both carry the measured buyer term.** The shipped H1s: "SEO Data: Google
Results, Keywords and Backlinks", "Waterfall Enrichment: Find and Verify Work Emails", "Social Data
MCP: Reddit, Instagram, TikTok, YouTube", "Ad Library API: Meta, Google, TikTok, LinkedIn Ads",
"Company Research: Funding, Headcount and Leadership". Per-vendor MCP keywords still belong on
`/tools/<provider>`; a category-level term ("social data mcp", "ad library api") may lead a hub when
it is the measured phrase.

**CTAs are "Start Free" and "Paste llms.txt".** The primary CTA links `/app?ref=<page_id>`, the
secondary links `/llms.txt` directly. The copy-paste prompt in each page's workflow section is the
action the page exists to produce.

**JSON-LD: BreadcrumbList and FAQPage.** Every page carries both schemas. The breadcrumb names
"treg.to" (never bare "treg") as the root. FAQ pairs are extracted from the "Before you sign up"
section during build.

**What the 2026-08-31 review fixed in the build** (each shipped past green tests and was caught by
reading the rendered pages): the hero's fenced prompt rendered as `<code>text\n…` — `render_hero`
now strips the fence with `code_text` and gives it the copy affordance, and the bold price line
under it (previously dropped) renders as the subline. The FAQ parser only knew full-line bold
questions, so the rewritten `**Q?**: answer` one-liners folded several visible FAQs into one
JSON-LD acceptedAnswer; it now splits the one-line form first. The kicker was hand-typed
("2,600+ tools · 40+ providers") — it is now read from the catalog at build time and floored to a
bound (F-01's convention: a static page states a rounded-down claim that stays true as the catalog
grows). `sitetrack.js` had been dropped in the rewrite (the attribution test caught it) and is
restored before `adtrack.js` on all six files. The advertised `.md` alternates are gone — the
legacy-hub route serves no `.md`, so every one 404ed. The brand anchor reads `treg.to`. And the
lead-enrichment "Proof from one real run" block no longer shows the 1-email $0.0245 demo: it
carries the receipt of the 50-company workflow run (2026-08-26, $3.62, $0.13 per deliverable
lead) and points at `/workflows/find-and-verify-a-lead-list`, so the hub sells the workflow
instead of competing with it. That page now headlines the gated 2026-09-23 re-run and keeps
the 2026-08-26 total in its narrative as the before, so the hub's block names its run as the
ungated first one; `/pricing` and `/people-search` carry the 2026-09-23 receipt.

**Links to job pages, not competing with them.** The "Next steps" section links real job pages and
workflows: lead-enrichment links `/workflows/find-and-verify-a-lead-list` (the receipt of a real run) and
`/use-cases/find-professional-emails`; SEO links keyword and SERP job pages; social links creator and
trending job pages. The hubs sell the job pages, not cannibalize them.

**No hardcoded numbers.** Every figure on the page comes from `catalog_store` or a real run receipt.
The workflow receipts (e.g. the lead-list total) are hand-recorded from actual runs, not
rate-card estimates.

**`{BASE}` templating.** The canonical URL and `og:url` use `{BASE}` in the HTML, substituted at
request time by `routers/web.py` reading and replacing before returning `HTMLResponse`. This is the
same pattern as `landing.html` and the legal pages.

## The workflow pages — `/workflows/<slug>`, and the hub at `/workflows`

A use-case page answers one job; a workflow page is **the sequence a real person runs**, as ONE
paste-in prompt. It renders, in order: the setup line and the prompt (copy buttons), four "why this
prompt works" cards, a **step table** with a per-step price pulled live from the catalog (the
endpoint the worked run used, its `cost_view` price per billing unit, how many providers do the
step, observed success rate and p50 when there are samples, and a link to the step's use-case page
resolved through `USE_CASES` by capability — or the category anchor on the default agent page when
no page is written), a worst-case total (`price × rows_in` if every call hits), then **the receipt**
of a real run (`id="run"`), `WHY_TREG`, the failure modes (at least four), the FAQ (four to six
entries; a use-case page stays at exactly four), and four related cards.
JSON-LD: BreadcrumbList, a `HowTo` whose steps are the table rows, and a FAQPage. `.md` mirrors it
all, ending with `HTML version: …`. Hosted-only, sitemapped (hub 0.8, page 0.7) and case-folded to
the canonical slug with a 301, exactly like the use-case pages.

The data lives in `agent_pages.WORKFLOWS`, one dict per slug: `steps` are
`(name, capability, what the agent asks, endpoint the run used, why)` tuples. A step whose
capability is `decision` is a judgement on rows the earlier steps fetched, not a fetch: jev reads
the row and returns a probability. jev is not a catalog capability (the run goes through the
team's own TypeSafe key), so `_wf_steps` prices it from `agent_pages.DECISION_STEPS` (provider,
domain, list rate per verdict, unit, link), the one place that rate lives, and the table's
success-rate cell reads "a verdict on rows already fetched" instead of a measured rate. The
`.md` twin and the hub's per-row price read the same dict. `run` holds the
`date`, `rows_in` (and an optional `rows_noun`, default "companies", for the "N companies in"
line), the `receipt` label/value pairs, `cost_usd`, the narrative paragraphs and the
CSV path. **Prices are never written into the copy**: the step table prints the live catalog
rate, so a number in `why`, the FAQ or the narrative is a second source of truth that drifts
(the 2026-09 SEO batch shipped hunter at $0.003 against a catalog $0.01225). The receipt is the
one place a dollar figure belongs, because it records what one dated run actually cost. **The receipt and the CSV are hand-recorded from a real run and dated** — the page
prints them verbatim and computes nothing from them; only the per-step prices are live. The CSV is
shipped in the package at `src/treg/workflow_runs/<slug>.csv` and served at
`/workflows/<slug>.csv` (404 when the file is missing). The published CSV carries **row-level
outcomes only** (`person_found`, the finder, the verdict, catch-all, news) — never a name, title
or address: these are real people and a title at a named company identifies one. A spec's `once`
tuple names the endpoints called once per run rather than once per row (Apollo's list page); the
"at the rates above" total and the hub's per-row price read it, so the list step is 1 × its price.
The rule: **a workflow page is not written
without a real run behind it.** A page whose receipt is a rate card is the thing this page type
exists to not be.

Six workflows ship as of 2026-09-14: the lead list, and five from the SEO batch (creator
discovery, creator screening, keyword demand to ad budget, competitor Meta ads, TikTok plus
Xiaohongshu category intel), each with a run made through the treg CLI on 2026-09-14 and its
CSV in `workflow_runs/`. Their CSVs carry row numbers and stats, never handles.

The lead list was re-run on 2026-09-23 with two jev decision steps (the Jev × GTM plan: update
the existing page, never add a route): an ICP gate after the Apollo list, on the list fields
alone, with a 50% threshold, and an opener score after the news step. Same filter, same slug,
seven steps. The receipt keeps the 2026-08-26 run's total and lead count in its narrative as the
before, and says plainly that the dropped rows are the one thing the run cannot measure. The
CSV gained `opener_score`, `jev_fit` and `gate` columns after the original prefix
(`test_workflow_page_is_served_with_the_crawler_essentials` pins that prefix) and is sorted
strongest opener first. The run was made with `httpx` against `/call/` directly (four in
parallel, a browser-like `User-Agent`, since Tomba and Findymail 403 the Python default); the
gate and opener went through the team's `typesafe` own tool at `/call/typesafe/v1/systemone`, so
jev's cost is stated at list price and marked as not metered. Tomba was out of capacity on
treg.to's key for the whole run, so Hunter served and Kitt took Hunter's misses; that is the
"cheapest provider is out" failure mode with a new name on it. Its `extra_links` now open with
`/jev`, the one link from a workflow page to the Jev landing.

**Retitled for the agent phrasing (2026-10-06).** The sentence and title now read "AI lead generation in Claude: a verified B2B lead list…", keeping
the head term and adding "claude lead generation", whose results page is held by small sites. Jev is
two of the seven steps, so it stays in the lede, the steps and the FAQ, not the title. Three optional
`WORKFLOWS` keys carry it, and every other workflow renders as before:

- `description`: a hand-written meta description, replacing the generated one that was cut mid-word.
- `agent`: the example agent for this page (`claude-code`), so the steps heading reads "What Claude
  Code calls"; the use-case pages and the other workflows keep `DEFAULT_AGENT`.
- `sections`: hand-written sections after the receipt (trusted static HTML, `.guide` styling, and in
  the `.md` twin via `_guide_md`). The first is "What lead generation in Claude costs: recorded data costs" (metered data calls, not the Claude plan): this
  run's $0.12 per verified contact against the ungated run's $0.13, and the 16 Sep email bench.

`/jev` links back to it from the buyer-signal recipe's setup strip and from a new FAQ entry.
`test_the_lead_list_page_names_claude_and_carries_its_tested_section` holds the title, the
description, the agent override staying on this page, and FAQ/FAQPage parity.

Tests: `test_workflow_page_is_served_with_the_crawler_essentials` (crawler plumbing, HowTo with the
step count, `.md`, `.csv`, hub, 301, sitemap), `test_every_workflow_step_capability_and_endpoint_exist`,
`test_no_workflow_ships_with_an_empty_section`, `test_workflow_copy_has_no_em_dashes`,
`test_every_workflow_run_has_its_csv_on_disk` and `test_every_workflow_csv_route_serves` (a
receipt with no file behind it is exactly the fabricated-run failure these pages exist to avoid).

## Counts

The two headline numbers come from `catalog_store.headline_counts` (direct endpoints rounded down
to the hundred, and their providers) and are never typed: `llms.txt`, `skill.md`, the landing (title,
descriptions, JSON-LD, kicker, CTA), `/docs` and every bundled page served through `_static_page`
(the launch landings, `/resources`, the use-case pages, the legal and support pages) all read
`{ENDPOINTS}` / `{PROVIDERS}` through `_fill_headline` or the same call; `marketing/landing/build_html.py`
emits the placeholders rather than baking a number. Copy that is not templated (`tutorial.js` and its
two mirrors, `README.md`, the CLI) states no count at all. The landing once carried eight typed copies
that had drifted to 2,630/47 against a catalog of 3,600+/91, and six launch pages later disagreed
with each other the same way; `test_no_page_types_the_catalog_size` (tests/test_static_pages.py) scans
the front-door files for a typed catalog size, and `test_no_page_ships_an_unsubstituted_base` fetches
every sitemap page, use-case page and agent file for an unfilled placeholder. The landing title is `treg.to: OpenRouter for agent tools and data, pay per call`
(58 characters, matching the H1's positioning line) and its description names one MCP server, one
key and the data categories, with no count to go stale. Note the catalog index
shows the **whole** catalog, not the sum of its tiles: a tile counts only its browse surface, so the
account/utility endpoints — real inventory, listed on each shelf page — are excluded from tile counts
by `catalog_store.HIDDEN_KINDS`.

## Discovery — the hubs are linked, not just listed

Search Console on 2026-08-27 showed the 38 job pages, `/workflows` and `/agents` at zero
impressions, and URL inspection answered "URL is unknown to Google" for
`/use-cases/find-professional-emails` and `/workflows/find-and-verify-a-lead-list`. They were in
the sitemap and linked from nothing: the landing linked `/catalog` and `/resources` only, `/catalog`
linked `/tools/*` only, `/resources` linked the five outcome pages only — and those five were the
only non-homepage URLs with impressions. A sitemap is not a crawl path.

What links what now, and where it is generated:

| From | To | Where |
|---|---|---|
| footer of every server-rendered page (Explore / Build / Company columns; the nav is unchanged by request) | `/use-cases`, `/workflows`, `/agents/claude-code`, `/showcase` and `/blog` — **hosted only**: those pages 404 on a self-hosted registry, so the links are gated by `_hosted()` (the landing wraps them in `<!--hosted-->` markers the route strips off-host) | `_page()` in `routers/web.py` |
| the landing footer (`landing.html`; the public catalog SPA has no footer and links the hubs from its prerender) | same four; the people-search, jev and use-case landings carry `/blog` in their hand-kept footers too | hand-kept markup, so `test_every_surface_links_the_three_hubs` walks `/` and `/catalog` |
| `/catalog` prerender | both hubs, in a sentence | `catalog_index` |
| `/tools/<provider>` "Used in" | every job page whose capabilities the provider answers | `_jobs_by_provider()`, cached per process from `USE_CASE_PAGES` × the catalog |
| `/use-cases/<job>` "Run the full sequence" | every workflow with a step on one of the job's capabilities | `_workflows_by_capability()`, cached from `WORKFLOWS[*].steps` |

Both reverse indexes are derived from the same tables the pages render from, so a new job or
workflow is cross-linked the moment it is routed, and nothing is listed by hand.

### Titles: Title matches H1

`/tools/<provider>` titles match their H1s:

- Metered: `{Provider}: {n} tools from {price} | treg.to` (falls back to `{Provider}: from {price} | treg.to`
  past 65 characters; with no price the primary is `{Provider}: {n} tools | treg.to` and the fallback is
  `{Provider} | treg.to`, which the H1 still starts with)
- Mixed (platform + BYOK): `{Provider}: {n} tools, platform or your own key | treg.to` (falls back to
  `{Provider}: {n} tools, platform + BYOK | treg.to` or `{Provider}: platform + BYOK | treg.to` past 65 characters)
- Own-account: `{Provider}: connect your own account | treg.to`
- **MCP-intent own-account providers** (`_MCP_INTENT_PROVIDERS`: google-search-console, google-analytics,
  semrush, snapchat-ads, pinterest-ads, meta-ads, tiktok-ads, facebook) lead with MCP instead:
  `{Provider} MCP: connect your own account | treg.to` for Title and H1, and the meta description
  names MCP plus connect-own-account plus treg.to as one MCP for the catalog. The set is the pages
  where GSC shows `{provider} mcp` or `{provider} connector` impressions with near-zero clicks.
  The MCP-intent titles win over the generic own-account title pattern for these providers.

The price label carries its own billing unit ("$0.00245/result", "$0.0089/call"), so the copy
never says "per call" beside it: a per-result or per-success rate is not a per-call one.
The kicker carries the measured line (calls observed, ok rate weighted by DECIDED calls, median p50)
read through `_observed_or_empty`. Descriptions go through `_serp_desc` (sentence-fit under
Google's cut) and may still mention pricing intent. The HowTo's steps mirror the visible setup section
in order — the one-line install first, direct MCP second — because schema describing a different
flow than the page shows is the mismatch Google treats as a violation. The setup line on these
pages is the canonical `set up treg — {base}/llms.txt` (the em-dash is the documented exception,
and a colon variant that shipped briefly forked the product's one paste-line).
- compare-form job titles get `, from $X` appended when the hand-written title carries no price and
  the result stays within `_TITLE_MAX` (65); " compared" is dropped to make room.

### IndexNow

`/{INDEXNOW_KEY}.txt` serves the IndexNow key (not a secret: the protocol only checks the key is
served from the host named in the submission), on every host, since IndexNow is generic.
`scripts/indexnow_submit.py` reads the live sitemap and pushes every URL to `api.indexnow.org`
(Bing, Yandex, Seznam, Naver share the feed). Google retired its sitemap ping; its resubmission goes through Search Console
(`google-search-console.x.webmasters-sitemaps-submit` in the catalog, owner OAuth). The route is
registered in `bootstrap.py`'s ownership table like every other public route.

Tests: `test_every_surface_links_the_three_hubs`, `test_provider_page_names_the_jobs_it_serves`,
`test_job_page_names_the_workflows_that_chain_it`, `test_compare_titles_carry_the_cheapest_price`,
`test_provider_title_matches_h1`, `test_indexnow_key_is_served_from_the_root`.

### Baidu push

`scripts/baidu_push.py` pushes every sitemap URL to Baidu's webmaster push API
(`data.zz.baidu.com/urls`, up to 2,000 newline-separated URLs per call). The property token
arrives through `TREG_BAIDU_PUSH_TOKEN` — env, never a flag. Same-host URLs only; exit is
non-zero when Baidu accepts fewer than it was sent (`success` < count).

### Named crawler groups in robots.txt

`robots.txt` names the domestic search/AI crawlers (Baiduspider, Bytespider, YisouSpider,
Sogou web spider, 360Spider) and the international AI answer engines (GPTBot, ClaudeBot,
PerplexityBot, Google-Extended) in their own `User-agent` groups. Robots semantics give a named
bot ONLY its own group — the `*` block stops applying — so every group repeats the full disallow
list verbatim; `test_robots_txt_names_the_domestic_and_ai_crawlers_explicitly` pins that
synchronization.

### Social links, one source

The marketing pages' social row fills from `{SOCIAL_LINKS}`, rendered by `_social_links_html`
out of `src/treg/web/social.json` — the same list `frontend/src/state/social.ts` serves the
dashboard (edit both together until a build step shares them). A platform the page already links
by icon is skipped, so a page keeps its hand-drawn brand icons and picks up the rest from the
token. `kind: "qrcode"` (WeChat) links to `/media/wechat-qr.svg`, a placeholder until the account
exists. Test: `test_marketing_pages_render_the_social_list_from_one_source`.

### Chinese mirrors (`/zh`)

`web/zh/<name>.html` files are Chinese pages of their own — separate indexable URLs
(`/zh`, `/zh/aeo`, in the sitemap), each with its own canonical, `lang="zh-CN"` and
`inLanguage: zh-CN` JSON-LD. `_hreflang_tags` injects the en/zh-CN/x-default cross-links into any
page whose zh counterpart exists, both directions, so a new mirror gets the pair the moment the
file appears. The bare `/` negotiates once: a Chinese-reading first visitor (Accept-Language,
unless the `treg-locale` cookie says otherwise, and only with a clean query string — referrals
and SSO landings never move) 302s to `/zh` with `Vary: Accept-Language`. The `/zh/{page}` route
404s for untranslated names rather than pretending. Tests: `test_zh_mirrors_serve_chinese_pages_
with_hreflang_both_ways`, `test_root_negotiates_chinese_once_only`.

### Agent pages name the workflows

`/agents/<agent>` (and its `.md` twin) carries a **Workflows** section listing every entry in
`agent_pages.WORKFLOWS` with its step count, between "The menu" and the category sections. Before
this the workflow pages were reachable from `/workflows` alone. `AGENTS["grok-bot"]` also carries
three Grok-Bot-specific FAQ entries (lead generation, research, what it cannot do yet) because
"grok bot lead generation" is the one emerging term in the outbound research that passed all seven
gates; the use-case map lives in `marketing/rebuild/06-grok-bot-use-cases.md`. Test:
`test_agent_pages_name_the_workflows`.

## Provider inventory and mixed access

`tools_provider` includes all active non-routed provider tools, including account/helper operations.
The browse census still excludes management tools. Mixed-access key-provider pages show total, platform + BYOK
and BYOK-only counts; each tool labels access, helper/account kind and verification. Small provider
inventories (up to 50) list every tool. Prices use the display units from `Catalog.cost_view`, and
notes explain composite or rounded billing. A tool counts as platform only when it is
platform-eligible AND the deploy holds an enabled key for its provider (`platform_key_for`, the
same two halves as MCP's `no_key_needed`); a keyless provider's page reads as own-key. Only those
prices inform the platform starting price. OAuth rows use account-connection language; configured billed OAuth calls are
labeled metered. The sample uses `call_template`, including the upstream method and inputs.

The landing redesign is released to all homepage visitors and is independent of Dashboard account
rollout. It has no old/new landing experiment. Logged-in visitors can revisit `/` and use Open
dashboard. The classic `gateway-loader.js` catches failed module downloads outside the Three.js
module graph and reveals the monochrome fallback. BFCache page transitions retain the scene and
resume the shared animation clock on restoration.
