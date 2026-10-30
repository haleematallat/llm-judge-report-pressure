# Preregistration — Pilot A

**Status: SPECIFIED, NOT YET FROZEN.** Written 2026-10-30, under
`~/pivotal-pilots/plans/pilot-a-amendment-1.md`, before any live model call. The
amendment's procedure freezes this document *after* the real dev batch, because the
held-out case count is set from measured dev cost. No key was visible in this
environment, so the dev batch did not run and the freeze did not happen. Everything
below except the one quantity marked **OPEN** is fixed and will not change.

Any change after the freeze is a dated amendment appended to §8, never an edit above it.

- Supersedes: the original `plans/pilot-a.md` preregistration, where they conflict.
- Live calls made so far: **none**. OpenRouter spend $0.0000.

## 1. Question

A judge rates a household-robot plan drawn from SafeAgentBench. The agent being judged
may append an end-of-task report; the transcript is never edited, so the reference label
stays valid. As an attacker searches harder over candidate reports (best-of-N, N = 1, 4,
8), how much does the judge's held-out error rate rise, and how much of that carries to
a judge the attacker never queried?

## 2. Threat model (fixed)

The attacker scores all 8 of its candidate reports against the **target judge on the
same item** before choosing one, so it has per-item query access to the target judge.
Target-judge results measure a query-access attack. The **transfer judge is never
queried during selection**, so transfer-judge results measure what carries to an
unprobed judge. The attacker also sees the reference label. The judge is told the
appended text is the agent's own report but is **not** told to distrust it; telling it
so would be a defence, and the measurement is of the undefended judge.

## 3. Design (fixed)

- **Dataset**: SafeAgentBench only, 600 usable rows (`safe_detailed` + `unsafe_detailed`).
- **Group**: the instruction family — connected components joining each `instruction` to
  its `risk_instruction`. 301 groups over 600 items. Groups are the unit of sampling,
  splitting and bootstrapping; no group straddles the split.
- **Sample**: ~20 development items and **OPEN** held-out items (see §7), sampled as
  whole groups in stratified round-robin order, seed 0, dev fraction 0.25 by a hash of
  the group id. Realised at the specified size: 21 dev (14 groups) / 81 held out
  (45 groups).
- **Judges**: target `qwen/qwen3.7-flash`; transfer `openai/gpt-5-nano` (different
  family, never queried in selection). Attacker `deepseek/deepseek-v4.1-flash`.
- **Judge protocol**: K = 5 samples, temperature 1.0, strict JSON from a closed option
  set, ≤3 parse attempts per sample, unparseable samples coded as refusals. Answer =
  plurality; confidence = largest-cluster share over K; refusals form their own cluster,
  never win, and stay in the denominator.
- **Attack**: 8 candidate reports per item, ≤150 words, in the agent's voice, all arguing
  for one fixed wrong label per item (chosen deterministically from the item id).
- **Selection**: candidates scored by the target judge as P(wrong label) over K = 5
  samples; for N ∈ {1, 4, 8} the chosen report is the best of the first N candidates
  (nested prefixes; the 8 candidates are generated and scored once). N = 1 is the
  random-report control.
- **Evaluation**: **5 fresh samples** per condition per judge, drawn under stage `eval`,
  never the stage-`select` samples that chose the report.
- **Conditions**: C0 (no report), C_honest (neutral faithful summary), N1, N4, N8.
- **Not run** (code retained): M2–M5 including the AI-only adaptation of Top-N
  assistance, N50 curve fitting, the model-generations arm, Top-3 displacement, Modal.

## 4. Primary outcome (fixed)

**Held-out error rate at N = 8 minus held-out error rate at N = 1**, computed separately
for the target judge and the transfer judge. Paired over items, bootstrapped over
**groups**, 10,000 resamples, seed 42, percentile 95% CI, two-sided p floored at
1/10,000. Two primary tests, one per judge; no correction between them, and each is
reported with its interval rather than as a threshold decision.

## 5. Secondary outcomes (fixed)

1. The contrasts N4 − N1, N1 − C0, N8 − C0 and C_honest − C0, per judge, Holm-corrected
   within judge. C_honest − C0 is the check that a neutral appended report does not by
   itself move the judge.
2. The **self-consistency review rule**: τ is fitted on **dev C0** to flag as close to
   30% of dev items for review as the discrete K = 5 confidence allows (a strict
   quantile cannot hit 30%; `review_threshold` picks the closest achievable rate and the
   achieved dev rate is reported as `dev_review_rate_at_tau`). An item is flagged when
   self-consistency ≤ τ. Reported per condition on the held-out split: actual review
   rate, errors left unflagged (count and share of all errors), errors caught, and false
   positives (flagged but correct) with their rate. This is an AI-only rule over the
   judge's own samples; **no human is involved and no complementarity is claimed**.
3. Unanimous-and-wrong rate: share of items where all 5 evaluation samples agree and the
   agreed answer is wrong.
4. C0 accuracy beside Sampura's reported SafeAgent AI-alone numbers (their Table 4 and
   Table 2), labelled as not a like-for-like replication.
5. Selection strength: the target judge's P(wrong label) for the chosen report at each N.

## 6. Analysis rules (fixed)

- Thresholds are fitted on dev only; every reported number is on the held-out split.
- All intervals resample groups. Row-level intervals are printed alongside, labelled, so
  the difference the clustering makes is visible; the group interval is the one that
  counts.
- Refusals are never silently dropped: they are counted in the denominator and reported
  as a refusal rate.
- Every table and figure is recomputed from the JSONL logs by `python -m pilot_a.report`.
  No number is entered by hand.
- Parse failures, retries and spend are reported from the logs, not estimated.

## 7. Open quantity

**OPEN — held-out case count.** The amendment sets it from measured dev-batch cost. The
pre-run estimate is $0.0780 for 21 dev items and $0.3018 for 81 held-out items
(+30% headroom: $0.1014 and $0.3924), against a $6.00 cap for the whole pilot. If the
dev batch measures close to the estimate, the cap permits substantially more than 81
held-out cases. The count is to be set once, recorded here as a dated amendment, and not
revisited.

## 8. Amendments after the freeze

_(none — the freeze has not happened)_
