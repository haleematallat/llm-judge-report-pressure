# Dev-batch summary (2026-10-30T17:49:55+0500)

Real run, 21 development items in 14 groups, 167.7s wall clock. Target judge `qwen/qwen3.7-flash`, transfer judge `openai/gpt-5-nano`, attacker `deepseek/deepseek-v4.1-flash`.

## Measured

| model | calls | fresh | cached | tok_in | tok_out | reasoning_tok | out_per_fresh_call | retry_share_of_judge_calls | cost_usd |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| deepseek/deepseek-v4.1-flash | 189 | 180 | 9 | 33124 | 23030 | 0 | 127.9 |  | 0.013 |
| openai/gpt-5-nano | 525 | 500 | 25 | 144365 | 14000 | 0 | 28.0 | 0.0 | 0.0128 |
| qwen/qwen3.7-flash | 1365 | 1300 | 65 | 435490 | 15756 | 0 | 12.1 | 0.0 | 0.0151 |

- Provider-reported cost this run: **$0.0409** ($0.00195 per item).
- Pilot spend so far: **$0.3229** of the $6.00 budget.
- Peak concurrently reserved: $0.0237 over 1980 reservations.
- Judge samples: 1050; unparseable (coded as refusals): 0 (0.0%); items with no usable answer at all: 0.
- Median completion tokens per fresh call: 12.

## Recomputed main-run cost

At $0.00195 per item, 81 held-out items project to **$0.1579**, or **$0.2053** with the 30% retry/concurrency headroom the amendment requires.

Remaining budget after the dev batch: $5.6771.
