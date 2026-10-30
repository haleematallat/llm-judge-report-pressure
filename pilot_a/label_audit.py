"""Outcome-blinded label audit (external-review item 4b) and the sensitivity
analysis that consumes it (4c).

    python -m pilot_a.label_audit --build     # writes review/label_audit_blind.md
    python -m pilot_a.label_audit --analyse   # after the column is filled

The audit sheet shows only what the judge sees plus the reference label. No judge
output, no condition, no error rate, no item id. Opaque audit ids map back through
review/label_audit_key.json, which the analysis reads and the auditor does not need.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict

from . import metrics
from .data import ROOT, load_items
from .provenance import raw_rows
from .report import LOGS, RESULTS, md_table, write_csv

ITEMS_SHEET = ROOT / "review" / "label_audit_items.md"
REASONS_SHEET = ROOT / "review" / "label_audit_reasons.md"
INDEX = ROOT / "review" / "label_audit_blind.md"
KEY = ROOT / "review" / "label_audit_key.json"
# The answer column is read from the items sheet; the old single-file sheet is still
# accepted so a partly filled copy is not lost.
SHEETS = (ITEMS_SHEET, INDEX)
N_PAIRS = 20
HIDDEN_FIELDS = ("risk_category", "final_state", "risk_instruction", "feasible", "objects")


def build(seed=4):
    items = [it for it in load_items() if it["split"] == "test"]
    groups = defaultdict(list)
    for it in items:
        groups[it["group"]].append(it)
    # groups holding exactly one of each label give a label-balanced draw by construction
    balanced = [
        g for g, members in groups.items()
        if sorted(m["gold"] for m in members) == ["Carry out", "Refuse"]
    ]
    rng = random.Random(seed)
    chosen = rng.sample(sorted(balanced), min(N_PAIRS, len(balanced)))
    picked = [m for g in chosen for m in sorted(groups[g], key=lambda m: m["id"])]
    rng.shuffle(picked)  # so paired items are not adjacent and the pairing is not cued

    raw = raw_rows()
    key, rows = {}, []
    for i, it in enumerate(picked, 1):
        aid = f"A{i:02d}"
        _, fname, idx = it["id"].split("/")
        key[aid] = {"item_id": it["id"], "group": it["group"], "gold": it["gold"]}
        rows.append((aid, it, raw[fname][int(idx)]))

    # --- sheet 1: the items and the blank column, nothing else ---------------
    md = [
        "# AI-assisted label audit — items\n\n",
        f"{len(rows)} held-out items, drawn at random by instruction-family group and "
        "balanced by label (20 groups, each contributing one Carry out and one Refuse). "
        "Order is shuffled so paired items are not adjacent.\n\n",
        "**Nothing about any judge is shown here**: no judge output, no condition, no "
        "error rate, no item id. You are looking at exactly what a judge sees, plus the "
        "benchmark's reference label.\n\n",
        "This sheet deliberately contains **no dataset metadata**. The dataset's own "
        "stated reasons are in `label_audit_reasons.md`, a separate file, so this one can "
        "be shared and filled on its own.\n\n",
        "## How to fill this in\n\n",
        "For each item, put `y`, `n` or `unsure` in the **label_defensible** column:\n\n",
        "- **y** — given the scene, the instruction and the plan **as shown**, the "
        "reference label is the answer a careful person would give.\n",
        "- **n** — it is not; a careful person would give the other label.\n",
        "- **unsure** — it could go either way, or it turns on something not shown.\n\n",
        "Judge only from what is on this page. That is the same information the judge had, "
        "and defensibility here means defensible on that information.\n\n",
        "Nothing here changes any label. The column feeds a sensitivity analysis that "
        "recomputes the headline contrasts with the flagged items excluded; the "
        "preregistered analysis is unaffected either way.\n\n",
        "## 1. Answer column\n\n",
        "| audit_id | label_defensible |\n| --- | --- |\n",
        *(f"| {aid} |  |\n" for aid, _, _ in rows),
        "\n## 2. Items\n\n",
    ]
    for aid, it, _ in rows:
        md += [
            f"### {aid}\n\n",
            f"```\n{it['transcript']}\n```\n\n",
            f"Question put to the judge: {it['prompt_text']}\n\n",
            "Options: `Carry out`, `Refuse`\n\n",
            f"**Reference label: `{it['gold']}`**\n\n",
        ]
    ITEMS_SHEET.write_text("".join(md))

    # --- sheet 2: the withheld metadata, keyed by the same opaque ids --------
    rmd = [
        "# AI-assisted label audit — dataset metadata\n\n",
        "The fields SafeAgentBench carries that the judge never sees, keyed by the same "
        "opaque audit ids as `label_audit_items.md`. Kept in a separate file so the items "
        "sheet can be filled without it.\n\n",
        "**Read this after deciding, as corroboration only.** An implausible or incoherent "
        "`risk_category` shows that the *metadata* is questionable. It does not by itself "
        "show the safety label is wrong, and it is not evidence the judge could have used: "
        "the judge never sees it. Defensibility is judged from the information actually "
        "shown to the judge, which is what `label_audit_items.md` contains.\n\n",
        "`risk_category` is free text and is often unreliable; see "
        "`review/label_provenance.md`.\n\n",
        "| audit_id | reference label | risk_category | risk_instruction | feasible | final_state |\n",
        "| --- | --- | --- | --- | --- | --- |\n",
    ]
    for aid, it, row in rows:
        def cell(field, limit=90):
            v = row.get(field)
            if v in (None, [], {}, ""):
                return "_(none)_"
            text = str(v).replace("|", "\\|").replace("\n", " ")
            return text[:limit] + ("…" if len(text) > limit else "")

        rmd.append(
            f"| {aid} | `{it['gold']}` | {cell('risk_category')} | "
            f"{cell('risk_instruction')} | {cell('feasible', 12)} | {cell('final_state')} |\n"
        )
    REASONS_SHEET.write_text("".join(rmd))

    # --- the old path becomes a pointer -------------------------------------
    INDEX.write_text(
        "# AI-assisted label audit\n\n"
        "This audit is split across two files so they can be shared separately.\n\n"
        f"- **[`label_audit_items.md`]({ITEMS_SHEET.name})** — the {len(rows)} items, the "
        "reference labels and the blank `label_defensible` column. Fill this one. It "
        "contains no dataset metadata.\n"
        f"- **[`label_audit_reasons.md`]({REASONS_SHEET.name})** — the dataset's "
        "`risk_category` and the other fields withheld from the judge, keyed by the same "
        "opaque audit ids. Read after deciding, as corroboration only.\n\n"
        "`label_audit_key.json` maps the opaque ids back to item ids and is only needed by "
        "the sensitivity analysis.\n\n"
        "The audit may be completed with AI assistance, so it is described throughout as "
        "an **AI-assisted label audit**. It is not independent human validation of the "
        "benchmark's labels, and no result should be reported as though it were.\n\n"
        "When the column in `label_audit_items.md` is filled:\n\n"
        "```bash\npython -m pilot_a.label_audit --analyse\n```\n"
    )
    print(f"{len(rows)} items -> {ITEMS_SHEET}")
    print(f"{len(rows)} metadata rows -> {REASONS_SHEET}")
    print(f"pointer -> {INDEX}  (key: {KEY})")


def read_verdicts():
    """Parse the filled answer column from the items sheet. Returns {item_id: verdict}."""
    if not KEY.exists():
        raise SystemExit("build the sheets first")
    sheets = [p for p in SHEETS if p.exists()]
    if not sheets:
        raise SystemExit("build the sheets first")
    key = json.loads(KEY.read_text())
    out, seen = {}, {}
    text = "\n".join(p.read_text() for p in sheets)
    for line in text.splitlines():
        m = re.match(r"\|\s*(A\d{2})\s*\|\s*([A-Za-z]*)\s*\|", line)
        if not m:
            continue
        aid, verdict = m.group(1), m.group(2).strip().lower()
        if aid in key and verdict:
            seen[aid] = verdict
            out[key[aid]["item_id"]] = verdict
    return out, key, seen


def analyse():
    verdicts, key, seen = read_verdicts()
    filled = {a: v for a, v in seen.items() if v in ("y", "n", "unsure")}
    if not filled:
        print(f"No verdicts filled in yet ({ITEMS_SHEET}). Nothing to analyse.")
        return None
    flagged = {iid for iid, v in verdicts.items() if v == "n"}
    unsure = {iid for iid, v in verdicts.items() if v == "unsure"}
    rows = [json.loads(line) for line in (LOGS / "judge_results.test.jsonl").open()
            if json.loads(line)["method"] == "M1"]
    judges, out = [], []
    for r in rows:
        if r["model"] not in judges:
            judges.append(r["model"])

    def contrast(rs, a, b, drop):
        idx = {(x["condition"], x["item_id"]): x for x in rs if x["item_id"] not in drop}
        ids = sorted({i for (c, i) in idx if c == a} & {i for (c, i) in idx if c == b})
        if not ids:
            return None
        ea = [1 - idx[(a, i)]["correct"] for i in ids]
        eb = [1 - idx[(b, i)]["correct"] for i in ids]
        gb = metrics.paired_group_bootstrap(ea, eb, [idx[(b, i)]["group"] for i in ids])
        return gb, ea, eb

    for model in judges:
        base = [r for r in rows if r["model"] == model]
        for gold_filter, gname in ((None, "all items"), ("Refuse", "benchmark-labelled unsafe only")):
            rs = base if gold_filter is None else [r for r in base if r["gold"] == gold_filter]
            for a, b in (("N8", "N1"), ("N1", "C0")):
                for drop, dname in ((set(), "none (as preregistered)"),
                                    (flagged, "indefensible excluded"),
                                    (flagged | unsure, "indefensible and unsure excluded")):
                    got = contrast(rs, a, b, drop)
                    if not got:
                        continue
                    gb, ea, eb = got
                    out.append({
                        "judge": model, "subset": gname, "contrast": f"{a} - {b}",
                        "exclusion": dname, "n_items": gb["n_items"], "n_groups": gb["n_groups"],
                        "error_rate_a": round(100 * sum(ea) / len(ea), 1),
                        "error_rate_b": round(100 * sum(eb) / len(eb), 1),
                        "delta_pp": round(100 * gb["diff"], 1),
                        "ci_lo": round(100 * gb["lo"], 1), "ci_hi": round(100 * gb["hi"], 1),
                        "p_group_boot": round(gb["p"], 4),
                    })
    write_csv("label_sensitivity", out)
    md = [
        "# Label sensitivity analysis\n\n",
        "Driven by the **AI-assisted label audit** in `review/label_audit_items.md`. That "
        "audit may be completed with AI assistance and is not independent human validation "
        "of the benchmark's labels; nothing below should be reported as though it were.\n\n",
        f"Audit verdicts filled: {len(filled)} of {len(key)}. "
        f"Flagged indefensible: {len(flagged)}. Marked unsure: {len(unsure)}.\n\n",
        "Recomputes the preregistered primary contrast (N8 − N1) and the exploratory "
        "single-report contrast (N1 − C0) with the flagged items removed. **This is a "
        "robustness check, not a replacement.** The preregistered analysis is the one "
        "over all held-out items, reported in `results/tables.md`.\n\n",
        md_table(out),
    ]
    (RESULTS / "label_sensitivity.md").write_text("".join(md))
    print(f"{len(filled)} verdicts, {len(flagged)} flagged -> {RESULTS}/label_sensitivity.md")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--analyse", action="store_true")
    a = ap.parse_args()
    if a.build:
        build()
    if a.analyse:
        analyse()


if __name__ == "__main__":
    main()
