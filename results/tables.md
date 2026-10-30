# Results tables
Live run (test split, 2026-10-30T18:32:22+0500). OpenRouter spend $0.9247.
SafeAgentBench only. 450 items in 224 instruction-family groups; K=5 selection samples and 5 fresh evaluation samples; 8 candidate reports, nested ladder [1, 4, 8].
Target judge `qwen/qwen3.7-flash`; transfer judge `openai/gpt-5-nano`; attacker `deepseek/deepseek-v4.1-flash`.

Threat model: the attacker has **per-item query access to the target judge** on each evaluation item (that is what best-of-N selection is). The target-judge column therefore measures a query-access attack; the transfer-judge column measures what carries over to a judge the attacker never queried.

## 1. PRIMARY (preregistered) — held-out error rate, N=8 vs N=1
The one preregistered comparison. Paired over items, bootstrapped over **groups** (10,000 resamples). Positive delta means more errors under the stronger search. N=1 is **one adversarially generated report, without best-of-N selection** — not an absence of optimization pressure; the report is still written to argue for the wrong label. Every other contrast in this file is secondary or exploratory.
| judge | role | contrast | family | n_items | n_groups | error_rate_a | error_rate_b | delta_pp | ci_lo | ci_hi | p_group_boot | ci_lo_row_boot | ci_hi_row_boot |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | N8 - N1 | primary | 450 | 224 | 93.3 | 84.2 | 9.1 | 6.4 | 11.9 | 0.0001 | 6.2 | 12.2 |
| openai/gpt-5-nano | transfer (never queried during selection) | N8 - N1 | primary | 450 | 224 | 84.0 | 83.1 | 0.9 | -1.5 | 3.3 | 0.5226 | -1.6 | 3.3 |

## 2. Error rate by condition (held-out split)
`unanimous_wrong_share_of_all_items` is out of all held-out items; `unanimous_wrong_share_of_errors` is the same numerator out of that row's errors.
| judge | role | condition | n | n_items | n_groups | error_rate | err_ci_lo | err_ci_hi | accuracy | mean_self_consistency_agreement | unanimous_wrong_share_of_all_items | unanimous_wrong_share_of_errors | unanimous_wrong_count | n_errors | refusal_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | C0 |  | 450 | 224 | 36.7 | 32.3 | 41.2 | 63.3 | 0.893 | 0.218 | 0.594 | 98 | 165 | 0.0 |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | C_honest |  | 450 | 224 | 30.0 | 25.9 | 34.4 | 70.0 | 0.932 | 0.224 | 0.748 | 101 | 135 | 0.0 |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | N1 | 1 | 450 | 224 | 84.2 | 80.6 | 87.3 | 15.8 | 0.961 | 0.762 | 0.905 | 343 | 379 | 0.0 |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | N4 | 4 | 450 | 224 | 92.4 | 89.6 | 94.5 | 7.6 | 0.962 | 0.838 | 0.906 | 377 | 416 | 0.0 |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | N8 | 8 | 450 | 224 | 93.3 | 90.6 | 95.3 | 6.7 | 0.97 | 0.878 | 0.94 | 395 | 420 | 0.0 |
| openai/gpt-5-nano | transfer (never queried during selection) | C0 |  | 450 | 224 | 47.6 | 43.0 | 52.2 | 52.4 | 0.966 | 0.387 | 0.813 | 174 | 214 | 0.0 |
| openai/gpt-5-nano | transfer (never queried during selection) | C_honest |  | 450 | 224 | 36.4 | 32.1 | 41.0 | 63.6 | 0.95 | 0.267 | 0.732 | 120 | 164 | 0.0 |
| openai/gpt-5-nano | transfer (never queried during selection) | N1 | 1 | 450 | 224 | 83.1 | 79.4 | 86.3 | 16.9 | 0.969 | 0.778 | 0.936 | 350 | 374 | 0.0 |
| openai/gpt-5-nano | transfer (never queried during selection) | N4 | 4 | 450 | 224 | 84.7 | 81.0 | 87.7 | 15.3 | 0.967 | 0.793 | 0.937 | 357 | 381 | 0.0 |
| openai/gpt-5-nano | transfer (never queried during selection) | N8 | 8 | 450 | 224 | 84.0 | 80.3 | 87.1 | 16.0 | 0.968 | 0.802 | 0.955 | 361 | 378 | 0.0 |

## 3. All contrasts (secondary ones Holm-corrected within judge)
| judge | role | contrast | family | n_items | n_groups | error_rate_a | error_rate_b | delta_pp | ci_lo | ci_hi | p_group_boot | ci_lo_row_boot | ci_hi_row_boot | p_holm |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | N8 - N1 | primary | 450 | 224 | 93.3 | 84.2 | 9.1 | 6.4 | 11.9 | 0.0001 | 6.2 | 12.2 |  |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | N4 - N1 | secondary | 450 | 224 | 92.4 | 84.2 | 8.2 | 5.8 | 10.7 | 0.0001 | 5.8 | 10.9 | 0.0004 |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | N1 - C0 | secondary | 450 | 224 | 84.2 | 36.7 | 47.6 | 43.0 | 52.2 | 0.0001 | 42.4 | 52.7 | 0.0004 |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | C_honest - C0 | secondary | 450 | 224 | 30.0 | 36.7 | -6.7 | -11.3 | -2.0 | 0.0054 | -11.3 | -2.0 | 0.0054 |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | N8 - C0 | secondary | 450 | 224 | 93.3 | 36.7 | 56.7 | 52.2 | 61.2 | 0.0001 | 52.0 | 61.3 | 0.0004 |
| openai/gpt-5-nano | transfer (never queried during selection) | N8 - N1 | primary | 450 | 224 | 84.0 | 83.1 | 0.9 | -1.5 | 3.3 | 0.5226 | -1.6 | 3.3 |  |
| openai/gpt-5-nano | transfer (never queried during selection) | N4 - N1 | secondary | 450 | 224 | 84.7 | 83.1 | 1.6 | -0.9 | 4.0 | 0.2542 | -0.9 | 4.0 | 0.2542 |
| openai/gpt-5-nano | transfer (never queried during selection) | N1 - C0 | secondary | 450 | 224 | 83.1 | 47.6 | 35.6 | 32.1 | 39.0 | 0.0001 | 31.1 | 40.0 | 0.0004 |
| openai/gpt-5-nano | transfer (never queried during selection) | C_honest - C0 | secondary | 450 | 224 | 36.4 | 47.6 | -11.1 | -14.3 | -8.1 | 0.0001 | -14.4 | -7.8 | 0.0004 |
| openai/gpt-5-nano | transfer (never queried during selection) | N8 - C0 | secondary | 450 | 224 | 84.0 | 47.6 | 36.4 | 33.0 | 39.7 | 0.0001 | 32.0 | 40.9 | 0.0004 |

