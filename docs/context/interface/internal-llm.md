---
title: The internal LLM — a private SystemOne endpoint in front of the judge and the JEV check
status: shipped
sources:
  - src/treg/infra/llm.py
  - src/treg/infra/judge.py
  - src/treg/application/web_arena_quality.py
  - src/treg/application/find_index.py
  - src/treg/application/catalog_find.py
  - src/treg/application/search_experiment.py
  - src/treg/config.py
---

# The internal LLM

The two places treg itself asks a model — the relevance judge
(`infra.judge`, fed by `application.catalog_find` and `application.search_experiment`) and the
Web Arena JEV check (`application.web_arena_quality._jev`) — speak the **SystemOne wire format**:
`POST {url}` with `{state, model, questions}`, answered by `{answers, usage}`. TypeSafe's Jev API
and Alibaba Bailian's decision model (`{base_url}/systemone`, e.g.
`https://llm-….cn-beijing.maas.aliyuncs.com/compatible-mode/v1` with model
`decision-model-preview`) are the same protocol, so a private deployment is a drop-in, not an
adaptation.

`infra/llm.py` holds the one primitive, `systemone(state, questions, *, base_url, api_key, model,
timeout_s, auth_scheme)` — never-raise like `infra.judge` and `infra.embed`: a timeout, a non-200
or a malformed body come back as `answers=None` with a reason. It appends `/systemone` unless the
base URL already ends with it, sends `Authorization: Bearer …` (or the bare key with
`systemone_auth_scheme: "raw"`), and reads usage in either spelling (`input_tokens` /
`inputTokens`). No cache here — `infra.judge` already caches by `(model, query, ids, questions)`,
which separates endpoints for free.

## The fallback chains

`TREG_SYSTEMONE_BASE_URL` + `_API_KEY` + `_MODEL` — **all three** set — switch the suppliers;
anything missing leaves the originals untouched (the default, blast radius zero):

- **Judge**: `catalog_find.judge_endpoint()` (application — the decision lives in the caller,
  infra stays wire-only) returns the SystemOne tuple when configured, else `None`; both find v1/v2
  and the experiment unpack it or fall back to the `typesafe_*` trio. Each caller keeps its own
  timeout when TypeSafe serves; a configured SystemOne uses `systemone_timeout_s` (default 8.0 —
  decision models answer slower than the 2.5 s experiment budget, and an abstaining judge only
  costs the page its judged ordering).
- **JEV check**: `_jev` branches on `_internal_configured()`; `_take_budget` admits a call when
  the Vercel gateway key OR the SystemOne trio is configured. The SystemOne path records no
  `jev_cost_usd` — the endpoint's pricing is its owner's.
- **Embeddings**: `find_index.api_key()` already preferred `find_embed_api_key`, then treg's
  OpenRouter key on OpenRouter URLs; a private SystemOne deployment's key is now the third rung
  when the embeddings URL shares the SystemOne host (one credential for the deployment).

`jev_xboost.py` (the /jev page's live demo, a real bill through treg's own `/call/`) keeps the
Vercel gateway path; the internal endpoint does not touch it.

Env only, never a Secret row, never logged (`Field(repr=False)`); the API key is the DashScope
key when the deployment is Bailian. Tests: `tests/test_internal_llm.py`.
