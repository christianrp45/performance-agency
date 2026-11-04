"""Autorizar e executar propostas. Única porta de saída para a API da Meta.

Nada é autônomo: toda escrita precisa de autorização humana registrada.
  - libera_gasto  → só LICET (prova de autorização humana livre e consciente).
  - altera_conta  → LICET ou confirmação digitada "CONFIRMO <id>".
Antes de executar de verdade, o estado atual na Meta é conferido: se mudou desde a proposta,
a execução é recusada e o humano precisa ser consultado de novo.
"""
import time

from . import licet_gate, proposals
from .config import ClientConfig, load_secrets
from .meta import MetaClient, MetaError


class ExecutionRefused(RuntimeError):
    pass


def approve(cfg: ClientConfig, proposal_id: str, intent_hash: str, fetch=licet_gate.fetch_ledger_record,
            integrity=licet_gate.fetch_integrity):
    """Autorização pelo LICET (vale para qualquer nível de risco)."""
    p = proposals.load(cfg, proposal_id)
    if p.status != "aguardando_aprovacao":
        raise ExecutionRefused(f"{p.id} está '{p.status}', não aguarda aprovação.")
    res = licet_gate.verify(cfg, p, intent_hash, proposals.used_intent_hashes(cfg), fetch=fetch, integrity=integrity)
    if not res.ok:
        proposals.audit(cfg, "aprovacao_recusada", p.id, {"intent_hash": intent_hash, "motivos": res.reasons})
        raise ExecutionRefused("Aprovação recusada: " + " ".join(res.reasons))
    p.status = "aprovada"
    p.approval = {"method": "licet", "intent_hash": intent_hash.lower(), "ledger_id": res.record.get("id"),
                  "licet_timestamp": res.record.get("timestamp"), "trust_level": res.record.get("trust_level"),
                  "verified_at": time.time()}
    proposals.save(cfg, p)
    proposals.audit(cfg, "aprovada", p.id, {"method": "licet", "intent_hash": intent_hash.lower(),
                                            "ledger_id": res.record.get("id")})
    return p


def confirm(cfg: ClientConfig, proposal_id: str, phrase: str, who: str = ""):
    """Confirmação humana digitada — só para ações que NÃO liberam gasto."""
    p = proposals.load(cfg, proposal_id)
    if p.status != "aguardando_aprovacao":
        raise ExecutionRefused(f"{p.id} está '{p.status}', não aguarda aprovação.")
    if p.risk != proposals.RISK_CONFIRM:
        raise ExecutionRefused(f"{p.id} libera gasto: só pode ser autorizada pelo LICET.")
    if (phrase or "").strip() != f"CONFIRMO {p.id}":
        raise ExecutionRefused(f"Para confirmar, digite exatamente: CONFIRMO {p.id}")
    p.status = "aprovada"
    p.approval = {"method": "confirmacao", "by": who, "phrase": phrase.strip(), "confirmed_at": time.time()}
    proposals.save(cfg, p)
    proposals.audit(cfg, "aprovada", p.id, {"method": "confirmacao", "by": who})
    return p


def client_for(cfg: ClientConfig) -> MetaClient:
    s = load_secrets(cfg)
    return MetaClient(s.get("META_ACCESS_TOKEN", ""), cfg.meta_api_version, s.get("META_APP_SECRET", ""), cfg.dry_run)


def _check_authorization(cfg, p, fetch, integrity):
    method = p.approval.get("method") or ("licet" if p.approval.get("intent_hash") else "")
    if p.status != "aprovada" or not method:
        raise ExecutionRefused(f"{p.id} não tem autorização humana (status '{p.status}'). Nada executado.")
    if p.risk == proposals.RISK_LICET and method != "licet":
        raise ExecutionRefused(f"{p.id} libera gasto e só foi confirmada sem LICET. Autorize pelo LICET.")
    if method == "licet":  # reverifica no momento da execução: revogação, idade, integridade, nível
        res = licet_gate.verify(cfg, p, p.approval["intent_hash"], fetch=fetch, at_execution=True, integrity=integrity)
        if not res.ok:
            proposals.audit(cfg, "execucao_recusada", p.id, {"motivos": res.reasons})
            raise ExecutionRefused("Execução recusada na reverificação LICET: " + " ".join(res.reasons))
    elif time.time() - p.approval.get("confirmed_at", 0) > cfg.approval_max_age_minutes * 60:
        raise ExecutionRefused(f"Confirmação com mais de {cfg.approval_max_age_minutes} min: confirme de novo.")


def _check_live_state(meta: MetaClient, p):
    """Se a conta mudou desde a proposta, executar pode quebrar algo: recusa e pede nova consulta."""
    if meta.dry_run:
        return
    a = p.params
    if p.operation == "meta.adset.set_daily_budget":
        live = int(meta.get(a["object_id"], "daily_budget,effective_status").get("daily_budget") or 0)
        if a.get("from_daily_budget_cents") and live != int(a["from_daily_budget_cents"]):
            raise ExecutionRefused(f"O orçamento atual na Meta é {live/100:.2f}, não "
                                   f"{a['from_daily_budget_cents']/100:.2f} como na proposta. Crie uma nova proposta.")
    elif p.operation == "meta.object.set_status":
        live = meta.get(a["object_id"], "status,effective_status")
        if live.get("status") == a["status"]:
            raise ExecutionRefused(f"{a['object_id']} já está {a['status']} na Meta. Nada a fazer.")
        if live.get("status") not in ("ACTIVE", "PAUSED"):
            raise ExecutionRefused(f"{a['object_id']} está '{live.get('status')}' na Meta: situação inesperada, consulte.")


def execute(cfg: ClientConfig, proposal_id: str, meta: MetaClient = None, fetch=licet_gate.fetch_ledger_record,
            integrity=licet_gate.fetch_integrity):
    p = proposals.load(cfg, proposal_id)
    _check_authorization(cfg, p, fetch, integrity)
    proposals.check_policy(cfg, p.operation, p.params, p.params.get("from_daily_budget_cents", 0))

    meta = meta or client_for(cfg)
    a = p.params
    try:
        _check_live_state(meta, p)
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

    p.execution = {"at": time.time(), "dry_run": meta.dry_run, "result": result}
    # Simulação não consome a autorização: dá para repetir de verdade depois (com reverificação).
    p.status = "aprovada" if meta.dry_run else "executada"
    proposals.save(cfg, p)
    proposals.audit(cfg, "simulada" if meta.dry_run else "executada", p.id, {"result": result})
    return p, result
