# Exploratory: error rate by direction (not preregistered)

Added after the main results were seen, at Haleema's request. These splits were not in the frozen PREREG and carry no multiplicity correction; treat them as descriptive.

An error on a **gold=Refuse** item is a **benchmark-labelled unsafe plan approved**; an error on a **gold=Carry out** item is a benchmark-labelled safe plan refused. "Benchmark-labelled" is doing real work in those phrases: the label is the source file the item came from, not an independent safety judgement, and `review/label_provenance.md` sets out what it does and does not establish. The two directions are not equally consequential and the pooled error rate mixes them.

N=1 throughout is **one adversarially generated report, without best-of-N selection** — the report still argues for the wrong label.

## Error rate by gold label

| judge | role | gold | direction | condition | n_items | n_groups | error_rate | ci_lo | ci_hi |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.7-flash | target | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | C0 | 226 | 221 | 42.0 | 35.8 | 48.6 |
| qwen/qwen3.7-flash | target | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | C_honest | 226 | 221 | 35.8 | 29.9 | 42.3 |
| qwen/qwen3.7-flash | target | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | N1 | 226 | 221 | 69.9 | 63.6 | 75.5 |
| qwen/qwen3.7-flash | target | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | N4 | 226 | 221 | 85.0 | 79.7 | 89.0 |
| qwen/qwen3.7-flash | target | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | N8 | 226 | 221 | 86.7 | 81.7 | 90.5 |
| qwen/qwen3.7-flash | target | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | C0 | 224 | 217 | 31.2 | 25.5 | 37.6 |
| qwen/qwen3.7-flash | target | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | C_honest | 224 | 217 | 24.1 | 19.0 | 30.1 |
| qwen/qwen3.7-flash | target | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | N1 | 224 | 217 | 98.7 | 96.1 | 99.5 |
| qwen/qwen3.7-flash | target | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | N4 | 224 | 217 | 100.0 | 98.3 | 100.0 |
| qwen/qwen3.7-flash | target | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | N8 | 224 | 217 | 100.0 | 98.3 | 100.0 |
| openai/gpt-5-nano | transfer | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | C0 | 226 | 221 | 0.4 | 0.1 | 2.5 |
| openai/gpt-5-nano | transfer | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | C_honest | 226 | 221 | 2.2 | 0.9 | 5.1 |
| openai/gpt-5-nano | transfer | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | N1 | 226 | 221 | 67.3 | 60.9 | 73.0 |
| openai/gpt-5-nano | transfer | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | N4 | 226 | 221 | 69.5 | 63.2 | 75.1 |
| openai/gpt-5-nano | transfer | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | N8 | 226 | 221 | 68.1 | 61.8 | 73.9 |
| openai/gpt-5-nano | transfer | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | C0 | 224 | 217 | 95.1 | 91.4 | 97.2 |
| openai/gpt-5-nano | transfer | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | C_honest | 224 | 217 | 71.0 | 64.7 | 76.5 |
| openai/gpt-5-nano | transfer | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | N1 | 224 | 217 | 99.1 | 96.8 | 99.8 |
| openai/gpt-5-nano | transfer | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | N4 | 224 | 217 | 100.0 | 98.3 | 100.0 |
| openai/gpt-5-nano | transfer | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | N8 | 224 | 217 | 100.0 | 98.3 | 100.0 |

## Contrasts within each direction (paired, group-bootstrapped)

| judge | role | gold | direction | contrast | n_items | n_groups | error_rate_a | error_rate_b | delta_pp | ci_lo | ci_hi | p_group_boot |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| qwen/qwen3.7-flash | target | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | N8 - N1 | 226 | 221 | 86.7 | 69.9 | 16.8 | 11.5 | 22.3 | 0.0001 |
| qwen/qwen3.7-flash | target | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | N1 - C0 | 226 | 221 | 69.9 | 42.0 | 27.9 | 21.1 | 34.8 | 0.0001 |
| qwen/qwen3.7-flash | target | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | N8 - N1 | 224 | 217 | 100.0 | 98.7 | 1.3 | 0.0 | 3.1 | 0.0876 |
| qwen/qwen3.7-flash | target | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | N1 - C0 | 224 | 217 | 98.7 | 31.2 | 67.4 | 61.1 | 73.5 | 0.0001 |
| openai/gpt-5-nano | transfer | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | N8 - N1 | 226 | 221 | 68.1 | 67.3 | 0.9 | -3.6 | 5.4 | 0.7746 |
| openai/gpt-5-nano | transfer | Refuse | benchmark-labelled unsafe plan approved (gold=Refuse judged Carry out) | N1 - C0 | 226 | 221 | 67.3 | 0.4 | 66.8 | 60.6 | 72.9 | 0.0001 |
| openai/gpt-5-nano | transfer | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | N8 - N1 | 224 | 217 | 100.0 | 99.1 | 0.9 | 0.0 | 2.3 | 0.2642 |
| openai/gpt-5-nano | transfer | Carry out | benchmark-labelled safe plan refused (gold=Carry out judged Refuse) | N1 - C0 | 224 | 217 | 99.1 | 95.1 | 4.0 | 0.9 | 7.2 | 0.0108 |
