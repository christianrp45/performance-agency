"""Testes do portão LICET, das regras de política e do executor (sem rede: LICET e Meta simulados)."""
import json
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from performance_agency import config, executor, licet_gate, proposals  # noqa: E402
from performance_agency.meta import MetaClient  # noqa: E402

HASH = "a" * 64


def make_cfg(tmp: Path, **over):
    (tmp / "agencia").mkdir(parents=True, exist_ok=True)
    data = {"name": "Teste", "ad_account_id": "111", "page_id": "222", "dry_run": True,
            "limits": {"max_daily_budget_cents": 2000, "max_increase_pct": 20}}
    data.update(over)
    (tmp / "agencia" / "config.json").write_text(json.dumps(data), encoding="utf-8")
    return config.load(tmp)


def ledger_for(cfg, p, **over):
    rec = {"id": 7, "timestamp": time.time(), "authorized": True, "trust_level": "L1",
           "agent_id": cfg.agent_id, "action": p.licet_action(), "target": p.licet_target(cfg),
           "intent_hash": HASH, "ui_binding_status": "VERIFIED", "revoked": False}
    rec.update(over)
    return lambda _cfg, _h: rec


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = make_cfg(self.tmp)
        self.p = proposals.create(self.cfg, "meta.adset.set_daily_budget",
                                  {"object_id": "333", "daily_budget_cents": 1800},
                                  "Orçamento 15 → 18", "teste", "voltar", 300, current_daily_cents=1500)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class GateTests(Base):
    def test_valid_authorization_passes(self):
        r = licet_gate.verify(self.cfg, self.p, HASH, fetch=ledger_for(self.cfg, self.p))
        self.assertTrue(r.ok, r.reasons)

    def test_each_mismatch_is_refused(self):
        cases = {
            "authorized": False, "revoked": True, "agent_id": "outro-agente",
            "target": "meta:act_111:999", "action": "PA-x | outra coisa", "ui_binding_status": "ABSENT",
            "intent_hash": "b" * 64, "timestamp": time.time() - 3 * 3600,
        }
        for field, bad in cases.items():
            with self.subTest(field=field):
                r = licet_gate.verify(self.cfg, self.p, HASH, fetch=ledger_for(self.cfg, self.p, **{field: bad}))
                self.assertFalse(r.ok)

    def test_not_found_and_network_error_refuse(self):
        self.assertFalse(licet_gate.verify(self.cfg, self.p, HASH, fetch=lambda c, h: {}).ok)

        def boom(c, h):
            raise OSError("sem rede")
        self.assertFalse(licet_gate.verify(self.cfg, self.p, HASH, fetch=boom).ok)

    def test_bad_hash_format_and_reuse(self):
        self.assertFalse(licet_gate.verify(self.cfg, self.p, "123", fetch=ledger_for(self.cfg, self.p)).ok)
        r = licet_gate.verify(self.cfg, self.p, HASH, used_hashes={HASH}, fetch=ledger_for(self.cfg, self.p))
        self.assertFalse(r.ok)


class PolicyTests(Base):
    def test_budget_cap_and_scale_rule(self):
        with self.assertRaises(proposals.PolicyError):  # acima do teto do cliente
            proposals.create(self.cfg, "meta.adset.set_daily_budget", {"object_id": "1", "daily_budget_cents": 2500},
                             "x", "x", "x", current_daily_cents=2000)
        with self.assertRaises(proposals.PolicyError):  # mais de 20% de uma vez
            proposals.create(self.cfg, "meta.adset.set_daily_budget", {"object_id": "1", "daily_budget_cents": 2000},
                             "x", "x", "x", current_daily_cents=1500)

    def test_unknown_operation_and_missing_ids(self):
        with self.assertRaises(proposals.PolicyError):
            proposals.create(self.cfg, "meta.object.delete", {"object_id": "1"}, "x", "x", "x")
        cfg2 = make_cfg(self.tmp / "c2", ad_account_id="")
        with self.assertRaises(proposals.PolicyError):
            proposals.create(cfg2, "meta.object.set_status", {"object_id": "1", "status": "PAUSED"}, "x", "x", "x")

    def test_tampered_proposal_file_is_rejected(self):
        path = self.cfg.proposals_dir / f"{self.p.id}.json"
        d = json.loads(path.read_text(encoding="utf-8"))
        d["params"]["daily_budget_cents"] = 2000
        path.write_text(json.dumps(d), encoding="utf-8")
        with self.assertRaises(proposals.PolicyError):
            proposals.load(self.cfg, self.p.id)


class ExecutorTests(Base):
    def test_cannot_execute_without_approval(self):
        with self.assertRaises(executor.ExecutionRefused):
            executor.execute(self.cfg, self.p.id, meta=MetaClient("", dry_run=True), fetch=ledger_for(self.cfg, self.p))

    def test_approve_then_dry_run_execute(self):
        fetch = ledger_for(self.cfg, self.p)
        executor.approve(self.cfg, self.p.id, HASH, fetch=fetch)
        p, result = executor.execute(self.cfg, self.p.id, meta=MetaClient("", dry_run=True), fetch=fetch)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["params"]["daily_budget"], "1800")
        self.assertNotIn("access_token", json.dumps(result))
        self.assertEqual(p.status, "aprovada")  # simulação não consome a aprovação

    def test_same_licet_hash_cannot_approve_two_proposals(self):
        executor.approve(self.cfg, self.p.id, HASH, fetch=ledger_for(self.cfg, self.p))
        p2 = proposals.create(self.cfg, "meta.object.set_status", {"object_id": "333", "status": "PAUSED"},
                              "Pausar 333", "x", "x")
        with self.assertRaises(executor.ExecutionRefused):
            executor.approve(self.cfg, p2.id, HASH, fetch=ledger_for(self.cfg, p2))

    def test_revoked_after_approval_blocks_execution(self):
        executor.approve(self.cfg, self.p.id, HASH, fetch=ledger_for(self.cfg, self.p))
        with self.assertRaises(executor.ExecutionRefused):
            executor.execute(self.cfg, self.p.id, meta=MetaClient("", dry_run=True),
                             fetch=ledger_for(self.cfg, self.p, revoked=True))

    def test_real_mode_needs_env_flag(self):
        cfg = make_cfg(self.tmp / "c3", dry_run=False)
        self.assertTrue(cfg.dry_run)  # sem AGENCY_DRY_RUN=0 continua simulando


if __name__ == "__main__":
    unittest.main()
