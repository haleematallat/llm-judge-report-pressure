# Scaling Pilot A onto Modal

Answers the 2026-10-30 plan update: cost both the planned run and a hackathon-sized
run with almost all inference on Modal vLLM and open-weight models, and list the
public Sampura-suite datasets that could be added.

Regenerate every number here with `python -m pilot_a.modal_estimate`.

## 0. Stop state

No real run happened. Phase 0, the dry run, the tests and the cost estimate are done;
Phases 1–5 have not been run on either provider. Spend is $0.00 / $0.00.

**The ≤$1 Modal smoke test could not run.** `~/.modal.toml` is present and well-formed
(profile `haleematallat`, `active = true`) but its token is rejected:
`modal app list` and `modal.App.lookup` both return
`modal.exception.AuthError: Token not found`, before any container is created. A new
token (`modal token new`) would unblock `modal run modal_app.py`, which is written and
parses. That smoke test is what would replace the throughput assumptions below with
measurements.

## 1. Modal prices used

Read from modal.com/pricing on 2026-10-30. The page quotes per-second; per-hour is
×3600.

| GPU | $/sec (as published) | $/hour |
| --- | --- | --- |
| B300 | 0.001972 | 7.0992 |
| B200 | 0.001736 | 6.2496 |
| H200 SXM | 0.001261 | 4.5396 |
| H100 SXM5 | 0.001097 | 3.9492 |
| RTX PRO 6000 | 0.000842 | 3.0312 |
| A100 80 GB | 0.000694 | 2.4984 |
| A100 40 GB | 0.000583 | 2.0988 |
| L40S | 0.000542 | 1.9512 |
| A10 | 0.000306 | 1.1016 |
| L4 | 0.000222 | 0.7992 |
| T4 | 0.000164 | 0.5904 |

CPU $0.0000131/core/s ($0.0472/core/h), memory $0.00000222/GiB/s ($0.0080/GiB/h);
both are rounding error next to GPU time here. Modal lists an "A10", not an A10G.

### Which GPU

This workload is prefill-dominated: judge prompts average ~900–1,100 tokens and
replies are ~40, so >95% of the token bill is input. That makes raw bf16 FLOP/$ the
right thing to optimise, and H100 wins:

| GPU | 9B prefill tok/s (40% MFU) | $/h | M tokens per $ |
| --- | --- | --- | --- |
| H100 | 22,000 | 3.95 | **20.1** |
| H200 | 22,000 | 4.54 | 17.4 |
| L40S | 8,044 | 1.95 | 14.8 |
| L4 | 2,689 | 0.80 | 12.1 |
| A100 80 GB | 6,933 | 2.50 | 10.0 |

H200 only helps when VRAM, not FLOPs, is the constraint (a 70B at bf16). L4 is the
right choice only for a cheap smoke test.

## 2. Throughput model — an assumption, not a measurement

Because the smoke test could not run, GPU-hours come from a transparent analytic
model rather than from a benchmark. All of it is in
`pilot_a/modal_estimate.py`, as four constants to replace once measurements exist:

- prefill: 2 FLOP per parameter per token at **40% MFU** of the GPU's peak dense bf16
  throughput;
- decode: **12% of prefill** throughput (memory-bound, heavily batched; it moves the
  total by <5% either way because decode is <5% of tokens);
- tensor parallel: **80%** scaling across GPUs inside one container;
- **+5 minutes** container start per model per run (weights pull + vLLM warm-up).

Worked: 9B on 1×H100 → 22,000 prefill tok/s; 70B FP8 on 2×H100 → 4,526 prefill tok/s.
**Treat every dollar figure below as ±2×** until the smoke test lands. If real MFU is
25% rather than 40%, every total rises by 1.6×.

## 3. Models

All verified present on Hugging Face (HTTP 200) on 2026-10-30. Llama and Gemma are
acceptance-gated on HF: a token whose account has accepted those licences is needed
to pull weights, which is a second credential to sort out alongside Modal's.

| role | model | params | GPU | VRAM at that precision |
| --- | --- | --- | --- | --- |
| J_dev (selection target) | `Qwen/Qwen3.5-9B` | 9B | 1×H100 | 18 GB bf16 |
| held out (Meta) | `meta-llama/Llama-3.1-8B-Instruct` | 8B | 1×H100 | 16 GB bf16 |
| held out (Mistral) | `mistralai/Mistral-Small-24B-Instruct-2501` | 24B | 1×H100 | 48 GB bf16 |
| held out (Google) | `google/gemma-3-12b-it` | 12B | 1×H100 | 24 GB bf16 |
| held out, large | `meta-llama/Llama-3.3-70B-Instruct` | 70B | **2×H100, FP8 W8A8** | ~70 GB + KV |
| generations arm | `Qwen/Qwen2.5-7B-Instruct`, `Qwen/Qwen3-8B`, `Qwen/Qwen3.5-9B` | 7–9B | 1×H100 | — |

