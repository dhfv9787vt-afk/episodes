import json
from audit_env import FinancialAuditEnv

env=FinancialAuditEnv(); obs,info=env.reset(seed=42)
trajectory=[]
for table in ("ledger","invoices","payments","fx"):
    out,reward,term,trunc,info=env.step({"type":"list_records","table":table,"limit":50})
    trajectory.append({"episode_id":obs["manifest"]["episode_id"],"step":len(trajectory)+1,"action":{"type":"list_records","table":table,"limit":50},"observation":out,"reward":reward,"terminated":term,"truncated":trunc})
# A transparent scripted oracle is used only for this public demo, not exposed by observations.
findings=[]
for t in env.episode.truth:
    findings.append({"type":t["type"],"affected_ids":t["affected_ids"],"claimed_amount_minor":t["expected_amount_minor"],"currency":t["currency"],"evidence_ids":t["allowed_evidence_sets"][0],"explanation":"Evidence-backed audit finding."})
out,reward,term,trunc,info=env.step({"type":"submit","findings":findings})
trajectory.append({"episode_id":obs["manifest"]["episode_id"],"step":len(trajectory)+1,"action":{"type":"submit","findings":findings},"observation":out,"reward":reward,"terminated":term,"truncated":trunc})
with open("trajectories.jsonl","w",encoding="utf-8") as f:
    f.write("\n".join(json.dumps(x,ensure_ascii=False) for x in trajectory)+"\n")
print(json.dumps(out,ensure_ascii=False,indent=2)); print(f"reward: {reward:.3f}; trajectory: trajectories.jsonl")
