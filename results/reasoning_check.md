# Reasoning-on check (secondary, preregistration §7)

Target judge `qwen/qwen3.7-flash` on 60 held-out items, C0 and N=8 only, reusing the reports the main run selected. The main run's judges run with reasoning disabled or minimal; this one uses the provider's default, so reasoning is on. Same items, same reports, same K.

**Read this table with the refusal column.** With reasoning on, the judge spends its output budget on reasoning tokens and often returns nothing parseable, even at a 300-token cap. Roughly 55% of individual samples and a double-digit number of whole items come back with no usable answer, and an item with no usable answer is scored as an error. `error_rate_all_items` therefore mixes attack success with parse failure. `error_rate_answered_only` removes the unanswered items, but it conditions on an outcome produced after the treatment, so the two conditions no longer rest on the same set of items. Neither column is a clean estimate; both are given so the gap between them is visible.

## Error rate

| judge_config | condition | n_items | n_groups | error_rate_all_items | ci_lo | ci_hi | items_with_no_usable_answer | error_rate_answered_only | mean_self_consistency | unparseable_sample_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reasoning ON (this check) | C0 | 60 | 31 | 38.3 | 27.1 | 51.0 | 15 | 17.8 | 0.44 | 0.553 |
| reasoning ON (this check) | N8 | 60 | 31 | 95.0 | 86.3 | 98.3 | 11 | 93.9 | 0.45 | 0.547 |
| reasoning OFF (main run) | C0 | 60 | 31 | 36.7 | 25.6 | 49.3 | 0 | 36.7 | 0.877 | 0.0 |
| reasoning OFF (main run) | N8 | 60 | 31 | 95.0 | 86.3 | 98.3 | 0 | 95.0 | 0.977 | 0.0 |

## N=8 vs C0 under each configuration (all items, refusals scored as errors)

| judge_config | contrast | n_items | n_groups | error_rate_N8 | error_rate_C0 | delta_pp | ci_lo | ci_hi | p_group_boot |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reasoning ON (this check) | N8 - C0 | 60 | 31 | 95.0 | 38.3 | 56.7 | 42.6 | 70.5 | 0.0001 |
| reasoning OFF (main run) | N8 - C0 | 60 | 31 | 95.0 | 36.7 | 58.3 | 47.5 | 69.0 | 0.0001 |

This is a secondary check on how much of the measured attack success depends on the judges running without reasoning. It is not the primary comparison, and its refusal rate means it cannot settle the question on its own.
