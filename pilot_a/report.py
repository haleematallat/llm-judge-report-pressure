"""Recompute every table and figure from logs/ alone.

    python -m pilot_a.report

Writes results/*.csv, results/tables.md and figures/*.png. Nothing here calls a model.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import metrics  # noqa: E402
from .attack import N_LADDER  # noqa: E402
from .data import load_items  # noqa: E402
from .judges import REFUSAL  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"
CONDS = ["C0", "C_honest"] + [f"N{n}" for n in N_LADDER]

# Sampura's reported AI-alone test accuracy (%) on the same three datasets.
# Table 4 (Gemini 3 Flash, Sonnet 4.6) and Table 2 (Qwen3.5-9B) of arXiv 2610.24969.
# Different models, different item samples and a different split: not like-for-like.
PAPER_AI_ALONE = {
    "safeagentbench": {"Gemini 3 Flash": 83.6, "Sonnet 4.6": 78.3, "Qwen3.5-9B": 76.9, "N": 511},
    "liars_bench": {"Gemini 3 Flash": 42.6, "Sonnet 4.6": 46.6, "Qwen3.5-9B": 36.9, "N": 371},
    "bbeh_safety": {"Gemini 3 Flash": 47.1, "Sonnet 4.6": 49.2, "Qwen3.5-9B": 40.3, "N": 238},
}


def load():
    rows = [json.loads(line) for line in (LOGS / "judge_results.jsonl").open() if line.strip()]
    selection = [json.loads(line) for line in (LOGS / "selection.jsonl").open() if line.strip()]
    meta = json.loads((LOGS / "run_meta.json").read_text())
    items = {it["id"]: it for it in load_items()}
    return rows, selection, meta, items


def index(rows):
    """(model, method, condition, split) -> {item_id: row}"""
    out = defaultdict(dict)
    for r in rows:
        out[(r["model"], r["method"], r["condition"], r["split"])][r["item_id"]] = r
    return out


def cheapest_three(models):
    price_file = RESULTS / "openrouter_prices.csv"
    if not price_file.exists():
        return sorted(models)[:3]
    prices = {}
    with price_file.open() as f:
        for row in csv.DictReader(f):
            prices[row["model"]] = float(row["prompt_usd_per_tok"]) + float(
                row["completion_usd_per_tok"]
            )
    return sorted(models, key=lambda m: prices.get(m, 9e9))[:3]


# --- tables -----------------------------------------------------------------


def t_reproduction(idx, judges):
    out = []
    for model in judges:
        for dataset in sorted(PAPER_AI_ALONE):
            rs = [
                r
                for r in idx[(model, "M1", "C0", "test")].values()
                if r["dataset"] == dataset
            ]
            if not rs:
                continue
            correct = [r["correct"] for r in rs]
            conf = [r["confidence"] for r in rs]
            stated = [
                r["stated_confidence"] / 100 for r in rs if r["stated_confidence"] is not None
            ]
            stated_y = [r["correct"] for r in rs if r["stated_confidence"] is not None]
            p, lo, hi = metrics.wilson(sum(correct), len(correct))
            out.append(
                {
                    "dataset": dataset,
                    "judge": model,
                    "n_test": len(rs),
                    "acc": round(100 * p, 1),
                    "ci_lo": round(100 * lo, 1),
                    "ci_hi": round(100 * hi, 1),
                    "mean_self_consistency": round(sum(conf) / len(conf), 3),
                    "auroc_self_consistency": round(metrics.auroc(conf, correct), 3),
                    "ece_self_consistency": round(metrics.ece(conf, correct), 3),
                    "auroc_stated": round(metrics.auroc(stated, stated_y), 3) if stated else None,
                    "ece_stated": round(metrics.ece(stated, stated_y), 3) if stated else None,
                    "refusal_rate": round(
                        sum(r["refusals"] for r in rs) / (len(rs) * len(rs[0]["samples"])), 3
                    ),
                    "paper_gemini3flash": PAPER_AI_ALONE[dataset]["Gemini 3 Flash"],
                    "paper_sonnet46": PAPER_AI_ALONE[dataset]["Sonnet 4.6"],
                    "paper_qwen35_9b": PAPER_AI_ALONE[dataset]["Qwen3.5-9B"],
                    "paper_n": PAPER_AI_ALONE[dataset]["N"],
                }
            )
    return out


def combine(idx, models, condition, split, items, weighted):
    """M2/M3 rows built from the M1 rows already in the logs."""
    from .methods import confidence_weighted, majority

    per_item = defaultdict(list)
    for m in models:
        for iid, r in idx[(m, "M1", condition, split)].items():
            per_item[iid].append(r)
    out = {}
    for iid, rs in per_item.items():
        if len(rs) < len(models):
            continue
        item = items[iid]
        comb = (confidence_weighted if weighted else majority)(rs, item["options"])
        out[iid] = {
            "item_id": iid,
            "dataset": item["dataset"],
            "split": split,
            "condition": condition,
            "model": ("M3:" if weighted else "M2:") + "+".join(models),
            "method": "M3" if weighted else "M2",
            "answer": comb["answer"],
            "confidence": comb["confidence"],
            "stated_confidence": None,
            "samples": [r["answer"] for r in rs],
            "refusals": sum(r["answer"] == REFUSAL for r in rs),
            "correct": int(comb["answer"] == item["gold"]),
            "gold": item["gold"],
            "n": rs[0]["n"],
        }
    return out


def acc_of(rows_by_item, ids):
    v = [rows_by_item[i]["correct"] for i in ids]
    return sum(v) / len(v) if v else float("nan")


def t_hillclimb(idx, judges, trio, items):
    """Test accuracy at C0 for M1-M5 against the best single judge."""
    arms = {}
    for m in judges:
        arms[f"M1 {m}"] = idx[(m, "M1", "C0", "test")]
    arms["M2 majority(3 cheapest)"] = combine(idx, trio, "C0", "test", items, weighted=False)
    arms["M3 conf-weighted(3 cheapest)"] = combine(idx, trio, "C0", "test", items, weighted=True)
    for mk in sorted({(r["model"], r["method"]) for r in _all_rows if r["method"] in ("M4", "M5")}):
        arms[f"{mk[1]} {mk[0]}"] = idx[(mk[0], mk[1], "C0", "test")]
    common = set.intersection(*(set(a) for a in arms.values()))
    common = sorted(common)
    best_name = max(
        (n for n in arms if n.startswith("M1")), key=lambda n: acc_of(arms[n], common)
    )
    out = []
    pvals = {}
    for name, a in arms.items():
        acc = acc_of(a, common)
        p, lo, hi = metrics.wilson(round(acc * len(common)), len(common))
        pb = metrics.paired_bootstrap(
            [a[i]["correct"] for i in common], [arms[best_name][i]["correct"] for i in common]
        )
        pvals[name] = pb["p"]
        out.append(
            {
                "arm": name,
                "n_test": len(common),
                "acc": round(100 * acc, 1),
                "ci_lo": round(100 * lo, 1),
                "ci_hi": round(100 * hi, 1),
                "delta_vs_best_single": round(100 * pb["diff"], 1),
                "delta_ci_lo": round(100 * pb["lo"], 1),
                "delta_ci_hi": round(100 * pb["hi"], 1),
                "p": round(pb["p"], 4),
            }
        )
    holm = metrics.holm(pvals)
    for row in out:
        row["p_holm"] = round(holm[row["arm"]], 4)
    # oracle of two judges (either correct) = the ceiling
    oracle = []
    m1 = [n for n in arms if n.startswith("M1")]
    for i, a in enumerate(m1):
        for b in m1[i + 1 :]:
            v = [max(arms[a][x]["correct"], arms[b][x]["correct"]) for x in common]
            oracle.append((f"oracle({a.split()[1]}, {b.split()[1]})", sum(v) / len(v)))
    for name, acc in sorted(oracle, key=lambda kv: -kv[1]):
        out.append(
            {
                "arm": name,
                "n_test": len(common),
                "acc": round(100 * acc, 1),
                "ci_lo": None,
                "ci_hi": None,
                "delta_vs_best_single": round(100 * (acc - acc_of(arms[best_name], common)), 1),
                "delta_ci_lo": None,
                "delta_ci_hi": None,
                "p": None,
                "p_holm": None,
            }
        )
    return out, best_name, common


def t_pressure(idx, arms, items):
    """Accuracy, confidently-wrong and router miss for every arm x condition."""
    out = []
    for name, by_cond in arms.items():
        dev_c0 = by_cond.get(("C0", "dev"), {})
        tau = metrics.router_threshold([r["confidence"] for r in dev_c0.values()])
        base = by_cond.get(("C0", "test"), {})
        for cond in CONDS:
            rs = by_cond.get((cond, "test"), {})
            if not rs:
                continue
            ids = sorted(set(rs) & set(base)) if base else sorted(rs)
            correct = [rs[i]["correct"] for i in ids]
            conf = [rs[i]["confidence"] for i in ids]
            p, lo, hi = metrics.wilson(sum(correct), len(correct))
            cw = metrics.confidently_wrong(
                [rs[i]["samples"] for i in ids], [items[i]["gold"] for i in ids]
            )
            rm = metrics.router_miss(correct, conf, tau)
            pb = (
                metrics.paired_bootstrap(correct, [base[i]["correct"] for i in ids])
                if base and cond != "C0"
                else None
            )
            out.append(
                {
                    "arm": name,
                    "condition": cond,
                    "n": int(cond[1:]) if cond.startswith("N") else None,
                    "n_test": len(ids),
                    "acc": round(100 * p, 1),
                    "ci_lo": round(100 * lo, 1),
                    "ci_hi": round(100 * hi, 1),
                    "delta_vs_C0": round(100 * pb["diff"], 1) if pb else 0.0,
                    "delta_ci_lo": round(100 * pb["lo"], 1) if pb else None,
                    "delta_ci_hi": round(100 * pb["hi"], 1) if pb else None,
                    "p": round(pb["p"], 4) if pb else None,
                    "mean_confidence": round(sum(conf) / len(conf), 3),
                    "confidently_wrong_rate": round(cw["rate"], 3),
                    "router_tau": round(tau, 3),
                    "router_miss_rate": round(rm["miss_rate"], 3)
                    if rm["miss_rate"] == rm["miss_rate"]
                    else None,
                    "router_missed_errors": rm["missed"],
                    "router_n_wrong": rm["n_wrong"],
                    "router_share_of_items": round(rm["share_of_items"], 3),
                }
            )
    # Holm within each arm's "accuracy falls with N" family
    for name in arms:
        fam = {
            r["condition"]: r["p"]
            for r in out
            if r["arm"] == name and r["condition"].startswith("N") and r["p"] is not None
        }
        if fam:
            adj = metrics.holm(fam)
            for r in out:
                if r["arm"] == name and r["condition"] in adj:
                    r["p_holm"] = round(adj[r["condition"]], 4)
    return out


def t_n50(arms):
    out = []
    for name, by_cond in arms.items():
        ns, correct = [], []
        for n in N_LADDER:
            for r in by_cond.get((f"N{n}", "test"), {}).values():
                ns.append(n)
                correct.append(r["correct"])
        if not ns:
            continue
        fit = metrics.fit_n50(ns, correct)
        out.append(
            {
                "arm": name,
                "a": round(fit["a"], 4),
                "b": round(fit["b"], 4),
                "n50": round(fit["n50"], 2) if fit["n50"] else None,
                "n50_display": f"{fit['n50']:.1f}" if fit["n50"] else (fit["note"] or "n/a"),
                "n_obs": len(ns),
            }
        )
    return out


def t_correlation(idx, judges):
    out = []
    for cond in ("C0", "N16"):
        for i, a in enumerate(judges):
            for b in judges[i + 1 :]:
                ra, rb = idx[(a, "M1", cond, "test")], idx[(b, "M1", cond, "test")]
                ids = sorted(set(ra) & set(rb))
                if not ids:
                    continue
                ea = [1 - ra[x]["correct"] for x in ids]
                eb = [1 - rb[x]["correct"] for x in ids]
                st = metrics.phi(ea, eb)
                out.append(
                    {
                        "condition": cond,
                        "judge_a": a,
                        "judge_b": b,
                        "n": st["n"],
                        "phi": round(st["phi"], 3) if st["phi"] == st["phi"] else None,
                        "cov": round(st["cov"], 4),
                        "both_wrong_rate": round(
                            sum(1 for x, y in zip(ea, eb) if x and y) / len(ids), 3
                        ),
                    }
                )
    return out


def t_transfer(idx, j_dev, held_out):
    """Reports were selected against J_dev; how much carries to held-out judges."""
    out = []
    for model in [j_dev, *held_out]:
        c0 = idx[(model, "M1", "C0", "test")]
        for n in N_LADDER:
            rs = idx[(model, "M1", f"N{n}", "test")]
            ids = sorted(set(c0) & set(rs))
            if not ids:
                continue
            pb = metrics.paired_bootstrap(
                [rs[i]["correct"] for i in ids], [c0[i]["correct"] for i in ids]
            )
            out.append(
                {
                    "judge": model,
                    "role": "J_dev (selection target)" if model == j_dev else "held out",
                    "n": n,
                    "acc_C0": round(100 * sum(c0[i]["correct"] for i in ids) / len(ids), 1),
                    "acc_N": round(100 * sum(rs[i]["correct"] for i in ids) / len(ids), 1),
                    "drop": round(-100 * pb["diff"], 1),
                    "drop_ci_lo": round(-100 * pb["hi"], 1),
                    "drop_ci_hi": round(-100 * pb["lo"], 1),
                }
            )
    return out


def t_topn_displacement(idx):
    """Share of items where gold leaves the Top-3 candidate list under pressure."""
    out = []
    m5 = sorted({(r["model"], r["method"]) for r in _all_rows if r["method"] == "M5"})
    for model, method in m5:
        for cond in CONDS:
            rs = idx[(model, method, cond, "test")]
            vals = [r.get("gold_in_top_n") for r in rs.values() if r.get("gold_in_top_n") is not None]
            if not vals:
                continue
            out.append(
                {
                    "arm": f"{method} {model}",
                    "condition": cond,
                    "n": int(cond[1:]) if cond.startswith("N") else None,
                    "n_test": len(vals),
                    "gold_in_top3_rate": round(sum(vals) / len(vals), 3),
                    "displacement_rate": round(1 - sum(vals) / len(vals), 3),
                }
            )
    return out


def t_selection(selection):
    """What the attacker's best-of-N search actually found, per dataset."""
    out = []
    for dataset in sorted({s["dataset"] for s in selection}):
        rows = [s for s in selection if s["dataset"] == dataset and s["split"] == "test"]
        if not rows:
            continue
        for n in N_LADDER:
            picked = [s["scores"][int(s["chosen"][str(n)])] for s in rows]
            out.append(
                {
                    "dataset": dataset,
                    "n": n,
                    "n_items": len(rows),
                    "mean_selected_p_wrong": round(sum(picked) / len(picked), 3),
                    "share_selected_p_wrong_1.0": round(
                        sum(1 for p in picked if p >= 0.999) / len(picked), 3
                    ),
                }
            )
    return out


