"""Autorizar e executar propostas. Única porta de saída para a API da Meta.

Nada é autônomo: toda escrita precisa de autorização humana registrada.
  - libera_gasto  → LICET (prova de autorização humana livre e consciente); enquanto o LICET não estiver
                    ativo, o cliente pode escolher `spend_approval: "humano"` → "AUTORIZO GASTO <id>" + nome.
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
    """Autorização humana digitada.

    - Ações que NÃO liberam gasto: frase "CONFIRMO <id>".
    - Ações que liberam gasto: só se o cliente escolheu `spend_approval: "humano"` (enquanto o LICET não
      estiver ativo), com a frase "AUTORIZO GASTO <id>" e o nome de quem autoriza. Caso contrário, só LICET.
    """
    p = proposals.load(cfg, proposal_id)
    if p.status != "aguardando_aprovacao":
        raise ExecutionRefused(f"{p.id} está '{p.status}', não aguarda aprovação.")
    phrase = (phrase or "").strip()
    if p.risk == proposals.RISK_LICET:
        if cfg.spend_approval != "humano":
            raise ExecutionRefused(f"{p.id} libera gasto: só pode ser autorizada pelo LICET.")
        expected = f"AUTORIZO GASTO {p.id}"
        if not who.strip():
            raise ExecutionRefused("Informe o nome de quem autoriza o gasto.")
    else:
        expected = f"CONFIRMO {p.id}"
    if phrase != expected:
        raise ExecutionRefused(f"Para autorizar, digite exatamente: {expected}")
    p.status = "aprovada"
    p.approval = {"method": "confirmacao", "by": who.strip(), "phrase": phrase, "confirmed_at": time.time(),
                  "releases_spend": p.risk == proposals.RISK_LICET}
    proposals.save(cfg, p)
    proposals.audit(cfg, "aprovada", p.id, {"method": "confirmacao", "by": who.strip(),
                                            "releases_spend": p.risk == proposals.RISK_LICET})
    return p


def client_for(cfg: ClientConfig) -> MetaClient:
    s = load_secrets(cfg)
    return MetaClient(s.get("META_ACCESS_TOKEN", ""), cfg.meta_api_version, s.get("META_APP_SECRET", ""), cfg.dry_run)


def _check_authorization(cfg, p, fetch, integrity):
    method = p.approval.get("method") or ("licet" if p.approval.get("intent_hash") else "")
    if p.status != "aprovada" or not method:
        raise ExecutionRefused(f"{p.id} não tem autorização humana (status '{p.status}'). Nada executado.")
    if p.risk == proposals.RISK_LICET and method != "licet":
        human_ok = (cfg.spend_approval == "humano" and p.approval.get("by")
                    and p.approval.get("phrase") == f"AUTORIZO GASTO {p.id}")
        if not human_ok:
            raise ExecutionRefused(f"{p.id} libera gasto e não tem autorização válida para isso. Autorize pelo LICET.")
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
    elif p.operation == "meta.ads.create" and a.get("campaign_paused_expected"):
        live = meta.get(a["campaign_id"], "status,effective_status")
        if live.get("status") != "PAUSED":
            raise ExecutionRefused(f"A campanha {a['campaign_id']} não está pausada ({live.get('status')}): criar anúncios "
                                   "agora libera gasto. Faça uma proposta de anúncios com autorização de gasto.")
    elif p.operation == "meta.object.set_status":
        live = meta.get(a["object_id"], "status,effective_status")
        if live.get("status") == a["status"]:
            raise ExecutionRefused(f"{a['object_id']} já está {a['status']} na Meta. Nada a fazer.")
        if live.get("status") not in ("ACTIVE", "PAUSED"):
            raise ExecutionRefused(f"{a['object_id']} está '{live.get('status')}' na Meta: situação inesperada, consulte.")


def _create_ads(cfg: ClientConfig, meta: MetaClient, adset_id: str, ads: list) -> list:
    """Sobe a mídia e cria criativo + anúncio. Recusa se algum arquivo mudou depois da autorização."""
    for ad in ads:  # confere tudo antes de enviar qualquer coisa
        for key in ("file", "thumbnail"):
            if ad.get(key) and proposals.file_sha256(cfg.folder / ad[key]) != ad.get(f"{key}_sha256"):
                raise ExecutionRefused(f"O arquivo {ad[key]} mudou depois da autorização. Crie uma nova proposta.")
    created = []
    for ad in ads:
        if ad["type"] == "video":
            video_id = meta.upload_video(cfg.ad_account_id, cfg.folder / ad["file"], ad["name"])
            thumb = meta.upload_image(cfg.ad_account_id, cfg.folder / ad["thumbnail"])
            creative = meta.create_message_creative(cfg.ad_account_id, cfg.page_id, cfg.instagram_user_id, ad["name"],
                                                    ad["primary_text"], ad["headline"], ad.get("welcome_message", ""),
                                                    image_hash=thumb, video_id=video_id)
        else:
            img = meta.upload_image(cfg.ad_account_id, cfg.folder / ad["file"])
            creative = meta.create_message_creative(cfg.ad_account_id, cfg.page_id, cfg.instagram_user_id, ad["name"],
                                                    ad["primary_text"], ad["headline"], ad.get("welcome_message", ""),
                                                    image_hash=img)
        creative_id = creative.get("id", "<creative_id>")
        created.append({"name": ad["name"], "creative": creative,
                        "ad": meta.create_ad(cfg.ad_account_id, adset_id, ad["name"], creative_id)})
    return created


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
            if a.get("ads"):
                result["ads"] = _create_ads(cfg, meta, adset.get("id", "<adset_id>"), a["ads"])
        elif p.operation == "meta.ads.create":
            result = {"ads": _create_ads(cfg, meta, a["object_id"], a["ads"])}
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
