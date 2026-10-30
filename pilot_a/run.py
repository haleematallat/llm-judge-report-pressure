"""Run the pipeline. Writes JSONL logs only; all tables come from pilot_a.report.

    python -m pilot_a.run --dry-run --split dev     # offline, deterministic fake
    python -m pilot_a.run --estimate --split dev    # calls/tokens/cost, spends nothing
    python -m pilot_a.run --split dev               # live dev batch (needs the key)
    python -m pilot_a.run --split test              # live main run

Scope is amendment 1: SafeAgentBench only, one target judge and one transfer judge,
conditions C0 / C_honest / N in {1, 4, 8} from 8 nested candidates, K=5 for selection
and 5 *fresh* responses for evaluation. M2-M5, the generations arm and Modal are off
in the run config; their code is still here behind --methods.
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

# Cheapest models that follow the strict-JSON contract, one per family.
# Prices in results/openrouter_prices.csv.
J_DEV = "qwen/qwen3.7-flash"  # target judge: selection runs against this one
TRANSFER = "openai/gpt-5-nano"  # transfer judge: never queried during selection
ATTACKER = "deepseek/deepseek-v4.1-flash"
HELD_OUT = [TRANSFER]

OPENROUTER_CAP = 6.00
CONDITIONS_FIXED = ("C0", "C_honest")


def conditions(ladder=attack.N_LADDER):
    return list(CONDITIONS_FIXED) + [f"N{n}" for n in ladder]


def load_run_items(split: str = "all", limit: int = 0):
    items = data.load_items()
    if split != "all":
        items = [it for it in items if it["split"] == split]
    return items[:limit] if limit else items


async def run_item(item, *, j_dev, held_out, attacker, k, ladder, results, use_methods=False):
    reports = await attack.write_reports(attacker, item, attack.N_CANDIDATES)
    honest = await attack.write_honest(attacker, item)
    scores = await attack.score_candidates(j_dev, item, reports, k=k)
    chosen = {n: attack.best_of_n(scores, n) for n in ladder}
    results["selection"].append(
        {
            "item_id": item["id"],
            "dataset": item["dataset"],
            "group": item["group"],
            "split": item["split"],
            "scores": scores,
            "chosen": {str(n): chosen[n] for n in ladder},
            "target_wrong": attack.target_wrong(item),
            "gold": item["gold"],
        }
    )

    def cond_report(cond):
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
            # stage="eval": fresh draws, never the samples that chose this report
            res = await judge_item(
                jc, item, report=text, report_id=rid, report_kind=kind,
                target_wrong=target, condition=cond, n_field=n, k=k, stage="eval",
            )
            res["method"] = "M1"
            res["gold"] = item["gold"]
            res["role"] = "target" if jc is j_dev else "transfer"
            results["judge"].append(res)
        if use_methods and len(all_judges) >= 2:
            for runner in (methods.critique_then_judge, methods.top_n_ai):
                res = await runner(
                    all_judges[1], all_judges[0], item, report=text, report_id=rid,
                    report_kind=kind, target_wrong=target, condition=cond, n_field=n, k=k,
                )
                res["gold"] = item["gold"]
                res["role"] = "method"
                results["judge"].append(res)


def make_callers(*, mock, prices, spend, concurrency, held_out_models):
    def mk(model, phase):
        return Caller(
            model, phase, spend=spend, mock=mock, prices=prices, concurrency=concurrency
        )

    return mk(J_DEV, "judge"), [mk(m, "judge") for m in held_out_models], mk(ATTACKER, "attack")


async def main_async(args):
    items = load_run_items(args.split, args.limit)
    held_out_models = HELD_OUT[: args.held_out]
    prices = {} if args.dry_run else model_prices()
    spend = None
    if not args.dry_run:
        start = key_usage()
        spend = Spend(OPENROUTER_CAP, ROOT / "logs" / "spend_ledger.jsonl", start_usage=start)
        print(f"OpenRouter key usage before this run: ${start:.4f} (pilot cap ${OPENROUTER_CAP:.2f})")
        est = estimate(args, quiet=True)
        print(f"Estimated cost of this run: ${est:.4f}")
        if start + est > OPENROUTER_CAP:
            raise SystemExit(
                f"refusing to start: ${start:.4f} already used + ${est:.4f} estimated "
                f"> cap ${OPENROUTER_CAP:.2f}"
            )
    j_dev, held_out, attacker = make_callers(
        mock=args.dry_run, prices=prices, spend=spend,
        concurrency=args.concurrency, held_out_models=held_out_models,
    )
    results = {"judge": [], "selection": []}
    sem = asyncio.Semaphore(args.item_concurrency)

    async def one(item):
        async with sem:
            await run_item(
                item, j_dev=j_dev, held_out=held_out, attacker=attacker, k=args.k,
                ladder=attack.N_LADDER, results=results, use_methods=args.methods,
            )

    t0 = time.time()
    await asyncio.gather(*(one(it) for it in items))
    for c in [j_dev, attacker, *held_out]:
        c.close()
    RESULTS.mkdir(exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    meta = {
        "mock": args.dry_run,
        "split": args.split,
        "k": args.k,
        "n_items": len(items),
        "n_groups": len({it["group"] for it in items}),
        "j_dev": J_DEV,
        "transfer": held_out_models[0] if held_out_models else None,
        "held_out": held_out_models,
        "attacker": ATTACKER,
        "ladder": list(attack.N_LADDER),
        "n_candidates": attack.N_CANDIDATES,
        "methods_enabled": bool(args.methods),
        "seconds": round(time.time() - t0, 1),
        "openrouter_spend": round(spend.spent, 6) if spend else 0.0,
        "spend_reservations": spend.reservations if spend else 0,
        "peak_reserved": round(spend.peak_committed, 6) if spend else 0.0,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    suffix = "" if args.split == "all" else f".{args.split}"
    (LOGS / f"run_meta{suffix}.json").write_text(json.dumps(meta, indent=2))
    (LOGS / "run_meta.json").write_text(json.dumps(meta, indent=2))
    for name in ("judge", "selection"):
        with (LOGS / f"{name}_results{suffix}.jsonl").open("w") as f:
            for r in results[name]:
                f.write(json.dumps(r) + "\n")
        with (LOGS / f"{name}_results.jsonl").open("a" if args.split == "test" else "w") as f:
            for r in results[name]:
                f.write(json.dumps(r) + "\n")
    print(
        f"{'DRY RUN (synthetic)' if args.dry_run else 'LIVE'} [{args.split}]: {len(items)} items, "
        f"{len(results['judge'])} judge rows in {time.time() - t0:.1f}s"
    )
    if spend:
        print(f"OpenRouter spend this run: ${spend.spent:.4f}; peak reserved ${spend.peak_committed:.4f}")


def estimate(args, quiet=False):
    """Upper-bound calls/tokens/cost. Spends nothing."""
    items = load_run_items(args.split, args.limit)
    held_out_models = HELD_OUT[: args.held_out]
    prices = model_prices()
    k, ladder = args.k, attack.N_LADDER
    n_cond = len(conditions(ladder))

    def tok(s):
        return len(s) // 4 + 1

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
        add(J_DEV, attack.N_CANDIDATES * k, with_rep, 40)  # selection
        add(J_DEV, n_cond * k, with_rep, 40)  # evaluation, fresh draws
        for m in held_out_models:
            add(m, n_cond * k, with_rep, 40)
        if args.methods and held_out_models:
            add(held_out_models[0], n_cond, with_rep, 150)
            add(J_DEV, n_cond * k, with_rep + 150, 40)
            add(J_DEV, n_cond, with_rep + tok("\n".join(it["options"])), 300)
            add(held_out_models[0], n_cond * k, with_rep + 200, 40)
    total = 0.0
    rows = []
    for m, d in per_model.items():
        p = prices.get(m, {"prompt": 0.0, "completion": 0.0})
        usd = d["in"] * p["prompt"] + d["out"] * p["completion"]
        total += usd
        rows.append((m, d, usd))
    headroom = total * (1 + args.headroom)
    if not quiet:
        print(
            f"\nCost estimate (upper bound, split={args.split}, {len(items)} items, K={k}, "
            f"{len(held_out_models)} transfer judge(s), N ladder {list(ladder)}, "
            f"{attack.N_CANDIDATES} candidates)\n"
        )
        print(f"{'model':40s} {'calls':>8s} {'tok_in':>11s} {'tok_out':>10s} {'usd':>8s}")
        for m, d, usd in rows:
            print(f"{m:40s} {d['calls']:8d} {d['in']:11d} {d['out']:10d} {usd:8.4f}")
        print(f"{'TOTAL':40s} {sum(d['calls'] for _, d, _ in rows):8d} {'':11s} {'':10s} {total:8.4f}")
        print(f"{'with ' + str(int(args.headroom * 100)) + '% retry/concurrency headroom':40s} "
              f"{'':8s} {'':11s} {'':10s} {headroom:8.4f}")
        print(f"\nOpenRouter pilot cap ${OPENROUTER_CAP:.2f} -> "
              f"{'WITHIN CAP' if headroom <= OPENROUTER_CAP else 'EXCEEDS CAP'}\n")
    return headroom


def cli(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="offline deterministic fake")
    ap.add_argument("--estimate", action="store_true", help="print cost estimate and exit")
    ap.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--held-out", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--methods", action="store_true", help="also run M4/M5 (off in the run config)")
    ap.add_argument("--headroom", type=float, default=0.30)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--item-concurrency", type=int, default=4)
    args = ap.parse_args(argv)
    if args.estimate:
        estimate(args)
        return
    if not args.dry_run and not have_key():
        raise SystemExit(
            "blocked on key: neither OPENROUTER_API_KEY nor open_router_key is set. Use --dry-run."
        )
    asyncio.run(main_async(args))


if __name__ == "__main__":
    cli()
