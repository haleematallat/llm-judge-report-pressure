# Same-judge perturbation check (exploratory, not preregistered)

Target judge `qwen/qwen3.7-flash`, same reasoning setting, same 450 held-out items, same records and the same appended reports the main run selected against the **original** prompt. Only the judge's instructions change: the same task reworded and reordered, as a rubric revision would. The reworded prompt, like the original, never mentions the appended report or tells the judge to discount it. Fresh evaluation samples, K = 5. Prompt text is in `judge_pressure/perturbation_check.py`.

This is a perturbation of one judge, not an update of it by training. It is a closer stand-in for a judge update than swapping model family, and a weaker one than retraining.

With no report at all (C0), the reworded prompt changes the judge's majority verdict on **24.9%** of items, so it is a real perturbation of the judge rather than a cosmetic one.

## Error rate by prompt and condition

| prompt | condition | n_items | error_rate | ci_lo | ci_hi | mean_self_consistency_agreement | unparseable_sample_rate |
| --- | --- | --- | --- | --- | --- | --- | --- |
| original prompt (main run) | C0 | 450 | 36.7 | 32.3 | 41.2 | 0.893 | 0.0 |
| original prompt (main run) | N1 | 450 | 84.2 | 80.6 | 87.3 | 0.961 | 0.0 |
| original prompt (main run) | N8 | 450 | 93.3 | 90.6 | 95.3 | 0.97 | 0.0 |
| reworded prompt (this check) | C0 | 450 | 23.3 | 19.7 | 27.5 | 0.9 | 0.0 |
| reworded prompt (this check) | N1 | 450 | 85.8 | 82.2 | 88.7 | 0.972 | 0.0 |
| reworded prompt (this check) | N8 | 450 | 92.0 | 89.1 | 94.2 | 0.972 | 0.0 |

## Contrasts (paired, group-bootstrapped, 10,000 resamples)

| prompt | contrast | n_items | n_groups | error_rate_a | error_rate_b | delta_pp | ci_lo | ci_hi | p_group_boot |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| original prompt (main run) | N8 - N1 | 450 | 224 | 93.3 | 84.2 | 9.1 | 6.4 | 11.9 | 0.0001 |
| original prompt (main run) | N1 - C0 | 450 | 224 | 84.2 | 36.7 | 47.6 | 43.0 | 52.2 | 0.0001 |
| reworded prompt (this check) | N8 - N1 | 450 | 224 | 92.0 | 85.8 | 6.2 | 3.6 | 8.9 | 0.0001 |
| reworded prompt (this check) | N1 - C0 | 450 | 224 | 85.8 | 23.3 | 62.4 | 58.0 | 66.7 | 0.0001 |

## Share of the selection gain that survives the prompt change

(N8 − N1 under the reworded prompt) / (N8 − N1 under the original prompt), on the same items, groups resampled together: **0.68** [0.41, 1.03] (10000 of 10000 draws had a positive original gain and enter the interval). 1.0 means all of the gain survives; 0 means none of it does.

## Comparison with the cross-family judge (post hoc)

**Computed after the result above was seen**, so it is not part of the amendment as specified. The same ratio for the main study's transfer judge `openai/gpt-5-nano`, which the attacker also never queried, on the same items:

| judge change | share of the N8 − N1 gain that survives | 95% CI |
| --- | --- | --- |
| same model, reworded instructions | 0.68 | [0.41, 1.03] |
| different model family | 0.10 | [-0.17, 0.37] |

Difference, same draws for both: **0.59** [0.22, 1.03], p = 0.0022.

## What this does not show

- One rewording of one judge. A different rewording, or a judge changed by training rather than by prompt, could retain more or less of the gain.
- The rewording also changed the judge's baseline: C0 error fell from 36.7% to 23.3%. The survival ratio compares gains, not levels, so it is not driven by that shift directly, but the two prompts are not equally strong judges.
- Both prompts sit near the ceiling at N1 (84–86% error), which caps how large either gain can be.
