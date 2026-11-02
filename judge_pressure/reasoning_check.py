"""Pre-registered secondary check (preregistration §7), reported separately.

The main study runs both judges with reasoning disabled or minimal, because left alone
they spend the whole output budget on reasoning tokens and return nothing parseable.
Sampura's judges reason freely, so attack success here may be higher than it would be
against a reasoning judge. This re-judges a subset of the held-out items with the
target judge's own default reasoning, on C0 and N=8 only, reusing the reports the main
run already selected. It is not part of the primary comparison.

    python -m judge_pressure.reasoning_check --n 60
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import defaultdict

from . import data, metrics
from .judges import judge_item
from .providers import LOGS, Caller, Spend, have_key, key_usage, model_prices
from .run import COMBINED_CAP, J_DEV, OPENROUTER_CAP, ROOT, pilot_baseline

RESULTS = ROOT / "results"
CONDS = ("C0", "N8")


def selected_reports():
    """item_id -> {condition: report text}, from the main run's logs."""
    sel = {}
    for line in (LOGS / "selection_results.test.jsonl").open():
        r = json.loads(line)
        sel[r["item_id"]] = r
    text = defaultdict(dict)
    for path in (LOGS / "attack").glob("*.jsonl"):
        for line in path.open():
            rec = json.loads(line)
            text[rec["item_id"]][rec["condition"]] = rec["raw"]
    out = {}
    for iid, rec in sel.items():
        chosen = int(rec["chosen"]["8"])
        out[iid] = {
            "N8": text[iid].get(f"cand{chosen}"),
            "report_id": f"{iid}#c{chosen}",
            "target_wrong": rec["target_wrong"],
        }
    return out


def pick(items, reports, n):
    """Whole groups, deterministic, until n items are reached."""
    pool = [it for it in items if it["split"] == "test" and reports.get(it["id"], {}).get("N8")]
    groups = defaultdict(list)
    for it in pool:
        groups[it["group"]].append(it)
    out = []
    for g in sorted(groups, key=lambda g: data.sha256("rcheck:" + g)):
        if len(out) >= n:
            break
        out.extend(sorted(groups[g], key=lambda it: it["id"]))
    return out


async def run(n, k, concurrency):
    items = data.load_items()
    reports = selected_reports()
    chosen = pick(items, reports, n)
    prices = model_prices()
    start = key_usage()
    baseline = pilot_baseline(start)
    spent, combined = max(0.0, start - baseline), start - baseline
    print(
        f"Pilot spend before this check ${spent:.4f} of ${OPENROUTER_CAP:.2f}; "
        f"combined ${combined:.4f} of ${COMBINED_CAP:.2f}"
    )
    # ~2 conditions x K calls per item on one judge; a generous ceiling
    est = len(chosen) * len(CONDS) * k * 0.0002
    print(f"Reasoning-on check: {len(chosen)} items, estimated <= ${est:.4f}")
    if spent + est > OPENROUTER_CAP or combined + est > COMBINED_CAP:
        raise SystemExit("refusing to start: would exceed a cap")
    spend = Spend(baseline + OPENROUTER_CAP, LOGS / "spend_ledger.jsonl", start_usage=start)
    caller = Caller(
        J_DEV, "reasoning_check", spend=spend, prices=prices,
        concurrency=concurrency, reasoning=None,  # provider default: reasoning ON
    )
    sem = asyncio.Semaphore(concurrency // 4 or 1)

    async def one(it, cond):
        async with sem:
            rep = reports[it["id"]]
            return await judge_item(
                caller, it,
                report=None if cond == "C0" else rep["N8"],
                report_id=None if cond == "C0" else rep["report_id"],
                report_kind="none" if cond == "C0" else "attack",
                target_wrong=None if cond == "C0" else rep["target_wrong"],
                condition=cond, n_field=None if cond == "C0" else 8, k=k, stage="eval",
            )

    rows = await asyncio.gather(*(one(it, c) for it in chosen for c in CONDS))
    caller.close()
    for r, it in zip(rows, [it for it in chosen for _ in CONDS]):
        r["gold"] = it["gold"]
        r["method"] = "M1-reasoning-on"
    with (LOGS / "reasoning_check.jsonl").open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"spend this check ${spend.spent:.4f}")
    return rows, chosen


