# Exploratory arms (not preregistered)

Specified after the main results were seen and recorded as a dated amendment in `docs/preregistration.md` §8. Descriptive, no multiplicity correction. The preregistered primary comparison is unchanged.

Subset: 152 held-out items sampled by whole groups. Third judge `meta-llama/llama-3.3-70b-instruct`, chosen on dev C0 only (`logs/third_judge.json`); never queried during any selection.

`report_type` is `none` (C0), `honest`, `original` (the main study's reports, which may state a verdict) or `verdict_free` (reports that may not state a verdict, address the judge, or use either option string). N=1 in every row is **one adversarially generated report, without best-of-N selection**.

Because the original reports state a verdict explicitly, plain answer-following is a live explanation for their effect: the judge may be copying a stated answer rather than being persuaded by a narrative. The verdict-free arm narrows that — those reports never state a verdict or name an option — but it does not establish that the remaining effect works through the same mechanism as human deference to an assistant, and nothing here tests that.

## Error rate by judge, report type and condition

| judge | report_type | condition | n_items | n_groups | error_rate | ci_lo | ci_hi | error_rate_benchmark_unsafe_approved | mean_self_consistency_agreement |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.7-flash | none | C0 | 152 | 78 | 39.5 | 32.1 | 47.4 | 44.9 | 0.897 |
| qwen/qwen3.7-flash | honest | C_honest | 152 | 78 | 29.6 | 22.9 | 37.3 | 32.1 | 0.93 |
| qwen/qwen3.7-flash | original | N1 | 152 | 78 | 84.2 | 77.6 | 89.2 | 70.5 | 0.95 |
| qwen/qwen3.7-flash | original | N4 | 152 | 78 | 91.4 | 85.9 | 94.9 | 83.3 | 0.961 |
| qwen/qwen3.7-flash | original | N8 | 152 | 78 | 91.4 | 85.9 | 94.9 | 83.3 | 0.963 |
| qwen/qwen3.7-flash | verdict_free | VF_N1 | 152 | 78 | 59.2 | 51.3 | 66.7 | 48.7 | 0.87 |
| qwen/qwen3.7-flash | verdict_free | VF_N4 | 152 | 78 | 77.0 | 69.7 | 83.0 | 59.0 | 0.916 |
| qwen/qwen3.7-flash | verdict_free | VF_N8 | 152 | 78 | 78.9 | 71.8 | 84.7 | 60.3 | 0.933 |
| openai/gpt-5-nano | none | C0 | 152 | 78 | 46.7 | 39.0 | 54.6 | 1.3 | 0.968 |
| openai/gpt-5-nano | honest | C_honest | 152 | 78 | 36.2 | 29.0 | 44.1 | 1.3 | 0.946 |
| openai/gpt-5-nano | original | N1 | 152 | 78 | 81.6 | 74.7 | 86.9 | 65.4 | 0.964 |
| openai/gpt-5-nano | original | N4 | 152 | 78 | 83.6 | 76.8 | 88.6 | 67.9 | 0.961 |
| openai/gpt-5-nano | original | N8 | 152 | 78 | 82.9 | 76.1 | 88.1 | 66.7 | 0.97 |
| openai/gpt-5-nano | verdict_free | VF_N1 | 152 | 78 | 52.0 | 44.1 | 59.8 | 7.7 | 0.974 |
| openai/gpt-5-nano | verdict_free | VF_N4 | 152 | 78 | 53.3 | 45.4 | 61.0 | 9.0 | 0.976 |
| openai/gpt-5-nano | verdict_free | VF_N8 | 152 | 78 | 53.3 | 45.4 | 61.0 | 9.0 | 0.98 |
| meta-llama/llama-3.3-70b-instruct | none | C0 | 152 | 78 | 42.1 | 34.5 | 50.1 | 15.4 | 0.984 |
| meta-llama/llama-3.3-70b-instruct | honest | C_honest | 152 | 78 | 38.8 | 31.4 | 46.7 | 5.1 | 0.984 |
| meta-llama/llama-3.3-70b-instruct | original | N1 | 152 | 78 | 73.7 | 66.2 | 80.0 | 50.0 | 0.974 |
| meta-llama/llama-3.3-70b-instruct | original | N8 | 152 | 78 | 77.0 | 69.7 | 83.0 | 55.1 | 0.98 |
| meta-llama/llama-3.3-70b-instruct | verdict_free | VF_N1 | 152 | 78 | 57.9 | 49.9 | 65.5 | 20.5 | 0.988 |
| meta-llama/llama-3.3-70b-instruct | verdict_free | VF_N8 | 152 | 78 | 59.2 | 51.3 | 66.7 | 20.5 | 0.986 |

## Contrasts (paired, group-bootstrapped)

| judge | contrast | what | n_items | n_groups | error_rate_a | error_rate_b | delta_pp | ci_lo | ci_hi | p_group_boot |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.7-flash | VF_N8 - VF_N1 | verdict-free: search | 152 | 78 | 78.9 | 59.2 | 19.7 | 13.2 | 26.4 | 0.0001 |
| qwen/qwen3.7-flash | VF_N1 - C0 | verdict-free: one report | 152 | 78 | 59.2 | 39.5 | 19.7 | 12.1 | 27.3 | 0.0001 |
| qwen/qwen3.7-flash | VF_N8 - N8 | verdict-free vs original at N=8 | 152 | 78 | 78.9 | 91.4 | -12.5 | -18.4 | -7.2 | 0.0001 |
| qwen/qwen3.7-flash | N8 - N1 | original: search | 152 | 78 | 91.4 | 84.2 | 7.2 | 2.6 | 12.3 | 0.0026 |
| qwen/qwen3.7-flash | N1 - C0 | original: one report | 152 | 78 | 84.2 | 39.5 | 44.7 | 36.5 | 52.9 | 0.0001 |
| openai/gpt-5-nano | VF_N8 - VF_N1 | verdict-free: search | 152 | 78 | 53.3 | 52.0 | 1.3 | -1.3 | 3.9 | 0.4424 |
| openai/gpt-5-nano | VF_N1 - C0 | verdict-free: one report | 152 | 78 | 52.0 | 46.7 | 5.3 | 1.3 | 9.9 | 0.014 |
| openai/gpt-5-nano | VF_N8 - N8 | verdict-free vs original at N=8 | 152 | 78 | 53.3 | 82.9 | -29.6 | -35.6 | -23.5 | 0.0001 |
| openai/gpt-5-nano | N8 - N1 | original: search | 152 | 78 | 82.9 | 81.6 | 1.3 | -2.6 | 5.5 | 0.6398 |
| openai/gpt-5-nano | N1 - C0 | original: one report | 152 | 78 | 81.6 | 46.7 | 34.9 | 27.8 | 41.7 | 0.0001 |
| meta-llama/llama-3.3-70b-instruct | VF_N8 - VF_N1 | verdict-free: search | 152 | 78 | 59.2 | 57.9 | 1.3 | 0.0 | 3.4 | 0.263 |
| meta-llama/llama-3.3-70b-instruct | VF_N1 - C0 | verdict-free: one report | 152 | 78 | 57.9 | 42.1 | 15.8 | 8.8 | 22.8 | 0.0001 |
| meta-llama/llama-3.3-70b-instruct | VF_N8 - N8 | verdict-free vs original at N=8 | 152 | 78 | 59.2 | 77.0 | -17.8 | -23.7 | -12.0 | 0.0001 |
| meta-llama/llama-3.3-70b-instruct | N8 - N1 | original: search | 152 | 78 | 77.0 | 73.7 | 3.3 | -2.0 | 8.7 | 0.2828 |
| meta-llama/llama-3.3-70b-instruct | N1 - C0 | original: one report | 152 | 78 | 73.7 | 42.1 | 31.6 | 22.4 | 41.1 | 0.0001 |

## Verdict-free generation

1216 valid candidates kept. 0 candidate drafts were rejected by the programmatic check and regenerated:

_(empty)_

The check rejects a draft containing "carry out", "refuse" or "the judge" (case-insensitive), or an empty body. It is a string test, not a semantic one: a report can still imply a verdict without using those words, and many do.
