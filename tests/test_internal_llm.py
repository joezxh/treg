"""The private SystemOne endpoint: `infra.llm.systemone`'s wire behaviour, and the fallback
chains that put it in front of TypeSafe's judge, the Web Arena JEV check and the embeddings key —
or leave every caller exactly as it was when nothing is configured."""
from __future__ import annotations

import json

import httpx

from treg.application import catalog_find as find
from treg.application import find_index
from treg.application import web_arena_quality as waq
from treg.config import get_settings
from treg.infra import judge as judge_infra
from treg.infra import llm

# ---- the wire primitive (infra.llm.systemone) --------------------------------------------


def _transport(body: dict | str | int, capture: list[httpx.Request] | None = None,
               status: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if capture is not None:
            capture.append(request)
        if isinstance(body, int):
            return httpx.Response(body)
        if isinstance(body, str):
            return httpx.Response(200, text=body)
        return httpx.Response(status, json=body)
    return httpx.MockTransport(handler)


async def test_systemone_answers_one_round_trip():
    seen: list[httpx.Request] = []
    answers, meta = await llm.systemone(
        {"task": "q"}, {"c0": {"type": "noul"}},
        base_url="https://llm.example.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        api_key="sk-dash", model="decision-model-preview", timeout_s=1.0,
        transport=_transport({"answers": {"c0": {"noul": 0.9}},
                              "usage": {"input_tokens": 11, "output_tokens": 3}}, capture=seen))
    assert answers == {"c0": {"noul": 0.9}}
    assert meta["input_tokens"] == 11 and meta["output_tokens"] == 3 and meta["error"] is None
    req = seen[0]
    assert str(req.url) == "https://llm.example.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/systemone"
    assert req.headers["Authorization"] == "Bearer sk-dash"
    sent = json.loads(req.content)
    assert sent["model"] == "decision-model-preview"
    assert sent["state"] == {"task": "q"} and "c0" in sent["questions"]


async def test_systemone_url_join_and_vercel_usage_spelling():
    seen: list[httpx.Request] = []
    answers, meta = await llm.systemone(
        {}, {}, base_url="https://gw.example/v1/systemone", api_key="k",
        transport=_transport({"answers": {}, "usage": {"inputTokens": 7}}, capture=seen))
    assert str(seen[0].url) == "https://gw.example/v1/systemone"
    assert answers == {} and meta["input_tokens"] == 7 and meta["error"] is None


async def test_systemone_raw_auth_scheme():
    seen: list[httpx.Request] = []
    await llm.systemone({}, {}, base_url="https://gw.example", api_key="RAW-KEY",
                        auth_scheme="raw",
                        transport=_transport({"answers": {}}, capture=seen))
    assert seen[0].headers["Authorization"] == "RAW-KEY"


async def test_systemone_never_raises():
    abstain, meta = await llm.systemone({}, {}, base_url="https://gw.example", api_key="k",
                                        timeout_s=0.01,
                                        transport=_transport({"answers": {}}, status=503))
    assert abstain is None and meta["error"] == "http_503"

    garbage, gmeta = await llm.systemone({}, {}, base_url="https://gw.example", api_key="k",
                                         transport=_transport("<html>not json</html>"))
    assert garbage is None and gmeta["error"] == "bad_body"

    answers_only, ameta = await llm.systemone({}, {}, base_url="https://gw.example", api_key="k",
                                              transport=_transport({"nope": 1}))
    assert answers_only is None and ameta["error"] == "bad_body"

    def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("slow upstream")
    none_, nmeta = await llm.systemone({}, {}, base_url="https://gw.example", api_key="k",
                                       transport=httpx.MockTransport(boom))
    assert none_ is None and nmeta["error"] == "timeout"


# ---- the fallback chains ------------------------------------------------------------------


def _patch(monkeypatch, **over):
    s = get_settings()
    for k, v in {"systemone_base_url": "", "systemone_api_key": "", "systemone_model": "",
                 "systemone_timeout_s": 8.0, "systemone_auth_scheme": "bearer",
                 "ai_gateway_api_key": "",
                 "find_embed_api_key": ""}.items():
        monkeypatch.setattr(s, k, v, raising=False)
    for k, v in over.items():
        monkeypatch.setattr(s, k, v, raising=False)
    return s


def test_judge_endpoint_off_by_default(monkeypatch):
    _patch(monkeypatch)
    assert find.judge_endpoint() is None


def test_judge_endpoint_needs_all_three_settings(monkeypatch):
    s = _patch(monkeypatch, systemone_base_url="https://llm.example/v1", systemone_api_key="sk-1")
    assert find.judge_endpoint() is None          # no model — the endpoint would refuse
    monkeypatch.setattr(s, "systemone_model", "decision-model-preview", raising=False)
    url, model, key, timeout = find.judge_endpoint()
    assert (url, model, key) == ("https://llm.example/v1", "decision-model-preview", "sk-1")
    assert timeout == 8.0


async def test_judge_serves_the_private_endpoint_when_configured(monkeypatch):
    _patch(monkeypatch, systemone_base_url="https://llm.example/v1", systemone_api_key="sk-1",
            systemone_model="decision-model-preview")
    seen: list[httpx.Request] = []
    judge_infra.clear_cache()
    j = await judge_infra.judge(
        "best tool for apple stock prices", [{"id": "ep1", "name": "n", "summary": "s",
                                              "capability": "c", "platform": "tiingo"}],
        api_key="sk-1", model="decision-model-preview", url="https://llm.example/v1/systemone",
        timeout_s=8.0,
        transport=_transport({"answers": {"c0": {"noul": 0.93}}, "usage": {}}, capture=seen))
    assert j.probs == [0.93] and j.error is None
    assert seen[0].headers["Authorization"] == "Bearer sk-1"


async def test_budget_gate_knows_the_private_endpoint(monkeypatch):
    # Nothing configured: the gate refuses before any spend or DB touch, whichever supplier set.
    _patch(monkeypatch)
    assert await waq._take_budget(1) is False
    # The private endpoint alone passes the gate (the DB admission behind it is worker territory).
    _patch(monkeypatch, systemone_base_url="https://llm.example/v1", systemone_api_key="sk-1",
           systemone_model="decision-model-preview")
    assert waq._internal_configured() is True
    monkeypatch.setattr(get_settings(), "systemone_model", "", raising=False)
    assert waq._internal_configured() is False


async def test_jev_uses_the_private_endpoint(monkeypatch):
    _patch(monkeypatch, systemone_base_url="https://llm.example/v1", systemone_api_key="sk-1",
           systemone_model="decision-model-preview")
    async def admitted(user_id):
        return True
    monkeypatch.setattr(waq, "_take_budget", admitted)   # the DB admission is not this test's unit
    calls: list[tuple[str, str]] = []

    async def fake_systemone(state, questions, *, base_url, api_key, model="", **kw):
        calls.append((base_url, model))
        return {"link0": True}, {"ms": 12, "input_tokens": 1, "output_tokens": 1, "error": None}

    monkeypatch.setattr(waq.llm_infra, "systemone", fake_systemone)
    answers, meta = await waq._jev({"task": "t"}, {"link0": {"type": "boolean"}}, 1)
    assert answers == {"link0": True}
    assert meta == {"jev_ms": 12, "jev_cost_usd": None}
    assert calls == [("https://llm.example/v1", "decision-model-preview")]


def test_embed_key_falls_back_to_the_private_key_on_its_own_host(monkeypatch):
    s = _patch(monkeypatch, systemone_base_url="https://llm.example/v1", systemone_api_key="sk-1")
    monkeypatch.setattr(s, "find_embed_url", "https://llm.example/v1/embeddings", raising=False)
    assert find_index.api_key() == "sk-1"
    monkeypatch.setattr(s, "find_embed_url", "https://elsewhere.example/v1/embeddings", raising=False)
    assert find_index.api_key() == ""     # another host gets no credential
    monkeypatch.setattr(s, "find_embed_url", "https://openrouter.ai/api/v1/embeddings", raising=False)
    monkeypatch.setattr(s, "platform_key_openrouter", "sk-or", raising=False)
    assert find_index.api_key() == "sk-or"


# ---- and nothing changed when nothing is configured ---------------------------------------


async def test_judge_still_serves_typesafe_by_default(monkeypatch):
    _patch(monkeypatch)
    seen: list[httpx.Request] = []
    judge_infra.clear_cache()
    j = await judge_infra.judge(
        "another distinct query for the cache", [{"id": "ep1", "name": "n", "summary": "s",
                                                  "capability": "c", "platform": "p"}],
        api_key="typesafe-key", model="jev-latest", url="https://api.typesafe.ai/v1/systemone",
        timeout_s=2.5,
        transport=_transport({"answers": {"c0": {"noul": 0.5}}}, capture=seen))
    assert j.probs == [0.5]
    assert seen[0].headers["Authorization"] == "Bearer typesafe-key"
