# Financial Audit RL Environment

Reproducible, dependency-free Python 3.9+ environment for the Genesis FINTech case.

```bash
cd /Users/admin/Desktop/fin_audit_hackathon
python3 verify.py
```

`FinancialAuditEnv.reset(seed, config)` returns public task metadata only.  The
hidden reference is retained by the evaluator and is never included in an
observation or trajectory.  `step(action)` follows the Gymnasium-style
`(observation, reward, terminated, truncated, info)` contract.

## Actions

- `list_records`: `{type, table, cursor?, limit?}` where table is `ledger`,
  `invoices`, `payments`, or `fx`.
- `get_record`: `{type, table, id}`.
- `get_document`: `{type, doc_id}` for invoice/payment documents.
- `calculator`: `{type, expression}`; arithmetic decimal expressions only.
- `submit`: `{type: "submit", findings: [...]}`; ends the episode.

Maximum page size is 50, maximum episode length is 100 actions, and at most 30
findings may be submitted.  `findings` use `type`, `affected_ids`,
`claimed_amount_minor`, `currency`, `evidence_ids`, and `explanation`.

## Files and isolation

Each generated episode contains public `manifest.json`, `ledger.csv`,
`invoices.jsonl`, `payments.jsonl`, `fx.csv`, and `policy.json`; internally it
also has `truth.json` and `provenance.json`. Only the public material is ever
returned by actions.  The generator produces four configurable error types:
duplicate invoice, missing allocation, FX/date mismatch, and wrong-period
posting. It also emits clean cases and legal, repeat-like decoys. Two seeds add
interacting errors (cross-currency partial payment near the boundary).

## Reproducibility and scoring

The seed determines every identifier, ordering, amount and error. Matching is
one-to-one; repeated or unsupported findings are false positives. F1 is
`2TP/(2TP+FP+FN)` and terminal reward is
`clip(2*F1 - 1 - 0.002*inspection_steps, -1, 1)`.

`demo.py` runs a small deterministic scripted policy and writes a public-only
trajectory to `trajectories.jsonl`.

## Submission files

- `LICENSE` - MIT license.
- `requirements.txt` - fixed dependency statement (standard library only).
- `episodes/train` and `episodes/dev` - 10 public episodes each.
- `policies.py` - four baseline-policy adapters.
- `DESIGN.md` - short design note.
- `tests/`, `trajectories.jsonl`, and `demo.py` - verification and demo.

Record the requested demo video by running `python3 verify.py`, then using
macOS `Shift-Command-5` to record the terminal while it reports success.