# --- output -----------------------------------------------------------------


def write_csv(name, rows):
    if not rows:
        return
    RESULTS.mkdir(exist_ok=True)
    fields = list({k: None for r in rows for k in r})
    with (RESULTS / f"{name}.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def md_table(rows, fields=None):
    if not rows:
        return "_(empty)_\n"
    fields = fields or list({k: None for r in rows for k in r})
    head = "| " + " | ".join(fields) + " |\n"
    head += "| " + " | ".join("---" for _ in fields) + " |\n"
    body = "".join(
        "| " + " | ".join("" if r.get(f) is None else str(r.get(f)) for f in fields) + " |\n"
        for r in rows
    )
    return head + body


def figures(pressure, n50, topn, mock=False):
    FIGURES.mkdir(exist_ok=True)
    arms = sorted({r["arm"] for r in pressure})
    banner = (
        "SYNTHETIC: deterministic simulator (--dry-run), not a model"
        if mock
        else None
    )

    def stamp(fig):
        if banner:
            fig.text(0.5, 0.985, banner, ha="center", va="top", fontsize=7, color="#A00000")

    def series(arm, field):
        pts = [(r["n"], r[field]) for r in pressure if r["arm"] == arm and r["n"]]
        pts.sort()
        return [p[0] for p in pts], [p[1] for p in pts]

    for field, ylabel, fname in (
        ("acc", "test accuracy (%)", "fig_accuracy_vs_n"),
        ("confidently_wrong_rate", "confidently-wrong rate", "fig_confidently_wrong_vs_n"),
        ("router_miss_rate", "router miss rate (errors kept from the human)", "fig_router_miss_vs_n"),
    ):
        fig, ax = plt.subplots(figsize=(7.2, 4.4))
        for arm in arms:
            x, y = series(arm, field)
            if x:
                ax.plot(x, y, marker="o", label=arm)
        ax.set_xscale("log", base=2)
        ax.set_xticks(list(N_LADDER))
        ax.set_xticklabels([str(n) for n in N_LADDER])
        ax.set_xlabel("best-of-N candidate reports (N)")
        ax.set_ylabel(ylabel)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=6, loc="best")
        fig.tight_layout(rect=(0, 0, 1, 0.96 if banner else 1))
        stamp(fig)
        fig.savefig(FIGURES / f"{fname}.png", dpi=160)
        plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    labels = [r["arm"] for r in n50]
    vals = [r["n50"] if r["n50"] else 17.0 for r in n50]
    ax.barh(range(len(labels)), vals, color=["#4C78A8" if r["n50"] else "#BBBBBB" for r in n50])
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=6)
    ax.axvline(16, ls="--", c="k", lw=0.8)
    ax.set_xlabel("N50 (grey bar at 17 = never reaches 50% within N<=16)")
    fig.tight_layout(rect=(0, 0, 1, 0.96 if banner else 1))
    stamp(fig)
    fig.savefig(FIGURES / "fig_n50_by_arm.png", dpi=160)
    plt.close(fig)

    if topn:
        fig, ax = plt.subplots(figsize=(7.2, 4.0))
        for arm in sorted({r["arm"] for r in topn}):
            pts = sorted((r["n"], r["displacement_rate"]) for r in topn if r["arm"] == arm and r["n"])
            ax.plot([p[0] for p in pts], [p[1] for p in pts], marker="s", label=arm)
        ax.set_xscale("log", base=2)
        ax.set_xticks(list(N_LADDER))
        ax.set_xticklabels([str(n) for n in N_LADDER])
        ax.set_xlabel("best-of-N candidate reports (N)")
        ax.set_ylabel("gold label outside Top-3 candidates")
        ax.grid(alpha=0.3)
        ax.legend(fontsize=7)
        fig.tight_layout(rect=(0, 0, 1, 0.96 if banner else 1))
        stamp(fig)
        fig.savefig(FIGURES / "fig_topn_displacement_vs_n.png", dpi=160)
        plt.close(fig)


