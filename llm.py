"""Cohere wrapper: disk cache, spend tracking, hard budget stop, mock mode.

MOCK=1 runs everything offline (no key, no spend) for smoke tests.
"""
import hashlib
import json
import os
import random
import re
import threading
import time
from pathlib import Path

import config as C

MOCK = os.environ.get("MOCK") == "1"
CACHE = Path("cache_mock" if MOCK else "cache")
CACHE.mkdir(exist_ok=True)
SPEND_FILE = Path("spend_mock.json" if MOCK else "spend.json")

_lock = threading.Lock()
_client = None
_pause_until = 0.0  # when any thread hits a rate limit, ALL threads wait until this time


class BudgetExceeded(Exception):
    pass


def _read_spend():
    try:
        return json.loads(SPEND_FILE.read_text())["usd"]
    except (FileNotFoundError, ValueError, KeyError):
        return 0.0


def spent():
    with _lock:
        return _read_spend()


def _add_spend(usd):
    with _lock:
        s = _read_spend() + usd
        tmp = SPEND_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps({"usd": s}))
        os.replace(tmp, SPEND_FILE)
        return s


def _cost(u):
    fresh = u["in"] - u["cached"]
    return fresh * C.PRICE_IN + u["cached"] * C.PRICE_CACHED + u["out"] * C.PRICE_OUT


def chat(messages, tools=None, tag="", meta=None, tool_choice="auto", json_mode=False):
    key = hashlib.sha256(
        json.dumps([C.MODEL, messages, tools, tool_choice, tag, json_mode], sort_keys=True).encode()
    ).hexdigest()
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text())
    if spent() >= C.BUDGET_USD:
        raise BudgetExceeded(f"spent ${spent():.2f} >= ${C.BUDGET_USD}")
    out = _mock(messages, tools, meta, json_mode) if MOCK else _call(messages, tools, tool_choice, json_mode)
    _add_spend(out["cost"])
    path.write_text(json.dumps(out))
    return out


def _call(messages, tools, tool_choice, json_mode):
    global _client, _pause_until
    if _client is None:
        import cohere

        _client = cohere.ClientV2(api_key=os.environ["COHERE_API_KEY"], timeout=120)
    kw = dict(model=C.MODEL, messages=_conv(messages), max_tokens=C.MAX_COMPLETION, temperature=C.TEMPERATURE)
    if C.THINK_BUDGET:
        kw["thinking"] = {"type": "enabled", "token_budget": C.THINK_BUDGET}
    if tools:
        kw["tools"] = tools
    if json_mode:
        kw["response_format"] = {"type": "json_object"}
        kw["max_tokens"] = 5000
        if C.THINK_BUDGET:
            kw["thinking"] = {"type": "enabled", "token_budget": 2000}
    kw = {k: v for k, v in kw.items() if v is not None}
    r = None
    last = None
    for attempt in range(12):
        wait = _pause_until - time.time()
        if wait > 0:
            time.sleep(wait)
        try:
            r = _client.chat(**kw)
            break
        except Exception as e:  # noqa: BLE001
            last = e
            msg = str(e).lower()
            if "thinking" in msg and "thinking" in kw and ("not support" in msg or "invalid" in msg or "unknown" in msg):
                kw.pop("thinking")
                continue
            code = getattr(e, "status_code", None)
            if code in (400, 401, 403, 404, 422):
                raise RuntimeError(f"Cohere rejected the request (HTTP {code}): {getattr(e, 'body', e)}") from e
            if code == 429 or "toomanyrequests" in type(e).__name__.lower():
                _pause_until = max(_pause_until, time.time() + min(90, 15 * (attempt + 1)))  # rate limit: everyone waits
                print(f"[rate limit hit; pausing all calls ~{min(90, 15 * (attempt + 1))}s]", flush=True)
            else:
                time.sleep(min(60, 2 ** attempt * 2))  # network drop / 5xx
            continue
    if r is None:
        raise RuntimeError(f"API failed after retries. Last error: {last!r}")
    m = r.message
    text = "".join(getattr(c, "text", "") or "" for c in (m.content or []) if getattr(c, "type", "") == "text")
    us = r.usage
    tok = getattr(us, "tokens", None)
    cached = getattr(us, "cached_tokens", 0) or 0
    u = {"in": (getattr(tok, "input_tokens", 0) or 0), "out": (getattr(tok, "output_tokens", 0) or 0), "cached": cached}
    calls = []
    for tc in (m.tool_calls or []):
        try:
            args = json.loads(tc.function.arguments or "{}")
        except ValueError:
            args = {}
        calls.append({"id": tc.id, "name": tc.function.name, "args": args})
    return {"content": text or None, "tool_calls": calls, "usage": u, "cost": _cost(u), "finish": str(r.finish_reason)}


def _conv(messages):
    """OpenAI-style messages -> Cohere V2 messages (assistant tool-call turns need a tool_plan or content)."""
    out = []
    for m in messages:
        m = dict(m)
        if m["role"] == "assistant" and m.get("tool_calls"):
            if not m.get("content"):  # this model rejects tool_plan; send the tool calls alone
                m.pop("content", None)
        out.append(m)
    return out


# ---------------- mock (offline smoke test only) ----------------
def _mock(messages, tools, meta, json_mode):
    seed = hashlib.md5(json.dumps(messages, sort_keys=True).encode()).hexdigest()
    rng = random.Random(seed)
    u = {"in": 1500, "out": 120, "cached": 0}
    if json_mode:
        n = rng.randint(1000, 9999)
        t, f = str(n), str(n + rng.randint(3, 40))
        o3, o4 = str(n - 7), str(n + 91)
        pad = " ".join(["context"] * 45)
        docs = (
            [{"role": "true", "title": f"True report {i}", "body": f"The record states {t}. {pad}"} for i in range(2)]
            + [{"role": "false", "title": f"False claim {i}", "body": f"It was actually {f}. {pad}"} for i in range(2)]
            + [{"role": "neutral", "title": f"Background {i}", "body": f"General background only. {pad}"} for i in range(2)]
        )
        obj = {"entity": f"Entity{n}", "question": f"In what year did Entity{n} open its main hall?",
               "options": [t, f, o3, o4], "true_index": 0, "false_index": 1, "docs": docs}
        return {"content": json.dumps(obj), "tool_calls": [], "usage": u, "cost": 0.0, "finish": "stop"}
    n_tool = sum(m["role"] == "tool" for m in messages)
    if tools and n_tool == 0:
        tc = [{"id": "c1", "name": "search", "args": {"query": "question"}}]
        return {"content": None, "tool_calls": tc, "usage": u, "cost": 0.0, "finish": "tool_calls"}
    if tools and n_tool == 1:
        last = [m for m in messages if m["role"] == "tool"][-1]["content"]
        ids = re.findall(r"\[(d\d)\]", last)[:2]
        tc = [{"id": f"c{i + 2}", "name": "read", "args": {"doc_id": d}} for i, d in enumerate(ids)]
        return {"content": None, "tool_calls": tc, "usage": u, "cost": 0.0, "finish": "tool_calls"}
    arm = (meta or {}).get("arm", "A0")
    p_false = {"A0": .5, "A1": .2, "A2": .25, "A3": .2, "A4": .45, "A5": .45, "A6": .25, "A7": .7}.get(arm, .5)
    letter = meta["false_letter"] if rng.random() < p_false else meta["true_letter"]
    return {"content": f"ANSWER: {letter}", "tool_calls": [], "usage": u, "cost": 0.0, "finish": "stop"}