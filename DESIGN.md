# Design note

The solution has three separate parts: a deterministic generator, the
agent-facing environment, and the evaluator. `reset(seed)` builds one fictional
company and returns only public metadata. The agent sees records solely through
bounded `step()` actions; it cannot access the hidden reference or provenance.

The data includes four auditable error families: duplicate posting, missing
payment allocation, wrong FX-date conversion, and a reporting-period cut-off.
Correct look-alikes are preserved as decoys, so an agent needs evidence rather
than simply flagging repeated values.

Matching is one-to-one. A finding is correct only if its type, affected IDs,
amount, currency, and complete evidence set match an unused reference finding.
Duplicates and unsupported claims are false positives. Terminal reward uses F1
and a small per-step penalty, rewarding precise and efficient investigation.

Train and dev folders use different fixed seeds. They contain public data only;
the evaluator's `truth.json` and provenance remain private.