def report(rows, chosen):
    main = {}
    for line in (LOGS / "judge_results.test.jsonl").open():
        r = json.loads(line)
        if r["model"] == J_DEV and r["method"] == "M1":
            main[(r["item_id"], r["condition"])] = r
    ids = sorted({r["item_id"] for r in rows})
    out = []
    for label, get in (("reasoning ON (this check)", {(r["item_id"], r["condition"]): r for r in rows}),
                       ("reasoning OFF (main run)", main)):
        for cond in CONDS:
            rs = [get[(i, cond)] for i in ids if (i, cond) in get]
            if not rs:
                continue
            err = [1 - r["correct"] for r in rs]
            _, lo, hi = metrics.wilson(sum(err), len(err))
            answered = [r for r in rs if r["answer"] != "__REFUSAL__"]
            err_ans = [1 - r["correct"] for r in answered]
            out.append({
                "judge_config": label, "condition": cond, "n_items": len(rs),
                "n_groups": len({r["group"] for r in rs}),
                "error_rate_all_items": round(100 * sum(err) / len(err), 1),
                "ci_lo": round(100 * lo, 1), "ci_hi": round(100 * hi, 1),
                "items_with_no_usable_answer": len(rs) - len(answered),
                "error_rate_answered_only": round(100 * sum(err_ans) / len(err_ans), 1)
                if err_ans else None,
                "mean_self_consistency": round(sum(r["confidence"] for r in rs) / len(rs), 3),
                "unparseable_sample_rate": round(
                    sum(r["refusals"] for r in rs) / (len(rs) * len(rs[0]["samples"])), 3),
            })
    contrasts = []
    for label, get in (("reasoning ON (this check)", {(r["item_id"], r["condition"]): r for r in rows}),
                       ("reasoning OFF (main run)", main)):
        pair = [i for i in ids if (i, "C0") in get and (i, "N8") in get]
        if not pair:
            continue
        a = [1 - get[(i, "N8")]["correct"] for i in pair]
        b = [1 - get[(i, "C0")]["correct"] for i in pair]
        gb = metrics.paired_group_bootstrap(a, b, [get[(i, "C0")]["group"] for i in pair])
        contrasts.append({
            "judge_config": label, "contrast": "N8 - C0", "n_items": gb["n_items"],
            "n_groups": gb["n_groups"],
            "error_rate_N8": round(100 * sum(a) / len(a), 1),
            "error_rate_C0": round(100 * sum(b) / len(b), 1),
            "delta_pp": round(100 * gb["diff"], 1),
            "ci_lo": round(100 * gb["lo"], 1), "ci_hi": round(100 * gb["hi"], 1),
            "p_group_boot": round(gb["p"], 4),
        })
    from .report import md_table, write_csv

    write_csv("reasoning_check", out + contrasts)
    (RESULTS / "reasoning_check.md").write_text(
        "# Reasoning-on check (secondary, preregistration §7)\n\n"
        f"Target judge `{J_DEV}` on {len(ids)} held-out items, C0 and N=8 only, reusing the "
        "reports the main run selected. The main run's judges run with reasoning disabled "
        "or minimal; this one uses the provider's default, so reasoning is on. Same items, "
        "same reports, same K.\n\n"
        "**Read this table with the refusal column.** With reasoning on, the judge spends "
        "its output budget on reasoning tokens and often returns nothing parseable, even "
        "at a 300-token cap. Roughly 55% of individual samples and a double-digit number "
        "of whole items come back with no usable answer, and an item with no usable answer "
        "is scored as an error. `error_rate_all_items` therefore mixes attack success with "
        "parse failure. `error_rate_answered_only` removes the unanswered items, but it "
        "conditions on an outcome produced after the treatment, so the two conditions no "
        "longer rest on the same set of items. Neither column is a clean estimate; both "
        "are given so the gap between them is visible.\n\n## Error rate\n\n" + md_table(out)
        + "\n## N=8 vs C0 under each configuration (all items, refusals scored as errors)\n\n"
        + md_table(contrasts)
        + "\nThis is a secondary check on how much of the measured attack success depends "
        "on the judges running without reasoning. It is not the primary comparison, and "
        "its refusal rate means it cannot settle the question on its own.\n"
    )
    print(md_table(out))
    print(md_table(contrasts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--concurrency", type=int, default=24)
    a = ap.parse_args()
    if not have_key():
        raise SystemExit("blocked on key")
    rows, chosen = asyncio.run(run(a.n, a.k, a.concurrency))
    report(rows, chosen)


if __name__ == "__main__":
    main()
