# Spend

| provider | cap | actual | notes |
| --- | --- | --- | --- |
| OpenRouter | $6.00 | **$0.0000** | No live call made: `OPENROUTER_API_KEY` is not set in this environment. `GET /api/v1/models` (free, no auth) was called once to collect prices. |
| Modal | $10.00 | **$0.0000** | No job submitted: the token in `~/.modal.toml` is rejected (`modal.exception.AuthError: Token not found`), so `modal app list` and an `App.lookup` both fail before any GPU is allocated. |
| **total** | | **$0.0000** | |

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
