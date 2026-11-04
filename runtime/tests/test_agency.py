"""Testes do portão LICET, do risco por operação, das regras de política e do executor.

Sem rede: LICET (registro e integridade) e Meta são simulados.
"""
import json
import os
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
INTACT = lambda _cfg: {"status": "INTACT", "tampered": False, "records": 10}  # noqa: E731


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


class FakeMeta(MetaClient):
    """Meta em 'modo real' sem rede: registra chamadas e devolve estado configurável."""

    def __init__(self, live=None):
        super().__init__("token-de-teste", dry_run=False)
        self.live = live or {}
        self.calls = []

    def _call(self, method, path, params):
        self.calls.append((method, path, params))
        if method == "GET":
            return self.live.get(path, {})
        return {"id": "999", "success": True}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.cfg = make_cfg(self.tmp)
        self.p = proposals.create(self.cfg, "meta.adset.set_daily_budget",
                                  {"object_id": "333", "daily_budget_cents": 1800, "from_daily_budget_cents": 1500},
                                  "Orçamento 15 → 18", "teste", "voltar", 300, current_daily_cents=1500)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        os.environ.pop("AGENCY_DRY_RUN", None)

    def real_cfg(self, name="real"):
        os.environ["AGENCY_DRY_RUN"] = "0"
        return make_cfg(self.tmp / name, dry_run=False)


class GateTests(Base):
    def verify(self, **over):
        return licet_gate.verify(self.cfg, self.p, HASH, fetch=ledger_for(self.cfg, self.p, **over), integrity=INTACT)

    def test_valid_authorization_passes(self):
        r = self.verify()
        self.assertTrue(r.ok, r.reasons)

    def test_each_mismatch_is_refused(self):
        cases = {
            "authorized": False, "revoked": True, "agent_id": "outro-agente",
            "target": "meta:act_111:999", "action": "PA-x | outra coisa", "ui_binding_status": "ABSENT",
            "intent_hash": "b" * 64, "timestamp": time.time() - 3 * 3600,
        }
        for field, bad in cases.items():
            with self.subTest(field=field):
                self.assertFalse(self.verify(**{field: bad}).ok)

    def test_not_found_and_network_error_refuse(self):
        self.assertFalse(licet_gate.verify(self.cfg, self.p, HASH, fetch=lambda c, h: {}, integrity=INTACT).ok)

        def boom(*a):
            raise OSError("sem rede")
        self.assertFalse(licet_gate.verify(self.cfg, self.p, HASH, fetch=boom, integrity=INTACT).ok)

    def test_bad_hash_format_and_reuse(self):
        self.assertFalse(licet_gate.verify(self.cfg, self.p, "123", fetch=ledger_for(self.cfg, self.p), integrity=INTACT).ok)
        r = licet_gate.verify(self.cfg, self.p, HASH, used_hashes={HASH}, fetch=ledger_for(self.cfg, self.p), integrity=INTACT)
        self.assertFalse(r.ok)

    def test_tampered_or_unreachable_ledger_refuses(self):
        tampered = lambda c: {"status": "TAMPERED", "tampered": True, "tampered_at_id": 1}  # noqa: E731
        r = licet_gate.verify(self.cfg, self.p, HASH, fetch=ledger_for(self.cfg, self.p), integrity=tampered)
        self.assertFalse(r.ok)
        self.assertIn("não está íntegro", r.reasons[0])

        def boom(c):
            raise OSError("sem rede")
        self.assertFalse(licet_gate.verify(self.cfg, self.p, HASH, fetch=ledger_for(self.cfg, self.p), integrity=boom).ok)

    def test_trust_level_l0_only_in_simulation(self):
        self.assertTrue(self.verify(trust_level="L0").ok)  # simulação aceita simulador
        cfg = self.real_cfg()
        p = proposals.create(cfg, "meta.object.set_status", {"object_id": "1", "status": "ACTIVE"}, "Ativar 1", "x", "x")
        r = licet_gate.verify(cfg, p, HASH, fetch=ledger_for(cfg, p, trust_level="L0"), integrity=INTACT)
        self.assertFalse(r.ok)
        self.assertTrue(licet_gate.verify(cfg, p, HASH, fetch=ledger_for(cfg, p, trust_level="L1"), integrity=INTACT).ok)


