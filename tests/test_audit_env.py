import unittest
from audit_env import FinancialAuditEnv

class AuditEnvironmentTests(unittest.TestCase):
    def setUp(self): self.env=FinancialAuditEnv(); self.obs,_=self.env.reset(seed=19)
    def test_reproducible_public_episode(self):
        a=self.env.step({"type":"list_records","table":"ledger","limit":50})[0]
        b=FinancialAuditEnv(); b.reset(seed=19); self.assertEqual(a,b.step({"type":"list_records","table":"ledger","limit":50})[0])
    def test_observations_do_not_leak_secrets(self):
        text=str(self.obs)+str(self.env.step({"type":"list_records","table":"ledger"})[0]); self.assertNotIn("iss_dup",text); self.assertNotIn("provenance",text)
    def test_perfect_evidence_scores_high_and_duplicate_does_not(self):
        fs=[{"type":t["type"],"affected_ids":t["affected_ids"],"claimed_amount_minor":t["expected_amount_minor"],"currency":t["currency"],"evidence_ids":t["allowed_evidence_sets"][0]} for t in self.env.episode.truth]
        _,score,*_=self.env.step({"type":"submit","findings":fs}); self.assertGreater(score,.9)
        self.env.reset(seed=19); _,score,*_=self.env.step({"type":"submit","findings":fs+fs}); self.assertLess(score,.9)
    def test_limits_and_invalid_action(self):
        out,*_=self.env.step({"type":"list_records","table":"ledger","limit":999}); self.assertLessEqual(len(out["records"]),50)
        out,*_=self.env.step({"type":"nope"}); self.assertIn("error",out)
    def test_calculator_blocks_code(self):
        out,*_=self.env.step({"type":"calculator","expression":"__import__('os')"}); self.assertIn("error",out)

if __name__ == "__main__": unittest.main()
