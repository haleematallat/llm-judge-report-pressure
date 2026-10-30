# Data sources

Downloaded 2026-10-30 into `data/raw/<source>/` (git-ignored). Read with `python -I`;
no code from any download is executed.

| dataset | source | revision | licence | files |
| --- | --- | --- | --- | --- |
| SafeAgentBench | https://github.com/shengyin1224/SafeAgentBench | `38ca3ab27eb8a5f5034a50bdcc5cbab23ce8f089` | MIT (stated in README.md; no LICENSE file in the repo) | `dataset/safe_detailed_1009.jsonl`, `dataset/unsafe_detailed_1009.jsonl`, `dataset/long_horizon_1009.jsonl`, `dataset/abstract_1009.jsonl` |
| BBEH (BBEH-Safety subset) | https://github.com/google-deepmind/bbeh | `80d12ca916b7158f22293fcf3144f4d3d854d4be` | Apache-2.0 (LICENSE in repo) | `bbeh/benchmark_tasks/bbeh_{web_of_lies,causal_understanding,sarc_triples,nycc,disambiguation_qa}/task.json` |
| Liar's Bench | https://huggingface.co/datasets/ventura1900/liarsbenchneurips (ungated mirror of `Cadenza-Labs/liars-bench`) | `cad75614e425ee35fd46b5f410d3d7be31f63dc5` | CC BY 4.0 for author-created data (upstream README + LICENSE; some subsets carry third-party terms) | `insider-trading/test-*.parquet`, `harm-pressure-knowledge-report/test-*.parquet` |

## Notes

- **Liar's Bench upstream is gated.** `Cadenza-Labs/liars-bench` (revision
  `503399b81aff28d6812b0ea4585607d5e4b7d3c4`) returns HTTP 401 ("Access to dataset
  ... is restricted") on both `/resolve/` and the parquet API, and no Hugging Face
  token is available in this environment. The ungated mirror above was used instead.
  Row counts differ from the upstream card's reported counts (insider-trading
  6,709 vs 6,873; harm-pressure-knowledge-report 9,227 vs 7,068), so the mirror is
  not a copy of the current upstream revision. Upstream paper: arXiv:2511.16035.
- SafeAgentBench `abstract_1009.jsonl` is downloaded but unused: Sampura dropped
  SafeAgentBench-Abstracted for overlapping with SafeAgentBench (their Appendix C).
  `long_horizon_1009.jsonl` is unused because those items carry no hazard label.
- `safe_detailed_1009.jsonl` also contains a `risk_instruction` field (an unsafe
  variant of the same instruction). Only `instruction` is used, so no item appears
  in both hazard strata.
- Benchmark canary strings in the Liar's Bench and BBEH files are preserved in
  `data/raw/` and are not copied into `data/items.jsonl`.
