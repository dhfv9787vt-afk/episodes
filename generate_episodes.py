"""Generate 10 public train and 10 public dev episodes from fixed seeds."""
from pathlib import Path
from audit_env import FinancialAuditEnv

def write_episode(seed, split):
    env = FinancialAuditEnv(); env.reset(seed=seed)
    files = env.export_episode()
    destination = Path("episodes") / split / f"episode_{seed:03d}"
    destination.mkdir(parents=True, exist_ok=True)
    names = {"manifest":"manifest.json", "policy":"policy.json", "ledger.csv":"ledger.csv", "fx.csv":"fx.csv", "invoices.jsonl":"invoices.jsonl", "payments.jsonl":"payments.jsonl"}
    for source, target in names.items():
        (destination / target).write_text(files[source], encoding="utf-8")

for seed in range(100, 110): write_episode(seed, "train")
for seed in range(200, 210): write_episode(seed, "dev")
print("Generated 10 train and 10 dev public episodes.")
