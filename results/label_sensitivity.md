# Label sensitivity analysis

Driven by the **AI-assisted label audit** in `review/label_audit_items.md`. That audit may be completed with AI assistance and is not independent human validation of the benchmark's labels; nothing below should be reported as though it were.

Audit verdicts filled: 40 of 40. Flagged indefensible: 4. Marked unsure: 5.

Recomputes the preregistered primary contrast (N8 − N1) and the exploratory single-report contrast (N1 − C0) with the flagged items removed. **This is a robustness check, not a replacement.** The preregistered analysis is the one over all held-out items, reported in `results/tables.md`.

| judge | subset | contrast | exclusion | n_items | n_groups | error_rate_a | error_rate_b | delta_pp | ci_lo | ci_hi | p_group_boot |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.7-flash | all items | N8 - N1 | none (as preregistered) | 450 | 224 | 93.3 | 84.2 | 9.1 | 6.4 | 11.9 | 0.0001 |
| qwen/qwen3.7-flash | all items | N8 - N1 | indefensible excluded | 446 | 224 | 93.3 | 84.1 | 9.2 | 6.5 | 12.0 | 0.0001 |
| qwen/qwen3.7-flash | all items | N8 - N1 | indefensible and unsure excluded | 441 | 224 | 93.2 | 84.1 | 9.1 | 6.3 | 11.9 | 0.0001 |
| qwen/qwen3.7-flash | all items | N1 - C0 | none (as preregistered) | 450 | 224 | 84.2 | 36.7 | 47.6 | 43.0 | 52.2 | 0.0001 |
| qwen/qwen3.7-flash | all items | N1 - C0 | indefensible excluded | 446 | 224 | 84.1 | 36.3 | 47.8 | 43.1 | 52.4 | 0.0001 |
| qwen/qwen3.7-flash | all items | N1 - C0 | indefensible and unsure excluded | 441 | 224 | 84.1 | 36.1 | 48.1 | 43.3 | 52.8 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N8 - N1 | none (as preregistered) | 226 | 221 | 86.7 | 69.9 | 16.8 | 11.5 | 22.3 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N8 - N1 | indefensible excluded | 223 | 218 | 86.5 | 69.5 | 17.0 | 11.6 | 22.6 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N8 - N1 | indefensible and unsure excluded | 219 | 214 | 86.3 | 69.4 | 16.9 | 11.5 | 22.5 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N1 - C0 | none (as preregistered) | 226 | 221 | 69.9 | 42.0 | 27.9 | 21.1 | 34.8 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N1 - C0 | indefensible excluded | 223 | 218 | 69.5 | 41.7 | 27.8 | 21.0 | 34.8 | 0.0001 |
| qwen/qwen3.7-flash | benchmark-labelled unsafe only | N1 - C0 | indefensible and unsure excluded | 219 | 214 | 69.4 | 41.1 | 28.3 | 21.5 | 35.3 | 0.0001 |
| openai/gpt-5-nano | all items | N8 - N1 | none (as preregistered) | 450 | 224 | 84.0 | 83.1 | 0.9 | -1.5 | 3.3 | 0.5226 |
| openai/gpt-5-nano | all items | N8 - N1 | indefensible excluded | 446 | 224 | 83.9 | 83.0 | 0.9 | -1.5 | 3.4 | 0.5226 |
| openai/gpt-5-nano | all items | N8 - N1 | indefensible and unsure excluded | 441 | 224 | 83.7 | 83.0 | 0.7 | -1.7 | 3.0 | 0.6518 |
| openai/gpt-5-nano | all items | N1 - C0 | none (as preregistered) | 450 | 224 | 83.1 | 47.6 | 35.6 | 32.1 | 39.0 | 0.0001 |
| openai/gpt-5-nano | all items | N1 - C0 | indefensible excluded | 446 | 224 | 83.0 | 47.8 | 35.2 | 31.7 | 38.7 | 0.0001 |
| openai/gpt-5-nano | all items | N1 - C0 | indefensible and unsure excluded | 441 | 224 | 83.0 | 48.1 | 34.9 | 31.4 | 38.5 | 0.0001 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N8 - N1 | none (as preregistered) | 226 | 221 | 68.1 | 67.3 | 0.9 | -3.6 | 5.4 | 0.7746 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N8 - N1 | indefensible excluded | 223 | 218 | 67.7 | 66.8 | 0.9 | -3.6 | 5.5 | 0.7906 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N8 - N1 | indefensible and unsure excluded | 219 | 214 | 67.1 | 66.7 | 0.5 | -4.1 | 5.1 | 0.9208 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N1 - C0 | none (as preregistered) | 226 | 221 | 67.3 | 0.4 | 66.8 | 60.6 | 72.9 | 0.0001 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N1 - C0 | indefensible excluded | 223 | 218 | 66.8 | 0.4 | 66.4 | 59.9 | 72.6 | 0.0001 |
| openai/gpt-5-nano | benchmark-labelled unsafe only | N1 - C0 | indefensible and unsure excluded | 219 | 214 | 66.7 | 0.5 | 66.2 | 59.7 | 72.6 | 0.0001 |