class RiskTests(Base):
    def risk(self, op, params):
        return proposals.assess(op, params)[0]

    def test_classification(self):
        L, C = proposals.RISK_LICET, proposals.RISK_CONFIRM
        self.assertEqual(self.risk("meta.object.set_status", {"status": "ACTIVE"}), L)
        self.assertEqual(self.risk("meta.object.set_status", {"status": "PAUSED"}), C)
        self.assertEqual(self.risk("meta.adset.set_daily_budget", {"daily_budget_cents": 1800, "from_daily_budget_cents": 1500}), L)
        self.assertEqual(self.risk("meta.adset.set_daily_budget", {"daily_budget_cents": 1200, "from_daily_budget_cents": 1500}), C)
        self.assertEqual(self.risk("meta.adset.set_daily_budget", {"daily_budget_cents": 1200}), L)  # sem saber o atual
        self.assertEqual(self.risk("meta.launch.create_paused", {"daily_budget_cents": 1500}), C)

    def test_risk_in_file_is_never_trusted(self):
        path = self.cfg.proposals_dir / f"{self.p.id}.json"
        d = json.loads(path.read_text(encoding="utf-8"))
        d["risk"] = proposals.RISK_CONFIRM  # tentativa de rebaixar o risco no arquivo
        path.write_text(json.dumps(d), encoding="utf-8")
        self.assertEqual(proposals.load(self.cfg, self.p.id).risk, proposals.RISK_LICET)


class PolicyTests(Base):
    def test_budget_cap_and_scale_rule(self):
        with self.assertRaises(proposals.PolicyError):
            proposals.create(self.cfg, "meta.adset.set_daily_budget", {"object_id": "1", "daily_budget_cents": 2500},
                             "x", "x", "x", current_daily_cents=2000)
        with self.assertRaises(proposals.PolicyError):
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
    def test_cannot_execute_without_authorization(self):
        with self.assertRaises(executor.ExecutionRefused):
            executor.execute(self.cfg, self.p.id, meta=MetaClient("", dry_run=True),
                             fetch=ledger_for(self.cfg, self.p), integrity=INTACT)

    def test_licet_approve_then_dry_run_execute(self):
        fetch = ledger_for(self.cfg, self.p)
        executor.approve(self.cfg, self.p.id, HASH, fetch=fetch, integrity=INTACT)
        p, result = executor.execute(self.cfg, self.p.id, meta=MetaClient("", dry_run=True), fetch=fetch, integrity=INTACT)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["params"]["daily_budget"], "1800")
        self.assertNotIn("access_token", json.dumps(result))
        self.assertEqual(p.status, "aprovada")

    def test_same_licet_hash_cannot_approve_two_proposals(self):
        executor.approve(self.cfg, self.p.id, HASH, fetch=ledger_for(self.cfg, self.p), integrity=INTACT)
        p2 = proposals.create(self.cfg, "meta.object.set_status", {"object_id": "333", "status": "PAUSED"},
                              "Pausar 333", "x", "x")
        with self.assertRaises(executor.ExecutionRefused):
            executor.approve(self.cfg, p2.id, HASH, fetch=ledger_for(self.cfg, p2), integrity=INTACT)

    def test_revoked_or_tampered_after_approval_blocks_execution(self):
        executor.approve(self.cfg, self.p.id, HASH, fetch=ledger_for(self.cfg, self.p), integrity=INTACT)
        with self.assertRaises(executor.ExecutionRefused):
            executor.execute(self.cfg, self.p.id, meta=MetaClient("", dry_run=True),
                             fetch=ledger_for(self.cfg, self.p, revoked=True), integrity=INTACT)
        with self.assertRaises(executor.ExecutionRefused):
            executor.execute(self.cfg, self.p.id, meta=MetaClient("", dry_run=True), fetch=ledger_for(self.cfg, self.p),
                             integrity=lambda c: {"status": "TAMPERED", "tampered": True})

    def test_confirmation_only_for_actions_that_do_not_release_spend(self):
        with self.assertRaises(executor.ExecutionRefused):  # aumento de gasto: confirmação não serve
            executor.confirm(self.cfg, self.p.id, f"CONFIRMO {self.p.id}", "Ana")
        pause = proposals.create(self.cfg, "meta.object.set_status", {"object_id": "333", "status": "PAUSED"},
                                 "Pausar 333", "custo alto", "reativar")
        with self.assertRaises(executor.ExecutionRefused):  # frase errada
            executor.confirm(self.cfg, pause.id, "confirmo", "Ana")
        executor.confirm(self.cfg, pause.id, f"CONFIRMO {pause.id}", "Ana")
        p, result = executor.execute(self.cfg, pause.id, meta=MetaClient("", dry_run=True), integrity=INTACT)
        self.assertEqual(result["params"]["status"], "PAUSED")

    def test_live_state_changed_requires_new_consultation(self):
        cfg = self.real_cfg()
        p = proposals.create(cfg, "meta.adset.set_daily_budget",
                             {"object_id": "333", "daily_budget_cents": 1200, "from_daily_budget_cents": 1500},
                             "Reduzir 15 → 12", "x", "x", current_daily_cents=1500)
        executor.confirm(cfg, p.id, f"CONFIRMO {p.id}", "Ana")
        meta = FakeMeta(live={"333": {"daily_budget": "1700"}})  # alguém mudou na Meta depois da proposta
        with self.assertRaises(executor.ExecutionRefused):
            executor.execute(cfg, p.id, meta=meta, integrity=INTACT)
        self.assertFalse([c for c in meta.calls if c[0] == "POST"])  # nada foi escrito

    def test_live_state_unchanged_executes_in_real_mode(self):
        cfg = self.real_cfg("real2")
        p = proposals.create(cfg, "meta.object.set_status", {"object_id": "444", "status": "PAUSED"},
                             "Pausar 444", "x", "x")
        executor.confirm(cfg, p.id, f"CONFIRMO {p.id}", "Ana")
        meta = FakeMeta(live={"444": {"status": "ACTIVE"}})
        p, _ = executor.execute(cfg, p.id, meta=meta, integrity=INTACT)
        self.assertEqual(p.status, "executada")
        self.assertIn(("POST", "444", {"status": "PAUSED"}), [(m, path, prm) for m, path, prm in meta.calls])

    def test_real_mode_needs_env_flag(self):
        cfg = make_cfg(self.tmp / "c3", dry_run=False)
        self.assertTrue(cfg.dry_run)