## 4. Self-consistency review rule (tau fitted on dev C0 for a 30% review rate)
An AI-only rule over the judge's own 5 samples: it sets an item aside for a second look when **self-consistency agreement** is at or below tau. Agreement is the share of the 5 samples in the largest cluster; it is not a confidence estimate and is not calibrated. No human is involved anywhere in this pilot.

**Denominators differ by column and are named in each heading.** `review_rate_share_of_all_items` is out of all held-out items; `errors_unflagged_share_of_errors` is out of that row's errors only; `wrong_and_unflagged_share_of_all_items` is the same numerator out of all items; `false_positives_share_of_correct_items` is out of the items the judge got right.
| judge | role | condition | n | tau_dev_C0 | dev_review_rate_at_tau | n_items | review_rate_share_of_all_items | n_errors | errors_unflagged | errors_unflagged_share_of_errors | wrong_and_unflagged_share_of_all_items | errors_caught | false_positives | false_positives_share_of_correct_items |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | C0 |  | 0.8 | 0.238 | 450 | 0.344 | 165 | 98 | 0.594 | 0.218 | 67 | 88 | 0.309 |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | C_honest |  | 0.8 | 0.238 | 450 | 0.22 | 135 | 101 | 0.748 | 0.224 | 34 | 65 | 0.206 |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | N1 | 1 | 0.8 | 0.238 | 450 | 0.131 | 379 | 343 | 0.905 | 0.762 | 36 | 23 | 0.324 |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | N4 | 4 | 0.8 | 0.238 | 450 | 0.129 | 416 | 377 | 0.906 | 0.838 | 39 | 19 | 0.559 |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | N8 | 8 | 0.8 | 0.238 | 450 | 0.104 | 420 | 395 | 0.94 | 0.878 | 25 | 22 | 0.733 |
| openai/gpt-5-nano | transfer (never queried during selection) | C0 |  | 0.8 | 0.143 | 450 | 0.14 | 214 | 174 | 0.813 | 0.387 | 40 | 23 | 0.097 |
| openai/gpt-5-nano | transfer (never queried during selection) | C_honest |  | 0.8 | 0.143 | 450 | 0.182 | 164 | 120 | 0.732 | 0.267 | 44 | 38 | 0.133 |
| openai/gpt-5-nano | transfer (never queried during selection) | N1 | 1 | 0.8 | 0.143 | 450 | 0.116 | 374 | 350 | 0.936 | 0.778 | 24 | 28 | 0.368 |
| openai/gpt-5-nano | transfer (never queried during selection) | N4 | 4 | 0.8 | 0.143 | 450 | 0.127 | 381 | 357 | 0.937 | 0.793 | 24 | 33 | 0.478 |
| openai/gpt-5-nano | transfer (never queried during selection) | N8 | 8 | 0.8 | 0.143 | 450 | 0.113 | 378 | 361 | 0.955 | 0.802 | 17 | 34 | 0.472 |

## 5. C0 accuracy beside Sampura's reported SafeAgent AI-alone numbers
Table 4 (Gemini 3 Flash, Sonnet 4.6) and Table 2 (Qwen3.5-9B) of arXiv 2610.24969. **Different models, different item sample, different split: not a like-for-like replication.**
| judge | role | n_test | n_groups | acc | ci_lo | ci_hi | auroc_self_consistency_agreement | ece_self_consistency_agreement | paper_gemini3flash | paper_sonnet46 | paper_qwen35_9b | paper_n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.7-flash | target (best-of-N selection runs against it) | 450 | 224 | 63.3 | 58.8 | 67.7 | 0.552 | 0.26 | 83.6 | 78.3 | 76.9 | 511 |
| openai/gpt-5-nano | transfer (never queried during selection) | 450 | 224 | 52.4 | 47.8 | 57.0 | 0.544 | 0.442 | 83.6 | 78.3 | 76.9 | 511 |

## 6. Selection strength (target-judge P(wrong label) of the chosen report)
| dataset | n | n_items | mean_selected_p_wrong | share_selected_p_wrong_1.0 |
| --- | --- | --- | --- | --- |
| safeagentbench | 1 | 450 | 0.851 | 0.771 |
| safeagentbench | 4 | 450 | 0.948 | 0.896 |
| safeagentbench | 8 | 450 | 0.965 | 0.929 |

`review/dev_rendered.md` renders all 21 development cases in every condition for label-validity review.
