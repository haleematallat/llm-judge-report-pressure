"""Model calls: OpenRouter (live), Modal vLLM (live), deterministic fake (offline).

Every call is cached by (model, prompt hash, sample index, temperature) and appended
to logs/<phase>/<model>.jsonl. Nothing is ever printed that could contain a key.

Spend guard follows the pattern in ~/pivotal-pilots/Collusion_Sprint/betrayal/llm.py
(key_usage/Spend): total key usage is read from OpenRouter before the run and the
running total is checked before every paid call.
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


def have_key() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))


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
    """Aborts before a call would push total key usage past the cap."""

    def __init__(self, cap: float, ledger: Path, start_usage: float = 0.0):
        self.cap, self.ledger, self.start = cap, ledger, start_usage
        self.spent = 0.0
        self.est = 0.0

    @property
    def total(self) -> float:
        return self.start + self.spent

    def check(self):
        if self.total + self.est > self.cap:
            raise SpendCapReached(
                f"OpenRouter cap ${self.cap:.2f}: key usage ${self.start:.4f} "
                f"+ this run ${self.spent:.4f} + next ${self.est:.4f}"
            )

    def add(self, cost: float, model: str, item_id: str):
        self.spent += cost
        self.est = max(self.est, cost)
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a") as f:
            f.write(
                json.dumps({"ts": time.time(), "model": model, "item_id": item_id, "cost": cost})
                + "\n"
            )


def prompt_hash(messages) -> str:
    from .data import sha256

    return sha256(json.dumps(messages, sort_keys=True))


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
    ):
        self.model, self.phase, self.spend = model, phase, spend
        self.temperature, self.mock = temperature, mock
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
        meta: dict,
        item_id: str,
        condition: str,
        sample_index: int = 0,
        max_tokens: int = 400,
        n_field: int | None = None,
    ) -> str:
        ph = prompt_hash(messages)
        key = f"{self.model}|{ph}|{sample_index}|{self.temperature}"
        cached = self._cache.get(key)
        if cached is not None:
            raw, usage, cost = cached, None, 0.0
        elif self.mock:
            from .fake import fake_reply

            raw = fake_reply(self.model, kind, meta, sample_index, ph)
            usage, cost = None, 0.0
            await self._cache_put(key, raw)
        else:
            raw, usage = await self._live(messages, max_tokens, sample_index)
            cost = self._cost(usage)
            if self.spend:
                self.spend.add(cost, self.model, item_id)
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

    async def _live(self, messages, max_tokens, sample_index):
        if self.spend:
            self.spend.check()
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": max_tokens,
            "seed": sample_index,
        }
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
                    return choices[0]["message"]["content"] or "", payload.get("usage") or {}
                except Exception as exc:  # noqa: BLE001 - retried, then re-raised
                    last = exc
                    await asyncio.sleep(min(30, 2**attempt) * (0.5 + random.random()))
        raise RuntimeError(f"{self.model}: all retries failed ({type(last).__name__})")
