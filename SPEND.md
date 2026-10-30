# Spend

| provider | cap | actual | notes |
| --- | --- | --- | --- |
| OpenRouter | $6.00 | **$0.0000** | No live call made: `OPENROUTER_API_KEY` is not set in this environment. `GET /api/v1/models` (free, no auth) was called once to collect prices. |
| Modal | $10.00 | **$0.0000** | No job submitted, including the ≤$1 smoke test authorised on 2026-10-30: the token in `~/.modal.toml` is rejected (`modal.exception.AuthError: Token not found`), so `modal app list` and an `App.lookup` both fail before any GPU is allocated. Modal GPU-hour estimates for a scaled run are in `SCALING.md`. |
| **total** | | **$0.0000** | |

## Cost estimate under amendment 1 (printed, not spent)

`python -m pilot_a.run --estimate --split dev|test`, prices from
`results/openrouter_prices.csv` (fetched 2026-10-30). SafeAgentBench only, target judge
+ one transfer judge, 8 candidates, N in {1, 4, 8}, K = 5 selection + 5 fresh evaluation
samples.

| run | items | calls | tokens in | tokens out | USD | +30% headroom |
| --- | --- | --- | --- | --- | --- | --- |
| dev batch | 21 | 2,079 | 950,976 | 132,300 | 0.0780 | 0.1014 |
| main run | 81 | 8,019 | 3,692,151 | 510,300 | 0.3018 | 0.3924 |
| **both** | 102 | 10,098 | 4,643,127 | 642,600 | **0.3798** | **0.4938** |

Per model, for both runs combined: `qwen/qwen3.7-flash` 6,630 calls / $0.1310;
`deepseek/deepseek-v4.1-flash` 918 calls / $0.1462; `openai/gpt-5-nano` 2,550 calls /
$0.1027.

Both runs together are about 8% of the $6.00 cap.

## Spend guard (amendment 1, fix 6)

`pilot_a.providers.Spend` **reserves** each call's maximum possible cost before dispatch
and releases the unused part on settlement, so the cap bounds committed spend, not
merely settled spend: a plain check-then-send lets N concurrent calls each pass a check
none of them has paid for yet. The reservation uses a pessimistic token estimate
(`chars / 3.2 + 64` input, `max_tokens` output). `run.py` additionally refuses to start
when prior key usage plus this run's estimate already exceeds the cap, and records
`peak_reserved` in the run metadata. One JSON line per call is appended to
`logs/spend_ledger.jsonl` with the reserved and the settled amount. No key is printed,
logged or written to disk.

---

## Superseded: estimate for the original three-dataset plan

## Cost estimate for the live run (printed, not spent)

`python -m pilot_a.run --estimate --items-per-dataset 85`, prices read from
`results/openrouter_prices.csv` (fetched 2026-10-30), upper bound, retries excluded:

| model | role | calls | tokens in | tokens out | USD |
| --- | --- | --- | --- | --- | --- |
| `qwen/qwen3.7-flash` | J_dev + M4 judge + M5 proposer | 40,035 | 35,664,924 | 2,065,500 | 1.338 |
| `deepseek/deepseek-v4.1-flash` | attacker | 4,335 | 2,477,274 | 1,300,500 | 0.762 |
| `google/gemini-2.5-flash-lite` | held-out + M4 critic + M5 picker | 19,635 | 18,612,426 | 981,750 | 2.254 |
| `meta-llama/llama-3.3-70b-instruct` | held-out | 8,925 | 7,648,830 | 357,000 | 0.879 |
| `openai/gpt-5-nano` | held-out | 8,925 | 7,648,830 | 357,000 | 0.525 |
| **total** | | **81,855** | | | **5.758** |

At the plan's full 100 items per dataset (300 items) the same estimate is **$6.788**,
over the $6.00 cap. Per the plan's shrink order (items, then held-out judges, then K),
the live configuration is **85 items per dataset = 255 items, 3 held-out judges, K = 5**,
estimated **$5.758**. The offline dry run reported in `README.md` uses the full 300
items because it costs nothing.

## Spend guard

`pilot_a/providers.Spend` reads total key usage from `GET /api/v1/key` before the run,
checks `usage + spent + next_estimate <= cap` before every paid call, raises
`SpendCapReached` otherwise, and appends one JSON line per paid call to
`logs/spend_ledger.jsonl`. No key is ever printed or logged.
