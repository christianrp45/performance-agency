"""Aprovar (com prova LICET) e executar propostas. Única porta de saída para a API da Meta."""
import time

from . import licet_gate, proposals
from .config import ClientConfig, load_secrets
from .meta import MetaClient, MetaError


class ExecutionRefused(RuntimeError):
    pass


def approve(cfg: ClientConfig, proposal_id: str, intent_hash: str, fetch=licet_gate.fetch_ledger_record):
    p = proposals.load(cfg, proposal_id)
    if p.status != "aguardando_aprovacao":
        raise ExecutionRefused(f"{p.id} está '{p.status}', não aguarda aprovação.")
    res = licet_gate.verify(cfg, p, intent_hash, proposals.used_intent_hashes(cfg), fetch=fetch)
    if not res.ok:
        proposals.audit(cfg, "aprovacao_recusada", p.id, {"intent_hash": intent_hash, "motivos": res.reasons})
        raise ExecutionRefused("Aprovação recusada: " + " ".join(res.reasons))
    p.status = "aprovada"
    p.approval = {"intent_hash": intent_hash.lower(), "ledger_id": res.record.get("id"),
                  "licet_timestamp": res.record.get("timestamp"), "trust_level": res.record.get("trust_level"),
                  "verified_at": time.time()}
    proposals.save(cfg, p)
    proposals.audit(cfg, "aprovada", p.id, {"intent_hash": intent_hash.lower(), "ledger_id": res.record.get("id")})
    return p


def client_for(cfg: ClientConfig) -> MetaClient:
    s = load_secrets(cfg)
    return MetaClient(s.get("META_ACCESS_TOKEN", ""), cfg.meta_api_version, s.get("META_APP_SECRET", ""), cfg.dry_run)


def execute(cfg: ClientConfig, proposal_id: str, meta: MetaClient = None, fetch=licet_gate.fetch_ledger_record):
    p = proposals.load(cfg, proposal_id)
    if p.status != "aprovada" or not p.approval.get("intent_hash"):
        raise ExecutionRefused(f"{p.id} não tem aprovação LICET (status '{p.status}'). Nada executado.")
    # Reverifica no momento da execução: pega revogação e autorização velha.
    res = licet_gate.verify(cfg, p, p.approval["intent_hash"], fetch=fetch, at_execution=True)
    if not res.ok:
        proposals.audit(cfg, "execucao_recusada", p.id, {"motivos": res.reasons})
        raise ExecutionRefused("Execução recusada na reverificação LICET: " + " ".join(res.reasons))
    proposals.check_policy(cfg, p.operation, p.params)

    meta = meta or client_for(cfg)
    a = p.params
    try:
        if p.operation == "meta.launch.create_paused":
            camp = meta.create_campaign_paused(cfg.ad_account_id, a["campaign_name"], a.get("objective", "OUTCOME_ENGAGEMENT"))
            camp_id = camp.get("id", "<campaign_id>")
            adset = meta.create_adset(cfg.ad_account_id, camp_id, a["adset_name"], cfg.page_id,
                                      a["daily_budget_cents"], a["targeting"], status="ACTIVE",
                                      destination_type=a.get("destination_type", "MESSAGING_INSTAGRAM_DIRECT_MESSENGER_WHATSAPP"))
            result = {"campaign": camp, "adset": adset}
        elif p.operation == "meta.adset.set_daily_budget":
            result = meta.set_daily_budget(a["object_id"], a["daily_budget_cents"])
        elif p.operation == "meta.object.set_status":
            result = meta.set_status(a["object_id"], a["status"])
        else:
            raise ExecutionRefused(f"Operação sem executor: {p.operation}")
    except MetaError as e:
        p.status = "falhou"
        p.execution = {"at": time.time(), "erro": str(e), "dry_run": meta.dry_run}
        proposals.save(cfg, p)
        proposals.audit(cfg, "falhou", p.id, {"erro": str(e)})
        raise

    p.status = "simulada" if meta.dry_run else "executada"
    p.execution = {"at": time.time(), "dry_run": meta.dry_run, "result": result}
    if meta.dry_run:  # simulação não consome a aprovação: dá para repetir de verdade depois
        p.status = "aprovada"
    proposals.save(cfg, p)
    proposals.audit(cfg, "simulada" if meta.dry_run else "executada", p.id, {"result": result})
    return p, result