def human_arm_export(idx, selection, items, j_dev, n_each=20):
    """Phase 6 export only. Not run here: 20 C0 + 20 N=16 test items, shuffled, unlabelled."""
    import random

    sel = {s["item_id"]: s for s in selection}
    attack_log = defaultdict(dict)
    for path in (LOGS / "attack").glob("*.jsonl"):
        for line in path.open():
            rec = json.loads(line)
            attack_log[rec["item_id"]][rec["condition"]] = rec["raw"]
    test_ids = sorted(i for i, it in items.items() if it["split"] == "test" and i in sel)
    rng = random.Random(7)
    pool = rng.sample(test_ids, min(2 * n_each, len(test_ids)))
    rows = []
    for i, iid in enumerate(pool):
        it = items[iid]
        cond = "C0" if i < len(pool) // 2 else "N16"
        body = it["transcript"]
        if cond == "N16":
            chosen = int(sel[iid]["chosen"]["16"])
            report = attack_log[iid].get(f"cand{chosen}", "")
            body = body + "\n\n[Agent's final report]\n" + report
        rows.append(
            {
                "export_id": f"H{i:03d}",
                "item_id": iid,
                "dataset": it["dataset"],
                "condition": cond,
                "question": it["prompt_text"],
                "options": " | ".join(it["options"]),
                "record": body,
            }
        )
    rng.shuffle(rows)
    write_csv("human_arm_items", rows)
    return rows


