"""One SystemOne call — the decision/evaluation protocol TypeSafe's Jev API speaks, and Alibaba
Bailian's `decision-model-preview` endpoint mirrors at `{base_url}/systemone`.

Infra: this module knows the wire format and nothing about search or quality checks. Like
`infra.judge` and `infra.embed` it never raises: a timeout, a non-200 or a malformed body comes
back as `answers=None` with a reason, and the caller (the relevance judge, the Web Arena check)
serves its fallback. No cache here — `infra.judge` already caches the judgements this feeds,
keyed by model, so answers from different endpoints never share an entry.

The wire format, one round trip regardless of question count:

    POST {base_url}/systemone           (base_url already ending in /systemone is used as-is)
    Authorization: Bearer <api_key>     (or the bare key when the deployment wants no scheme)
    {"model": "...", "state": {...}, "questions": {...}}
    → 200 {"answers": {...}, "usage": {"input_tokens": n, "output_tokens": n}}

`usage` may also spell its fields Vercel-gateway style (`inputTokens`); both are read.
"""
from __future__ import annotations

import logging
import time

import httpx

log = logging.getLogger("treg.llm")


def _url(base_url: str) -> str:
    base = base_url.rstrip("/")
    return base if base.endswith("/systemone") else f"{base}/systemone"


def _authorization(api_key: str, scheme: str) -> str:
    return api_key if scheme == "raw" else f"Bearer {api_key}"


async def systemone(state: dict, questions: dict, *, base_url: str, api_key: str,
                    model: str = "", timeout_s: float = 8.0, auth_scheme: str = "bearer",
                    transport: httpx.AsyncBaseTransport | None = None) -> tuple[dict | None, dict]:
    """Ask `questions` about `state`. Returns `(answers, meta)`.

    `answers` is the body's answers object, or None when the endpoint could not answer. `meta`
    carries `ms`, `input_tokens`/`output_tokens` when the body reports usage (either spelling,
    else None), and `error` — `timeout` | `http_<status>` | `bad_body` | `<ExceptionType>`,
    None when answered."""
    t0 = time.perf_counter()

    def ms() -> int:
        return int((time.perf_counter() - t0) * 1000)

    def meta(error: str | None, usage: dict | None = None) -> dict:
        usage = usage if isinstance(usage, dict) else {}
        return {"ms": ms(),
                "input_tokens": usage.get("input_tokens", usage.get("inputTokens")),
                "output_tokens": usage.get("output_tokens", usage.get("outputTokens")),
                "error": error}

    body = {"state": state, "questions": questions}
    if model:
        body["model"] = model
    try:
        async with httpx.AsyncClient(timeout=timeout_s, transport=transport) as client:
            r = await client.post(_url(base_url), json=body,
                                  headers={"Authorization": _authorization(api_key, auth_scheme)})
        if r.status_code != 200:
            return None, meta(f"http_{r.status_code}")
        data = r.json()
        answers = data.get("answers")
        if not isinstance(answers, dict):
            return None, meta("bad_body")
        return answers, meta(None, data.get("usage"))
    except httpx.TimeoutException:
        return None, meta("timeout")
    except (ValueError, KeyError, TypeError):
        return None, meta("bad_body")
    except Exception as exc:  # noqa: BLE001 — an abstaining endpoint, never a failed caller
        log.warning("systemone call failed: %s", type(exc).__name__)
        return None, meta(type(exc).__name__)
