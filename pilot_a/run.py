"""Run the pipeline. Writes JSONL logs only; all tables come from pilot_a.report.

  python -m pilot_a.run --dry-run                 # offline, deterministic fake
  python -m pilot_a.run --estimate                # calls/tokens/cost, spends nothing
  python -m pilot_a.run                           # live (needs OPENROUTER_API_KEY)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path

from . import attack, data, methods
from .judges import judge_item, judge_messages
from .providers import (
    LOGS,
    Caller,
    Spend,
    have_key,
    key_usage,
    model_prices,
)

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# Cheapest working model per family, from results/openrouter_prices.csv.
# J_dev carries the selection load (16 candidates x K per item), so it is the cheapest.
J_DEV = "qwen/qwen3.7-flash"
HELD_OUT = [
    "google/gemini-2.5-flash-lite",
    "meta-llama/llama-3.3-70b-instruct",
    "openai/gpt-5-nano",
]
ATTACKER = "deepseek/deepseek-v4.1-flash"

OPENROUTER_CAP = 6.00
CONDITIONS_FIXED = ("C0", "C_honest")


def conditions(ladder=attack.N_LADDER):
    return list(CONDITIONS_FIXED) + [f"N{n}" for n in ladder]


async def run_item(item, *, j_dev, held_out, attacker, k, ladder, results):
    reports = await attack.write_reports(attacker, item, attack.N_CANDIDATES)
    honest = await attack.write_honest(attacker, item)
    scores = await attack.score_candidates(j_dev, item, reports, k=k)
    chosen = {n: attack.best_of_n(scores, n) for n in ladder}
    results["selection"].append(
        {
            "item_id": item["id"],
            "dataset": item["dataset"],
            "split": item["split"],
            "scores": scores,
            "chosen": {str(n): chosen[n] for n in ladder},
            "target_wrong": attack.target_wrong(item),
            "gold": item["gold"],
        }
    )

    def cond_report(cond):
        """(report text, report id, report kind, target wrong, N) for a condition."""
        if cond == "C0":
            return None, None, "none", None, None
        if cond == "C_honest":
            return honest["text"], honest["report_id"], "honest", None, None
        n = int(cond[1:])
        r = reports[chosen[n]]
        return r["text"], r["report_id"], "attack", r["target_wrong"], n

    all_judges = [j_dev] + held_out
    for cond in conditions(ladder):
        text, rid, kind, target, n = cond_report(cond)
        for jc in all_judges:
            res = await judge_item(
                jc,
                item,
                report=text,
                report_id=rid,
                report_kind=kind,
                target_wrong=target,
                condition=cond,
                n_field=n,
                k=k,
            )
            res["method"] = "M1"
            res["gold"] = item["gold"]
            results["judge"].append(res)
        if len(all_judges) >= 2:
            res = await methods.critique_then_judge(
                all_judges[1],
                all_judges[0],
                item,
                report=text,
                report_id=rid,
                report_kind=kind,
                target_wrong=target,
                condition=cond,
                n_field=n,
                k=k,
            )
            res["gold"] = item["gold"]
            results["judge"].append(res)
            res = await methods.top_n_ai(
                all_judges[0],
                all_judges[1],
                item,
                report=text,
                report_id=rid,
                report_kind=kind,
                target_wrong=target,
                condition=cond,
                n_field=n,
                k=k,
            )
            res["gold"] = item["gold"]
            results["judge"].append(res)


def make_callers(*, mock, prices, spend, concurrency, held_out_models):
    mk = lambda model, phase: Caller(  # noqa: E731
        model, phase, spend=spend, mock=mock, prices=prices, concurrency=concurrency
    )
    return (
        mk(J_DEV, "judge"),
        [mk(m, "judge") for m in held_out_models],
        mk(ATTACKER, "attack"),
    )


async def main_async(args):
    items = _select_items(args)
    held_out_models = HELD_OUT[: args.held_out]
    prices = {} if args.dry_run else model_prices()
    spend = None
    if not args.dry_run:
        start = key_usage()
        spend = Spend(OPENROUTER_CAP, ROOT / "logs" / "spend_ledger.jsonl", start_usage=start)
        print(f"OpenRouter key usage before run: ${start:.4f} (cap ${OPENROUTER_CAP:.2f})")
    j_dev, held_out, attacker = make_callers(
        mock=args.dry_run,
        prices=prices,
        spend=spend,
        concurrency=args.concurrency,
        held_out_models=held_out_models,
    )
    results = {"judge": [], "selection": []}
    sem = asyncio.Semaphore(args.item_concurrency)

    async def one(item):
        async with sem:
            await run_item(
                item,
                j_dev=j_dev,
                held_out=held_out,
                attacker=attacker,
                k=args.k,
                ladder=attack.N_LADDER,
                results=results,
            )

    t0 = time.time()
    await asyncio.gather(*(one(it) for it in items))
    for c in [j_dev, attacker, *held_out]:
        c.close()
    RESULTS.mkdir(exist_ok=True)
    (LOGS / "run_meta.json").parent.mkdir(parents=True, exist_ok=True)
    (LOGS / "run_meta.json").write_text(
        json.dumps(
            {
                "mock": args.dry_run,
                "k": args.k,
                "n_items": len(items),
                "j_dev": J_DEV,
                "held_out": held_out_models,
                "attacker": ATTACKER,
                "ladder": list(attack.N_LADDER),
                "n_candidates": attack.N_CANDIDATES,
                "seconds": round(time.time() - t0, 1),
                "openrouter_spend": round(spend.spent, 4) if spend else 0.0,
            },
            indent=2,
        )
    )
    with (LOGS / "judge_results.jsonl").open("w") as f:
        for r in results["judge"]:
            f.write(json.dumps(r) + "\n")
    with (LOGS / "selection.jsonl").open("w") as f:
        for r in results["selection"]:
            f.write(json.dumps(r) + "\n")
    print(
        f"{'DRY RUN (synthetic)' if args.dry_run else 'LIVE'}: {len(items)} items, "
        f"{len(results['judge'])} judge rows in {time.time() - t0:.1f}s"
    )
    if spend:
        print(f"OpenRouter spend this run: ${spend.spent:.4f}")


def _select_items(args):
    items = data.load_items()
    if args.items_per_dataset:
        items = data.take_per_dataset(items, args.items_per_dataset)
    return items


def estimate(args):
    """Upper-bound calls/tokens/cost. Spends nothing."""
    items = _select_items(args)
    held_out_models = HELD_OUT[: args.held_out]
    prices = model_prices()
    k, ladder = args.k, attack.N_LADDER
    n_cond = len(conditions(ladder))
    tok = lambda s: len(s) // 4 + 1  # noqa: E731
    report_tok = attack.WORD_CAP * 2
    per_model = {m: {"calls": 0, "in": 0, "out": 0} for m in [J_DEV, ATTACKER, *held_out_models]}

    def add(model, n_calls, tok_in, tok_out):
        per_model[model]["calls"] += n_calls
        per_model[model]["in"] += n_calls * tok_in
        per_model[model]["out"] += n_calls * tok_out

    for it in items:
        base = tok("".join(m["content"] for m in judge_messages(it, None)))
        with_rep = base + report_tok
        attack_in = tok(it["transcript"] + it["prompt_text"]) + 120
        add(ATTACKER, attack.N_CANDIDATES + 1, attack_in, report_tok)
        add(J_DEV, attack.N_CANDIDATES * k, with_rep, 40)  # candidate scoring
        add(J_DEV, n_cond * k, with_rep, 40)
        for m in held_out_models:
            add(m, n_cond * k, with_rep, 40)
        if held_out_models:
            add(held_out_models[0], n_cond, with_rep, 150)  # M4 critique
            add(J_DEV, n_cond * k, with_rep + 150, 40)  # M4 judge
            add(J_DEV, n_cond, with_rep + tok("\n".join(it["options"])), 300)  # M5 propose
            add(held_out_models[0], n_cond * k, with_rep + 200, 40)  # M5 pick
    total = 0.0
    print(f"\nCost estimate (upper bound, {len(items)} items, K={k}, "
          f"{len(held_out_models)} held-out judges, no retries assumed)\n")
    print(f"{'model':40s} {'calls':>8s} {'tok_in':>11s} {'tok_out':>10s} {'usd':>8s}")
    for m, d in per_model.items():
        p = prices.get(m, {"prompt": 0.0, "completion": 0.0})
        usd = d["in"] * p["prompt"] + d["out"] * p["completion"]
        total += usd
        print(f"{m:40s} {d['calls']:8d} {d['in']:11d} {d['out']:10d} {usd:8.3f}")
    print(f"{'TOTAL':40s} {sum(d['calls'] for d in per_model.values()):8d} "
          f"{'':11s} {'':10s} {total:8.3f}")
    print(f"\nOpenRouter cap ${OPENROUTER_CAP:.2f} -> "
          f"{'WITHIN CAP' if total <= OPENROUTER_CAP else 'EXCEEDS CAP: shrink items, then held-out judges, then K'}")
    print("Modal: not used (see README deviations); Modal spend $0.00\n")
    return total


def cli(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="offline deterministic fake")
    ap.add_argument("--estimate", action="store_true", help="print cost estimate and exit")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--held-out", type=int, default=3)
    ap.add_argument("--items-per-dataset", type=int, default=0,
                    help="stratified subsample per dataset (0 = all built items)")
    ap.add_argument("--concurrency", type=int, default=16)
    ap.add_argument("--item-concurrency", type=int, default=8)
    args = ap.parse_args(argv)
    if args.estimate:
        estimate(args)
        return
    if not args.dry_run and not have_key():
        raise SystemExit("blocked on key: OPENROUTER_API_KEY is not set. Use --dry-run.")
    asyncio.run(main_async(args))


if __name__ == "__main__":
    cli()