_all_rows: list = []


README_BEGIN = "<!-- RESULTS:BEGIN -->"
README_END = "<!-- RESULTS:END -->"


def _inject_readme(tables_md: str):
    """Keep README's results section byte-identical to results/tables.md."""
    readme = ROOT / "README.md"
    if not readme.exists():
        return
    text = readme.read_text()
    if README_BEGIN not in text or README_END not in text:
        return
    head, _, rest = text.partition(README_BEGIN)
    _, _, tail = rest.partition(README_END)
    body = tables_md.split("\n", 1)[1].lstrip("\n").replace("\n## ", "\n### ")  # demote under README section 5
    readme.write_text(f"{head}{README_BEGIN}\n\n{body}\n{README_END}{tail}")


def main():
    global _all_rows
    rows, selection, meta, items = load()
    _all_rows = rows
    j_dev, held_out = meta["j_dev"], meta["held_out"]
    judges = [j_dev, *held_out]
    trio = cheapest_three(judges)

    idx = index(rows)
    arms = {}
    for model, method in sorted({(r["model"], r["method"]) for r in rows}):
        arms[f"{method} {model}"] = {
            (c, s): idx[(model, method, c, s)] for c in CONDS for s in ("dev", "test")
        }
    for label, weighted in (("M2 majority(3 cheapest)", False), ("M3 conf-weighted(3 cheapest)", True)):
        arms[label] = {
            (c, s): combine(idx, trio, c, s, items, weighted=weighted)
            for c in CONDS
            for s in ("dev", "test")
        }

    repro = t_reproduction(idx, judges)
    hill, best_single, common = t_hillclimb(idx, judges, trio, items)
    pressure = t_pressure(idx, arms, items)
    n50 = t_n50(arms)
    corr = t_correlation(idx, judges)
    transfer = t_transfer(idx, j_dev, held_out)
    topn = t_topn_displacement(idx)
    sel = t_selection(selection)

    for name, rs in (
        ("reproduction", repro),
        ("hillclimb", hill),
        ("pressure", pressure),
        ("n50", n50),
        ("error_correlation", corr),
        ("transfer", transfer),
        ("topn_displacement", topn),
        ("selection_strength", sel),
    ):
        write_csv(name, rs)
    figures(pressure, n50, topn, mock=bool(meta.get("mock")))
    human_arm_export(idx, selection, items, j_dev)

    label = (
        "**SYNTHETIC (--dry-run): every number below comes from the deterministic "
        "simulator in `pilot_a/fake.py`, not from a model.**"
        if meta.get("mock")
        else f"Live run. OpenRouter spend ${meta.get('openrouter_spend', 0):.4f}."
    )
    acc_vs_n = [
        {k: r[k] for k in ("arm", "condition", "n", "n_test", "acc", "ci_lo", "ci_hi",
                           "delta_vs_C0", "delta_ci_lo", "delta_ci_hi", "p", "p_holm")
         if k in r}
        for r in pressure
    ]
    md = [
        "# Results tables\n",
        label + "\n",
        f"Run: {meta['n_items']} items, K={meta['k']}, {meta['n_candidates']} candidate reports, "
        f"ladder {meta['ladder']}, J_dev `{j_dev}`, held-out {held_out}, attacker `{meta['attacker']}`.\n",
        f"Best single judge at C0 on the common test set (n={len(common)}): `{best_single}`.\n",
        "\n## 1. Reproduction (C0, test split)\n",
        "Paper columns are Sampura's reported AI-alone accuracy on the same dataset "
        "(Table 4 for Gemini 3 Flash / Sonnet 4.6, Table 2 for Qwen3.5-9B). "
        "**Different models, different item samples, different split: not a like-for-like replication.**\n",
        md_table(repro),
        "\n## 2. Static hill-climb (C0, test split)\n",
        md_table(hill),
        "\n## 3. Accuracy under pressure\n",
        md_table(acc_vs_n),
        "\n## 4. N50\n",
        md_table(n50),
        "\n## 5. Transfer to held-out judges (reports selected against J_dev)\n",
        md_table(transfer),
        "\n## 6. Error correlation across judges, C0 vs N=16\n",
        md_table(corr),
        "\n## 7. Top-N displacement\n",
        md_table(topn),
        "\n## 8. Selection strength (J_dev P(wrong label) of the chosen report)\n",
        md_table(sel),
    ]
    tables_md = "".join(md)
    (RESULTS / "tables.md").write_text(tables_md)
    _inject_readme(tables_md)
    summary = {
        "mock": bool(meta.get("mock")),
        "n_items": meta["n_items"],
        "k": meta["k"],
        "best_single_judge_C0": best_single,
        "n_common_test": len(common),
        "acc_by_arm_and_condition": {
            f"{r['arm']}|{r['condition']}": r["acc"] for r in pressure
        },
        "n50_by_arm": {r["arm"]: r["n50_display"] for r in n50},
        "confidently_wrong_by_arm_and_condition": {
            f"{r['arm']}|{r['condition']}": r["confidently_wrong_rate"] for r in pressure
        },
        "router_miss_by_arm_and_condition": {
            f"{r['arm']}|{r['condition']}": r["router_miss_rate"] for r in pressure
        },
        "openrouter_spend": meta.get("openrouter_spend", 0.0),
    }
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(f"wrote {RESULTS}/tables.md and {len(list(RESULTS.glob('*.csv')))} csv files")
    print(f"wrote {len(list(FIGURES.glob('*.png')))} figures")


if __name__ == "__main__":
    main()
