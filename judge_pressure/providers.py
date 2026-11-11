"""Model calls: OpenRouter (live), deterministic fake (offline).

Every call is cached by (model, prompt hash, **stage**, sample index, temperature) and
appended to logs/<phase>/<model>.jsonl. Nothing is ever printed that could contain a key.

`stage` is in the key because the selection pass and the evaluation pass send the
*same* prompt to the same judge: without it, evaluating a selected report returns the
very samples that selected it (winner's curse). The provider seed is derived from
the stage too, so a deterministic provider cannot hand back the selection draw either.

Spend guard follows the pattern in github.com/haleematallat/Collusion_Sprint (betrayal/llm.py)
(key_usage/Spend), with one change required by amendment 1: each call's maximum
possible cost is *reserved* before dispatch and the unused part released afterwards,
so concurrent in-flight requests cannot overshoot the cap together.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
OPENROUTER = "https://openrouter.ai/api/v1"
CACHE = ROOT / ".cache"
LOGS = ROOT / "logs"


class SpendCapReached(RuntimeError):
    pass


def use_openrouter_key() -> bool:
    """Map `open_router_key` onto OPENROUTER_API_KEY in-process. Never logs the value."""
    if not os.environ.get("OPENROUTER_API_KEY") and os.environ.get("open_router_key"):
        os.environ["OPENROUTER_API_KEY"] = os.environ["open_router_key"]
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def have_key() -> bool:
    return use_openrouter_key()


def key_usage() -> float:
    """Total USD already spent on the key (free endpoint)."""
    r = httpx.get(
        f"{OPENROUTER}/key",
        headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
        timeout=30,
    )
    r.raise_for_status()
    return float(r.json()["data"]["usage"])


def model_prices() -> dict:
    """{model_id: {prompt, completion}} in USD per token. No key needed."""
    r = httpx.get(f"{OPENROUTER}/models", timeout=60)
    r.raise_for_status()
    out = {}
    for m in r.json()["data"]:
        p = m.get("pricing") or {}
        try:
            out[m["id"]] = {
                "prompt": float(p.get("prompt", 0) or 0),
                "completion": float(p.get("completion", 0) or 0),
                "context_length": m.get("context_length"),
            }
        except ValueError:
            continue
    return out


class Spend:
    """Reserves each call's maximum cost before dispatch, releases the unused part after.

    `check`-then-dispatch is not enough with concurrency: N in-flight calls can each
    pass a check that none of them has yet paid for. Reserving up front means the cap
    bounds committed spend, not merely settled spend (amendment 1, fix 6).
    """

    def __init__(self, cap: float, ledger: Path, start_usage: float = 0.0):
        self.cap, self.ledger, self.start = cap, ledger, start_usage
        self.spent = 0.0
        self.committed = 0.0
        self.reservations = 0
        self.peak_committed = 0.0
        self._lock = asyncio.Lock()

    @property
    def total(self) -> float:
        """Everything the cap has to cover: already spent plus currently reserved."""
        return self.start + self.spent + self.committed

    async def reserve(self, max_cost: float, model: str) -> float:
        async with self._lock:
            if self.total + max_cost > self.cap:
                raise SpendCapReached(
                    f"OpenRouter cap ${self.cap:.2f} would be exceeded by a {model} call: "
                    f"key usage ${self.start:.4f} + settled ${self.spent:.4f} "
                    f"+ reserved ${self.committed:.4f} + this ${max_cost:.4f}"
                )
            self.committed += max_cost
            self.reservations += 1
            self.peak_committed = max(self.peak_committed, self.committed)
            return max_cost

    async def settle(self, reserved: float, actual: float, model: str, item_id: str):
        async with self._lock:
            self.committed = max(0.0, self.committed - reserved)
            self.spent += actual
            self.ledger.parent.mkdir(parents=True, exist_ok=True)
            with self.ledger.open("a") as f:
                f.write(
                    json.dumps(
                        {
                            "ts": time.time(),
                            "model": model,
                            "item_id": item_id,
                            "reserved": round(reserved, 8),
                            "cost": round(actual, 8),
                        }
                    )
                    + "\n"
                )


# Reasoning settings, decided from the dev batch (see docs/details.md, "Deviations").
# Both judges are reasoning models: left alone they spend the entire max_tokens budget
# on reasoning tokens and return an empty string, which the parser reads as a refusal.
# The measured dev batch had 69-78% refused samples and 62% retry calls. Turning
# reasoning down makes the judge answer in ~12-28 tokens and parse first time.
# `enabled: false` is rejected (HTTP 4xx) by the OpenAI family, which takes
# `effort: minimal` instead, so the setting is per model with a safe default.
DEFAULT_REASONING = {"effort": "minimal"}
REASONING = {
    "qwen/qwen3.7-flash": {"enabled": False},
    "deepseek/deepseek-v4.1-flash": {"enabled": False},
    "openai/gpt-5-nano": {"effort": "minimal"},
}


# Every distinct pass that may send the same prompt to the same model.
# "select" scores candidate reports; "eval" is the measurement that must never
# reuse a selection draw.
STAGES = ("select", "eval", "attack", "honest", "critique", "topn")


def prompt_hash(messages) -> str:
    from .data import sha256

    return sha256(json.dumps(messages, sort_keys=True))


def draw_id(stage: str, sample_index: int) -> str:
    assert stage in STAGES, f"unknown stage {stage!r}"
    return f"{stage}:{sample_index}"


def draw_seed(stage: str, sample_index: int) -> int:
    """A provider seed that differs across stages even at the same sample index."""
    from .data import sha256

    return int(sha256(draw_id(stage, sample_index))[:8], 16) % (2**31)


class Caller:
    """One model. Live when `mock` is False, deterministic simulator when True."""

    def __init__(
        self,
        model: str,
        phase: str,
        *,
        spend: Spend | None = None,
        temperature: float = 1.0,
        concurrency: int = 16,
        mock: bool = False,
        prices: dict | None = None,
        reasoning: dict | None | str = "default",
    ):
        self.model, self.phase, self.spend = model, phase, spend
        self.temperature, self.mock = temperature, mock
        # "default" = the per-model setting below; None = send no reasoning field at
        # all, i.e. the provider's own default, which is what the reasoning-on check uses.
        self.reasoning = REASONING.get(model, DEFAULT_REASONING) if reasoning == "default" else reasoning
        self.prices = (prices or {}).get(model, {"prompt": 0.0, "completion": 0.0})
        self.sem = asyncio.Semaphore(concurrency)
        safe = model.replace("/", "__")
        self.log_path = LOGS / phase / f"{safe}.jsonl"
        self.cache_path = CACHE / f"{safe}.jsonl"
        self._cache = self._load_cache()
        self._lock = asyncio.Lock()
        self._log_fh = None
        self._cache_fh = None
        self.calls = 0
        self.tokens_in = 0
        self.tokens_out = 0

    def _params_tag(self, max_tokens: int) -> str:
        from .data import sha256

        return sha256(json.dumps([self.reasoning, max_tokens], sort_keys=True))[:10]

    def _load_cache(self) -> dict:
        if not self.cache_path.exists():
            return {}
        out = {}
        with self.cache_path.open() as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    out[rec["key"]] = rec["raw"]
        return out

    async def _cache_put(self, key: str, raw: str):
        self._cache[key] = raw
        async with self._lock:
            if self._cache_fh is None:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                self._cache_fh = self.cache_path.open("a")
            self._cache_fh.write(json.dumps({"key": key, "raw": raw}) + "\n")

    async def _log(self, rec: dict):
        async with self._lock:
            if self._log_fh is None:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                self._log_fh = self.log_path.open("a")
            self._log_fh.write(json.dumps(rec) + "\n")

    def close(self):
        for fh in (self._log_fh, self._cache_fh):
            if fh is not None:
                fh.close()
        self._log_fh = self._cache_fh = None

    async def call(
        self,
        messages,
        *,
        kind: str,
        stage: str,
        meta: dict,
        item_id: str,
        condition: str,
        sample_index: int = 0,
        max_tokens: int = 400,
        n_field: int | None = None,
    ) -> str:
        ph = prompt_hash(messages)
        did = draw_id(stage, sample_index)
        # "mock" is in the key for the same reason "stage" is: a dry run and a live run
        # build byte-identical prompts, so without it a live call would be served the
        # simulator's answer out of the cache. `params` is there for the same reason
        # again: the prompt hash covers the messages only, so a change to the reasoning
        # setting or the output cap would otherwise replay the old response.
        params = self._params_tag(max_tokens)
        key = f"{'mock' if self.mock else 'live'}|{self.model}|{ph}|{did}|{self.temperature}|{params}"
        seed = draw_seed(stage, sample_index)
        cached = self._cache.get(key)
        if cached is not None:
            raw, usage, cost = cached, None, 0.0
        elif self.mock:
            from .fake import fake_reply

            raw = fake_reply(self.model, kind, meta, sample_index, ph, did)
            usage, cost = None, 0.0
            await self._cache_put(key, raw)
        else:
            raw, usage = await self._live(messages, max_tokens, seed)
            cost = self._cost(usage)
            self.calls += 1
            self.tokens_in += (usage or {}).get("prompt_tokens", 0)
            self.tokens_out += (usage or {}).get("completion_tokens", 0)
            await self._cache_put(key, raw)
        await self._log(
            {
                "model": self.model,
                "phase": self.phase,
                "kind": kind,
                "item_id": item_id,
                "stage": stage,
                "cache_key": key,
                "reasoning": self.reasoning,
                "draw_seed": seed,
                "condition": condition,
                "n": n_field,
                "sample_index": sample_index,
                "prompt_hash": ph,
                "raw": raw,
                "usage": usage,
                "cost": cost,
                "mock": self.mock,
            }
        )
        return raw

    def _cost(self, usage) -> float:
        if not usage:
            return 0.0
        return usage.get("prompt_tokens", 0) * self.prices.get("prompt", 0.0) + usage.get(
            "completion_tokens", 0
        ) * self.prices.get("completion", 0.0)

    def max_cost(self, messages, max_tokens: int) -> float:
        """Upper bound on one call's cost, used for the pre-dispatch reservation."""
        chars = sum(len(m["content"]) for m in messages)
        tok_in = int(chars / 3.2) + 64  # deliberately pessimistic vs chars/4
        return tok_in * self.prices.get("prompt", 0.0) + max_tokens * self.prices.get(
            "completion", 0.0
        )

    async def _live(self, messages, max_tokens, seed):
        reserved = 0.0
        if self.spend:
            reserved = await self.spend.reserve(self.max_cost(messages, max_tokens), self.model)
        try:
            return await self._dispatch(messages, max_tokens, seed, reserved)
        except BaseException:
            if self.spend and reserved:
                await self.spend.settle(reserved, 0.0, self.model, "failed")
            raise

    async def _dispatch(self, messages, max_tokens, seed, reserved):
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "seed": seed,
        }
        if self.reasoning is not None:
            body["reasoning"] = self.reasoning
        headers = {"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"}
        last = None
        async with self.sem:
            for attempt in range(6):
                try:
                    async with httpx.AsyncClient(timeout=180) as client:
                        r = await client.post(
                            f"{OPENROUTER}/chat/completions", json=body, headers=headers
                        )
                    if r.status_code in (429, 500, 502, 503, 504):
                        raise httpx.HTTPStatusError("retry", request=r.request, response=r)
                    r.raise_for_status()
                    payload = r.json()
                    choices = payload.get("choices") or []
                    if not choices:
                        raise RuntimeError(f"no choices: {payload.get('error')}")
                    usage = payload.get("usage") or {}
                    if self.spend:
                        await self.spend.settle(
                            reserved, self._cost(usage), self.model, body["model"]
                        )
                    return choices[0]["message"]["content"] or "", usage
                except Exception as exc:  # noqa: BLE001 - retried, then re-raised
                    last = exc
                    await asyncio.sleep(min(30, 2**attempt) * (0.5 + random.random()))
        raise RuntimeError(f"{self.model}: all retries failed ({type(last).__name__})")
