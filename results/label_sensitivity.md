# Label sensitivity analysis

Driven by the **AI-assisted label audit**. That audit may be completed with AI assistance and is not independent human validation of the benchmark's labels; nothing below should be reported as though it were.

## The frozen result is unchanged

The preregistered analysis is the one over **all held-out items**, reported in `results/tables.md`. It is reproduced below as the first row of every block and is not replaced, re-weighted or corrected by anything in this file. The defensible-subset rows are a **robustness check on a different set of items**, and they are valid only for the items actually audited.

## Why mislabelling is not benign here

With two options, a wrong reference label flips that item's correctness indicator in *every* condition, so the item's contribution to a paired difference becomes its own negative rather than cancelling. If a fraction f of items are mislabelled the aggregate paired difference can move by up to **2f**. On this data the bound is attainable: adversarially choosing 10% of items to flip moves the primary N8 - N1 contrast on the target judge by -20.0pp, from +9.1pp to -10.9pp, reversing its sign.

## Audit coverage

| items_audited | held_out_pool | share_of_held_out_pool | review_rows_filled | verdicts_overridden_by_review | flagged_indefensible | flag_rate | flag_rate_ci_lo | flag_rate_ci_hi | marked_unsure | worst_case_shift_pp_if_flagged_are_all_mislabelled |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 450 | 450 | 1.0 | 112 | 59 | 32 | 7.1 | 5.1 | 9.9 | 4 | 14.2 |

**All 450 held-out items have been audited; coverage is complete.** The residual risk is no longer un-audited items — there are none — but **auditor error**. The audit is AI-assisted, each item was seen by one agent, and an item whose label is wrong but was marked defensible appears nowhere in this file.

**Reliability evidence.** Two independent blinded audits covered the same 40 items — the 40-item sample and the full-pool pass. They agree exactly on **37/40** (92.5%): n->n 3, n->unsure 1, unsure->unsure 3, unsure->y 2, y->y 31. Every disagreement is one step between `unsure` and a decision; there is no straight `y`/`n` reversal. This is the only direct evidence here on how reliable a single audit pass is, and it rests on 40 items.

**The 2f bound still applies, now to undetected mislabels.** Complete coverage removes the un-audited gap, not the possibility that the audit itself missed wrong labels. If a further fraction f of labels are wrong and were marked defensible, the aggregate paired difference can still move by up to 2f, and those items are by construction absent from every exclusion below: an undetected 5% would permit another 10pp of movement, against a primary contrast of +9.1pp. The 32 detected flags are 7.1% [5.1, 9.9] of the pool.

**Haleema's review is complete.** `review/label_audit_haleema_review.md` has 112 of its 112 rows filled: **59** verdicts here come from its final column and override the agent's, and 53 rows are marked `agree`, confirming the agent without changing anything.

## By audit agent

Each agent saw one contiguous block of ids and only that block.

| block | items | y | n | unsure | indefensible_label | insufficient_context | ambiguous_criteria |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F001-F150 | 150 | 138 | 9 | 3 | 8 | 10 | 8 |
| F151-F300 | 150 | 138 | 11 | 1 | 8 | 5 | 15 |
| F301-F450 | 150 | 138 | 12 | 0 | 10 | 2 | 16 |

## Problem types

| problem_type | count |
| --- | --- |
| ambiguous_criteria | 39 |
| indefensible_label | 26 |
| insufficient_context | 17 |
| none | 368 |


## Contrasts