class HumanSpendApprovalTests(Base):
    """Enquanto o LICET não está ativo, o cliente pode escolher autorização humana digitada para gasto."""

    def test_default_still_requires_licet_for_spend(self):
        with self.assertRaises(executor.ExecutionRefused):
            executor.confirm(self.cfg, self.p.id, f"AUTORIZO GASTO {self.p.id}", "Christian")

    def test_human_mode_needs_exact_phrase_and_name(self):
        cfg = make_cfg(self.tmp / "h1", spend_approval="humano")
        p = proposals.create(cfg, "meta.object.set_status", {"object_id": "1", "status": "ACTIVE"}, "Ativar 1", "x", "x")
        with self.assertRaises(executor.ExecutionRefused):
            executor.confirm(cfg, p.id, f"CONFIRMO {p.id}", "Christian")  # frase de ação sem gasto não serve
        with self.assertRaises(executor.ExecutionRefused):
            executor.confirm(cfg, p.id, f"AUTORIZO GASTO {p.id}", "  ")  # sem nome
        executor.confirm(cfg, p.id, f"AUTORIZO GASTO {p.id}", "Christian")
        _, result = executor.execute(cfg, p.id, meta=MetaClient("", dry_run=True), integrity=INTACT)
        self.assertEqual(result["params"]["status"], "ACTIVE")

    def test_switching_back_to_licet_invalidates_typed_spend_approval(self):
        cfg = make_cfg(self.tmp / "h2", spend_approval="humano")
        p = proposals.create(cfg, "meta.object.set_status", {"object_id": "1", "status": "ACTIVE"}, "Ativar 1", "x", "x")
        executor.confirm(cfg, p.id, f"AUTORIZO GASTO {p.id}", "Christian")
        cfg_licet = make_cfg(self.tmp / "h2", spend_approval="licet")
        with self.assertRaises(executor.ExecutionRefused):
            executor.execute(cfg_licet, p.id, meta=MetaClient("", dry_run=True), integrity=INTACT)

    def test_invalid_mode_rejected(self):
        with self.assertRaises(ValueError):
            make_cfg(self.tmp / "h3", spend_approval="automatico")


class ReportTests(Base):
    def test_report_from_api_flags_ads(self):
        from performance_agency import report
        meta = FakeMeta()
        meta.insights = lambda *a, **k: {"data": [
            {"ad_name": "A1 video", "adset_name": "DAL", "spend": "70", "frequency": "1.4",
             "actions": [{"action_type": "onsite_conversion.messaging_conversation_started_7d", "value": "0"}]},
            {"ad_name": "A3 imagem", "adset_name": "DAL", "spend": "40", "frequency": "3.1",
             "actions": [{"action_type": "onsite_conversion.messaging_conversation_started_7d", "value": "4"}]},
        ]}
        text = report.from_api(self.cfg, meta)
        self.assertIn("gastou 3× o alvo sem conversa", text)
        self.assertIn("frequência alta", text)
        self.assertIn("$110.00 gastos", text)

    def test_report_without_csv_says_missing(self):
        from performance_agency import report
        path = report.write(self.cfg)
        self.assertIn("MISSING", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
