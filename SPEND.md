# Spend

| provider | cap | actual | notes |
| --- | --- | --- | --- |
| OpenRouter | $6.00 above baseline | see **Measured spend** below | Baseline key usage $7.774466788, recorded once in `logs/pilot_baseline.json`. |
| Modal | $10.00 | **$0.0000** | No job submitted, including the ≤$1 smoke test authorised on 2026-10-30: the token in `~/.modal.toml` is rejected (`modal.exception.AuthError: Token not found`), so `modal app list` and an `App.lookup` both fail before any GPU is allocated. Modal GPU-hour estimates for a scaled run are in `SCALING.md`. |
| **total** | | **$0.0000** | |

## Measured spend

| stage | items | wall clock | cost | note |
| --- | --- | --- | --- | --- |
| smoke test, 1 item | 1 | 387s | $0.0069 | discarded: reasoning config broken |
| dev batch, first attempt | 21 | 553s | $0.2618 | **discarded**: 69–78% of samples unparseable, 62% retries |
| smoke test after the fix | 1 | 11s | $0.0021 | kept |
| **dev batch, kept** | **21** | **168s** | **$0.0409** | 0% unparseable, 0% retries |
| **main run** | **450** | **1310s** | **$0.9247** | 0% unparseable, 4,500 judge rows |
| reasoning-on check | 60 | 109s | $0.0681 | secondary, PREREG §7; 55% unparseable by design |
| third-judge pick (dev C0) | 21 | 60s | $0.0164 | exploratory; 2 candidate models |
| exploratory arms | 152 | 1180s | $0.3881 | exploratory; verdict-free + third judge |
| **sum of per-call costs** | | | **$1.8944** | what the API reported call by call |
| **key-usage delta** | | | **$2.0091** | $7.7745 baseline -> $9.7836, the authoritative figure |

The two totals differ by $0.1147. The per-call sum counts only calls this pilot's code
logged a `usage` block for; the key delta counts everything billed to the key since the
baseline, including calls whose response carried no usage, any provider-side rounding,
and any spend by Pilot B, which shares this key. **The key delta is the figure the caps
are enforced against**, and it is the one to quote: $2.0091 of the $6.00 pilot budget
and of the $9.00 combined cap, leaving $3.99 and $6.99 respectively.

The discarded $0.2818 is counted against the budget: the guard tracks key usage, not
usable data. See README §9.2 for what went wrong and what it cost in validity.

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

## How the $6.00 cap is measured (baseline + budget)

The OpenRouter key is shared and already carried **$7.7745** of lifetime usage from
earlier work before this pilot made its first call. A guard capping *total key usage*
at $6.00 would therefore refuse every call. Haleema's intent is $6.00 of **new** spend
for Pilot A, so the guard is baseline-relative:

- The key's usage is read once, immediately before this pilot's first paid call, and
  written to `logs/pilot_baseline.json` (`baseline_usage = 7.774466788`, recorded
  2026-10-30T17:27:07+05:00).
- Every later run reads that file rather than re-reading the key, so restarting a run
  cannot extend the budget by moving the baseline forward.
- The enforced cap is `baseline + $6.00`. The dev batch and the main run draw on one
  shared $6.00 pilot budget, not $6.00 each.

**Combined cap.** Pilot B runs against the same key with its own $3.00 budget, so a
second, independent guard requires total key usage to stay at or below
`baseline + $9.00`. That one catches the other pilot's spend, which this process can
neither see nor reserve. Both guards are checked before a run starts and the run
aborts rather than partially executing.

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