**The 70B and its quantization.** bf16 is 140 GB, so it needs 2×H100 (160 GB) with
little room for KV cache, or 4×H100 to be comfortable. FP8 W8A8 halves weights to
~70 GB, which fits one H100 only with a very small KV budget; **2×H100 with FP8 and
`tensor_parallel_size=2`** is the configuration costed here — it leaves ~90 GB for KV
cache, which matters because Liar's Bench insider-trading transcripts are long. FP8
is native on Hopper in vLLM, so it costs no accuracy-free lunch but does change the
judge slightly; that belongs in the limitations if it ships.
`Qwen/Qwen2.5-72B-Instruct` is an equivalent substitute and is not acceptance-gated.

## 4. Estimates

Call accounting matches exactly what `pilot_a.run` issues: 16 candidate reports + 1
honest control per item from the attacker; 16×K J_dev calls to score candidates; K
calls per judge per condition across 7 conditions (C0, C_honest, N∈{1,2,4,8,16});
plus M4's critique + judge and M5's propose + pick. K=5 throughout.

### 4a. Planned version (plan Phases 1–4, 300 items, 4 judges, no 70B)

| model | GPU | calls | tokens in | GPU-h | $ |
| --- | --- | --- | --- | --- | --- |
| `Qwen/Qwen3.5-9B` | 1×H100 | 47,100 | 43,168,853 | 0.88 | 3.49 |
| `meta-llama/Llama-3.1-8B-Instruct` | 1×H100 | 23,100 | 22,499,533 | 0.44 | 1.75 |
| `mistralai/Mistral-Small-24B-Instruct-2501` | 1×H100 | 10,500 | 9,272,515 | 0.51 | 2.03 |
| `google/gemma-3-12b-it` | 1×H100 | 10,500 | 9,272,515 | 0.30 | 1.18 |
| `Qwen/Qwen3-8B` (attacker) | 1×H100 | 5,100 | 2,973,793 | 0.26 | 1.03 |
| **total** | | **96,300** | | **2.40** | **9.48** |

$9.48 against the plan's $10 Modal cap: it fits, with no margin for a retry or a
slower-than-assumed MFU. **For the planned version the OpenRouter route is cheaper
and safer at $5.758**; Modal is the right choice only from §4b onward.

### 4b. Scaled, balanced — the recommended hackathon configuration

3,520 items (≤2,000 per dataset, stratified), 5 judges including the 70B, 24B
attacker, generations arm (Qwen2.5-7B, Qwen3-8B, Qwen3.5-9B).

| model | GPU | calls | tokens in | GPU-h | $ |
| --- | --- | --- | --- | --- | --- |
| `Qwen/Qwen3.5-9B` | 1×H100 | 552,640 | 619,784,191 | 10.91 | 43.08 |
| `meta-llama/Llama-3.1-8B-Instruct` | 1×H100 | 271,040 | 319,547,151 | 4.94 | 19.50 |
| `mistralai/Mistral-Small-24B-Instruct-2501` (also attacker) | 1×H100 | 183,040 | 181,206,076 | 12.60 | 49.78 |
| `google/gemma-3-12b-it` | 1×H100 | 123,200 | 134,048,705 | 3.03 | 11.97 |
| `meta-llama/Llama-3.3-70B-Instruct` | 2×H100 FP8 | 123,200 | 134,048,705 | 21.66 | 85.55 |
| `Qwen/Qwen2.5-7B-Instruct` (generations) | 1×H100 | 123,200 | 134,048,705 | 1.80 | 7.12 |
| `Qwen/Qwen3-8B` (generations) | 1×H100 | 123,200 | 134,048,705 | 2.05 | 8.09 |
| **total** | | **1,499,520** | | **57.00** | **225.09** |

Making the 70B the attacker as well costs **$294.31 / 74.52 GPU-h** instead — $69
more for reports written by a larger model. Keeping the 70B as a judge only is the
better trade: it is the judge-side scaling question that the project is about.

### 4c. Scaled, full public pools

