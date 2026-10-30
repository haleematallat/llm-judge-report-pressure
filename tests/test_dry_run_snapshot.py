"""The dry run is deterministic: it must reproduce the committed summary numbers.

Regenerate the snapshot deliberately with:
    PILOT_A_WRITE_SNAPSHOT=1 .venv/bin/python -m pytest tests/test_dry_run_snapshot.py
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from pilot_a import attack, data, providers, run

SNAPSHOT = Path(__file__).parent / "dry_run_snapshot.json"
N_ITEMS_PER_DATASET = 2


def _run(tmp_path):
    providers.LOGS = tmp_path / "logs"
    providers.CACHE = tmp_path / "cache"
    items = data.take_per_dataset(data.load_items(), N_ITEMS_PER_DATASET)
    j_dev, held_out, attacker = run.make_callers(
        mock=True, prices={}, spend=None, concurrency=4, held_out_models=run.HELD_OUT
    )
    results = {"judge": [], "selection": []}
    for item in items:
        asyncio.run(
            run.run_item(
                item,
                j_dev=j_dev,
                held_out=held_out,
                attacker=attacker,
                k=5,
                ladder=attack.N_LADDER,
                results=results,
            )
        )
    for c in [j_dev, attacker, *held_out]:
        c.close()
    return items, results


def _summary(items, results):
    return {
        "n_items": len(items),
        "n_judge_rows": len(results["judge"]),
        "judge": sorted(
            f"{r['model']}|{r['method']}|{r['condition']}|{r['answer']}|"
            f"{r['confidence']:.2f}|{r['correct']}|{r['item_id']}"
            for r in results["judge"]
        ),
        "selection": sorted(
            f"{s['item_id']}|{s['target_wrong']}|"
            + ",".join(f"{v:.2f}" for v in s["scores"])
            + "|"
            + ",".join(f"{k}:{v}" for k, v in sorted(s["chosen"].items()))
            for s in results["selection"]
        ),
    }


def test_dry_run_is_reproducible(tmp_path):
    items, results = _run(tmp_path)
    summary = _summary(items, results)
    if os.environ.get("PILOT_A_WRITE_SNAPSHOT"):
        SNAPSHOT.write_text(json.dumps(summary, indent=1, sort_keys=True))
    saved = json.loads(SNAPSHOT.read_text())
    assert summary["n_items"] == saved["n_items"]
    assert summary["n_judge_rows"] == saved["n_judge_rows"]
    assert summary["selection"] == saved["selection"]
    assert summary["judge"] == saved["judge"]


def test_dry_run_twice_gives_the_same_numbers(tmp_path):
    a = _summary(*_run(tmp_path / "a"))
    b = _summary(*_run(tmp_path / "b"))
    assert a == b
