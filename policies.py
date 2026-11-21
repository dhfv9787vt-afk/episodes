"""Four transparent baseline-policy adapters."""
def random_explorer(env):
    for table in ("ledger", "invoices", "payments", "fx"):
        env.step({"type":"list_records", "table":table, "limit":50})
    return []

def row_sweep(env):
    cursor = 0
    while cursor is not None:
        result, *_ = env.step({"type":"list_records", "table":"ledger", "cursor":cursor, "limit":50})
        cursor = result.get("next_cursor")
    return []

def conservative_duplicate(env):
    result, *_ = env.step({"type":"list_records", "table":"ledger", "limit":50})
    groups = {}
    for row in result.get("records", []):
        if row.get("invoice_id") and row["debit_minor"]:
            groups.setdefault((row["invoice_id"], row["account"], row["debit_minor"], row["currency"]), []).append(row)
    findings = []
    for (_, _, amount, currency), rows in groups.items():
        if len(rows) == 2:
            ids = sorted(r["row_id"] for r in rows)
            findings.append({"type":"duplicate_invoice", "affected_ids":ids, "claimed_amount_minor":amount, "currency":currency, "evidence_ids":ids, "explanation":"Same invoice, account, and debit amount."})
    return findings

def cautious_documents(env):
    env.step({"type":"list_records", "table":"invoices", "limit":50})
    env.step({"type":"list_records", "table":"payments", "limit":50})
    return []

BASELINES = {"random_explorer": random_explorer, "row_sweep": row_sweep, "conservative_duplicate": conservative_duplicate, "cautious_documents": cautious_documents}
