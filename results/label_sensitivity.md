# Label sensitivity analysis

Driven by the **AI-assisted label audit**. That audit may be completed with AI assistance and is not independent human validation of the benchmark's labels; nothing below should be reported as though it were.

## The frozen result is unchanged

The preregistered analysis is the one over **all held-out items**, reported in `results/tables.md`. It is reproduced below as the first row of every block and is not replaced, re-weighted or corrected by anything in this file. The defensible-subset rows are a **robustness check on a different set of items**, and they are valid only for the items actually audited.

## Why mislabelling is not benign here

With two options, a wrong reference label flips that item's correctness indicator in *every* condition, so the item's contribution to a paired difference becomes its own negative rather than cancelling. If a fraction f of items are mislabelled the aggregate paired difference can move by up to **2f**. On this data the bound is attainable: adversarially choosing 10% of items to flip moves the primary N8 - N1 contrast on the target judge by -20.0pp, from +9.1pp to -10.9pp, reversing its sign.

## Audit coverage

| items_audited | share_of_held_out_pool | flagged_indefensible | flag_rate | flag_rate_ci_lo | flag_rate_ci_hi | marked_unsure | worst_case_shift_pp_at_point_estimate | worst_case_shift_pp_at_ci_upper |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 450 | 1.0 | 26 | 5.8 | 4.0 | 8.3 | 56 | 11.6 | 16.7 |

450 of 450 held-out items have been audited (100.0%). The flag rate is a **sample estimate with a wide interval**, not a population rate: 26/450 = 5.8% [4.0, 8.3]. Taking the interval's upper end, the worst-case shift bound is 16.7pp. Excluding audited items validates only those items; it says nothing about the un-audited remainder, which is where most of the pool still sits.

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
| qwen/qwen3.7-flash | all items | N8 - N1 | defensible subset: flagged indefensible removed | 424 | 223 | 92.9 | 83.5 | 9.4 | 6.5 | 12.4 | 0.0001 |
| qwen/qwen3.7-flash | all items | N8 - N1 | defensible subset: indefensible and unsure removed | 368 | 222 | 91.8 | 81.8 | 10.1 | 6.8 | 13.2 | 0.0001 |
| qwen/qwen3.7-flash | all items | N1 - C0 | FROZEN: all items, as preregistered | 450 | 224 | 84.2 | 36.7 | 47.6 | 43.0 | 52.2 | 0.0001 |
| qwen/qwen3.7-flash | all items | N1 - C0 | defensible subset: flagged indefensible removed | 424 | 223 | 83.5 | 35.6 | 47.9 | 43.0 | 52.7 | 0.0001 |
| qwen/qwen3.7-flash | all items | N1 - C0 | defensible subset: indefensible and unsure removed | 368 | 222 | 81.8 | 31.8 | 50.0 | 44.7 | 55.2 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N8 - N1 | FROZEN: all items, as preregistered | 226 | 221 | 86.7 | 69.9 | 16.8 | 11.5 | 22.3 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N8 - N1 | defensible subset: flagged indefensible removed | 203 | 198 | 85.2 | 67.0 | 18.2 | 12.4 | 24.3 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N8 - N1 | defensible subset: indefensible and unsure removed | 159 | 155 | 81.1 | 59.7 | 21.4 | 14.5 | 28.7 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N1 - C0 | FROZEN: all items, as preregistered | 226 | 221 | 69.9 | 42.0 | 27.9 | 21.1 | 34.8 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N1 - C0 | defensible subset: flagged indefensible removed | 203 | 198 | 67.0 | 40.9 | 26.1 | 19.0 | 33.2 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N1 - C0 | defensible subset: indefensible and unsure removed | 159 | 155 | 59.7 | 34.0 | 25.8 | 17.6 | 34.0 | 0.0001 |
| openai/gpt-5-nano | all items | N8 - N1 | FROZEN: all items, as preregistered | 450 | 224 | 84.0 | 83.1 | 0.9 | -1.5 | 3.3 | 0.5226 |
| openai/gpt-5-nano | all items | N8 - N1 | defensible subset: flagged indefensible removed | 424 | 223 | 83.3 | 82.3 | 0.9 | -1.4 | 3.4 | 0.5178 |
| openai/gpt-5-nano | all items | N8 - N1 | defensible subset: indefensible and unsure removed | 368 | 222 | 82.6 | 81.2 | 1.4 | -1.3 | 4.1 | 0.371 |
| openai/gpt-5-nano | all items | N1 - C0 | FROZEN: all items, as preregistered | 450 | 224 | 83.1 | 47.6 | 35.6 | 32.1 | 39.0 | 0.0001 |
| openai/gpt-5-nano | all items | N1 - C0 | defensible subset: flagged indefensible removed | 424 | 223 | 82.3 | 49.5 | 32.8 | 29.0 | 36.5 | 0.0001 |
| openai/gpt-5-nano | all items | N1 - C0 | defensible subset: indefensible and unsure removed | 368 | 222 | 81.2 | 53.8 | 27.4 | 23.3 | 31.5 | 0.0001 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N8 - N1 | FROZEN: all items, as preregistered | 226 | 221 | 68.1 | 67.3 | 0.9 | -3.6 | 5.4 | 0.7746 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N8 - N1 | defensible subset: flagged indefensible removed | 203 | 198 | 65.0 | 64.0 | 1.0 | -3.9 | 5.9 | 0.7884 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N8 - N1 | defensible subset: indefensible and unsure removed | 159 | 155 | 59.7 | 57.9 | 1.9 | -3.8 | 7.7 | 0.5968 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N1 - C0 | FROZEN: all items, as preregistered | 226 | 221 | 67.3 | 0.4 | 66.8 | 60.6 | 72.9 | 0.0001 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N1 - C0 | defensible subset: flagged indefensible removed | 203 | 198 | 64.0 | 0.0 | 64.0 | 57.2 | 70.6 | 0.0001 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N1 - C0 | defensible subset: indefensible and unsure removed | 159 | 155 | 57.9 | 0.0 | 57.9 | 50.0 | 65.6 | 0.0001 |