| judge | subset | contrast | analysis | n_items | n_groups | error_rate_a | error_rate_b | delta_pp | ci_lo | ci_hi | p_group_boot |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.7-flash | all items | N8 - N1 | FROZEN: all items, as preregistered | 450 | 224 | 93.3 | 84.2 | 9.1 | 6.4 | 11.9 | 0.0001 |
| qwen/qwen3.7-flash | all items | N8 - N1 | defensible subset: flagged indefensible removed | 418 | 223 | 92.8 | 83.3 | 9.6 | 6.6 | 12.6 | 0.0001 |
| qwen/qwen3.7-flash | all items | N8 - N1 | defensible subset: indefensible and unsure removed | 414 | 222 | 92.8 | 83.1 | 9.7 | 6.7 | 12.7 | 0.0001 |
| qwen/qwen3.7-flash | all items | N1 - C0 | FROZEN: all items, as preregistered | 450 | 224 | 84.2 | 36.7 | 47.6 | 43.0 | 52.2 | 0.0001 |
| qwen/qwen3.7-flash | all items | N1 - C0 | defensible subset: flagged indefensible removed | 418 | 223 | 83.3 | 35.6 | 47.6 | 42.7 | 52.5 | 0.0001 |
| qwen/qwen3.7-flash | all items | N1 - C0 | defensible subset: indefensible and unsure removed | 414 | 222 | 83.1 | 35.3 | 47.8 | 42.9 | 52.7 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N8 - N1 | FROZEN: all items, as preregistered | 226 | 221 | 86.7 | 69.9 | 16.8 | 11.5 | 22.3 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N8 - N1 | defensible subset: flagged indefensible removed | 205 | 200 | 85.4 | 67.3 | 18.0 | 12.3 | 24.0 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N8 - N1 | defensible subset: indefensible and unsure removed | 202 | 197 | 85.1 | 66.8 | 18.3 | 12.4 | 24.4 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N1 - C0 | FROZEN: all items, as preregistered | 226 | 221 | 69.9 | 42.0 | 27.9 | 21.1 | 34.8 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N1 - C0 | defensible subset: flagged indefensible removed | 205 | 200 | 67.3 | 40.5 | 26.8 | 19.8 | 34.0 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N1 - C0 | defensible subset: indefensible and unsure removed | 202 | 197 | 66.8 | 40.1 | 26.7 | 19.5 | 34.0 | 0.0001 |
| openai/gpt-5-nano | all items | N8 - N1 | FROZEN: all items, as preregistered | 450 | 224 | 84.0 | 83.1 | 0.9 | -1.5 | 3.3 | 0.5226 |
| openai/gpt-5-nano | all items | N8 - N1 | defensible subset: flagged indefensible removed | 418 | 223 | 83.0 | 82.1 | 1.0 | -1.4 | 3.4 | 0.5178 |
| openai/gpt-5-nano | all items | N8 - N1 | defensible subset: indefensible and unsure removed | 414 | 222 | 82.9 | 81.9 | 1.0 | -1.5 | 3.5 | 0.5066 |
| openai/gpt-5-nano | all items | N1 - C0 | FROZEN: all items, as preregistered | 450 | 224 | 83.1 | 47.6 | 35.6 | 32.1 | 39.0 | 0.0001 |
| openai/gpt-5-nano | all items | N1 - C0 | defensible subset: flagged indefensible removed | 418 | 223 | 82.1 | 48.3 | 33.7 | 30.0 | 37.5 | 0.0001 |
| openai/gpt-5-nano | all items | N1 - C0 | defensible subset: indefensible and unsure removed | 414 | 222 | 81.9 | 48.6 | 33.3 | 29.6 | 37.1 | 0.0001 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N8 - N1 | FROZEN: all items, as preregistered | 226 | 221 | 68.1 | 67.3 | 0.9 | -3.6 | 5.4 | 0.7746 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N8 - N1 | defensible subset: flagged indefensible removed | 205 | 200 | 65.4 | 64.4 | 1.0 | -3.9 | 5.9 | 0.7838 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N8 - N1 | defensible subset: indefensible and unsure removed | 202 | 197 | 64.9 | 63.9 | 1.0 | -3.9 | 6.0 | 0.7834 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N1 - C0 | FROZEN: all items, as preregistered | 226 | 221 | 67.3 | 0.4 | 66.8 | 60.6 | 72.9 | 0.0001 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N1 - C0 | defensible subset: flagged indefensible removed | 205 | 200 | 64.4 | 0.0 | 64.4 | 57.6 | 71.0 | 0.0001 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N1 - C0 | defensible subset: indefensible and unsure removed | 202 | 197 | 63.9 | 0.0 | 63.9 | 56.9 | 70.6 | 0.0001 |
