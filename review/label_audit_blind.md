# AI-assisted label audit

This audit is split across two files so they can be shared separately.

- **[`label_audit_items.md`](label_audit_items.md)** — the 40 items, the reference labels and the blank `label_defensible` column. Fill this one. It contains no dataset metadata.
- **[`label_audit_reasons.md`](label_audit_reasons.md)** — the dataset's `risk_category` and the other fields withheld from the judge, keyed by the same opaque audit ids. Read after deciding, as corroboration only.

`label_audit_key.json` maps the opaque ids back to item ids and is only needed by the sensitivity analysis.

The audit may be completed with AI assistance, so it is described throughout as an **AI-assisted label audit**. It is not independent human validation of the benchmark's labels, and no result should be reported as though it were.

When the column in `label_audit_items.md` is filled:

```bash
python -m pilot_a.label_audit --analyse
```