Every converted item in the three pools: 17,456 items (SafeAgentBench 600,
Liar's Bench 15,936, BBEH-Safety 920).

| model | GPU | calls | tokens in | GPU-h | $ |
| --- | --- | --- | --- | --- | --- |
| `Qwen/Qwen3.5-9B` | 1×H100 | 2,740,592 | 3,461,059,308 | 58.66 | 231.66 |
| `meta-llama/Llama-3.1-8B-Instruct` | 1×H100 | 1,344,112 | 1,774,707,788 | 26.29 | 103.81 |
| `mistralai/Mistral-Small-24B-Instruct-2501` | 1×H100 | 610,960 | 751,143,540 | 32.23 | 127.29 |
| `google/gemma-3-12b-it` | 1×H100 | 610,960 | 751,143,540 | 16.16 | 63.81 |
| `meta-llama/Llama-3.3-70B-Instruct` (also attacker) | 2×H100 FP8 | 907,712 | 1,026,959,088 | 242.30 | 956.89 |
| `Qwen/Qwen2.5-7B-Instruct` | 1×H100 | 610,960 | 751,143,540 | 9.46 | 37.36 |
| `Qwen/Qwen3-8B` | 1×H100 | 610,960 | 751,143,540 | 10.80 | 42.65 |
| **total** | | **7,436,256** | | **395.90** | **1,563.47** |

**91% of those items are Liar's Bench**, almost all of them variants of one
insider-trading scenario family, so the extra $1,338 over §4b buys mostly repeated
structure in one dataset. §4b is the better spend; if more Liar's Bench is wanted,
raise its cap from 2,000 rather than taking the whole pool.

### What the totals do not include

- Weight downloads beyond the first run: a `modal.Volume` HF cache makes these free
  after the first pull. The +5 min/model start is included.
- Retries and the 3-attempt JSON parse loop: on the dry run 3% of replies need a
  retry, so add ~3% to judge calls.
- Idle container time between stages. Running one model at a time with
  `scaledown_window` short keeps this near zero; running all seven concurrently is
  faster in wall-clock but risks paying for idle GPUs.
- Caching already in the pipeline: every call is keyed by
  (model, prompt hash, sample index, temperature), so a resumed or partially
  re-run job pays only for what is new.

## 5. Public Sampura-suite datasets that could be added

The suite is 8 datasets; this pilot uses 3. Checked 2026-10-30.

| dataset | status | where | licence | verdict |
| --- | --- | --- | --- | --- |
| **CulturalBench** | **public, ungated** | HF `kellycyy/CulturalBench`, rev `996d62a…`, `CulturalBench-Easy.csv` + `CulturalBench-Hard.csv` | CC BY 4.0 | **Add it.** 1,227 items in the paper, held out entirely there, which makes it a clean generalisation check. Factual single-turn, so the "end-of-task report" framing is weaker than for the agentic sets — the report becomes an assertion about an answer rather than a narration of behaviour. |
| **AttuneBench** | **partly public** | GitHub `Thoughtful-Lab/attunebench`, rev `37c429a…`, `Test Samples/Sample200/conversation_*.json` | CC BY 4.0 (`LICENSE-DATA`) for the conversation data | **Add with care.** The public sample is 200 conversations with one assistant response per turn plus annotations; it has no pairwise response pairs and no participant preference labels, so Sampura's 800-item pairwise adaptation cannot be rebuilt from it. A different pairwise item could be constructed, but it would not be their items and would not be comparable to their numbers. |
| **SHADE-Arena** | **partly public** | GitHub `safety-research/SHADE-Arena` (MIT); the paper (arXiv:2506.15740) releases 5 of 17 task pairs, full set on request | MIT for the released code/tasks | **Add the public 5/17.** Agentic and deception-flavoured, the closest in spirit to the pressure setting, and held out entirely in the paper. Carries a canary string; keep it out of any training data. Worth emailing the authors for the full set if the project continues. |
| **FACTS Search** | **public behind a Kaggle account** | Kaggle, Google DeepMind / Google Research, `FACTS Search` (V2, with V1 archived); paper arXiv:2512.10791 | Kaggle dataset terms | **Possible, low priority.** Needs a Kaggle API token, and Sampura's own Qwen3.5-9B scored 7.9% on it (their Table 2) — a floor that low leaves almost no headroom to lose under pressure, so it would measure parsing more than persuasion. |
| **Difference Awareness** | **inferred, not confirmed** | HF org `Complementarity`: `multidimensional-difference-awareness-legacy` and `difference-awareness-version-flip`, MIT, clinical + legal items | MIT | **Check before using.** The content matches the paper's description ("constructed from institutional legislation and medical sources, following Wang et al. 2025"), but the paper names no release and I could not confirm the org is Sampura's. Only 120 items in their suite (58 in test), so it adds little power either way. |
| **Liar's Bench (remaining 6 subsets)** | public via the same mirror | `alpaca`, `convincing-game`, `gender-secret`, `harm-pressure-choice`, `instructed-deception`, `soft-trigger` | CC BY 4.0 upstream | **Cheap diversity.** ~57k further items. Adding two or three subsets is a better use of the deception budget than more insider-trading. |

Adding CulturalBench + SHADE-Arena public + two more Liar's Bench subsets would take
the suite from 3 to 5 of the paper's 8 datasets at roughly the §4b cost, since the
item cap, not the number of datasets, sets the bill.

## 6. What to decide

1. A fresh Modal token, so the ≤$1 smoke test can replace §2's assumptions.
2. A Hugging Face token on an account that has accepted the Llama and Gemma licences,
   or swap both for ungated substitutes (`Qwen/Qwen2.5-72B-Instruct`,
   `Qwen/Qwen3-8B`) and drop the Meta/Google families from the cross-family claim.
3. Items per dataset (the cap that sets the bill) and whether to add CulturalBench
   and the SHADE-Arena public subset.
