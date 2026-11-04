"""Propostas: toda ação de escrita nasce como proposta e só anda com autorização humana.

Nível de risco (decide QUEM/COMO autoriza — nada é autônomo):
  libera_gasto  → aumenta ou libera gasto (ativar, subir orçamento): exige LICET (prova fisiológica).
  altera_conta  → muda a conta sem liberar gasto (pausar, reduzir orçamento, lançar pausado): exige
                  autorização humana explícita — LICET ou confirmação digitada "CONFIRMO <id>".

Ciclo: aguardando_aprovacao → aprovada → executada | falhou
                            ↘ rejeitada | expirada
"""
import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .config import ClientConfig

# Operações permitidas (lista fechada). Qualquer outra é recusada.
OPERATIONS = {
    "meta.launch.create_paused": "criar campanha PAUSADA com o conjunto de anúncios (não gasta nada até ser ativada)",
    "meta.adset.set_daily_budget": "mudar orçamento diário do conjunto",
    "meta.object.set_status": "pausar ou ativar campanha/conjunto/anúncio",
    "meta.ads.create": "criar anúncios (imagem/vídeo) num conjunto existente",
}
MONEY_OPERATIONS = {"meta.adset.set_daily_budget", "meta.object.set_status"}
RISK_LICET = "libera_gasto"
RISK_CONFIRM = "altera_conta"


def assess(operation: str, params: dict, cfg_currency: str = "USD"):
    """Devolve (nível de risco, lista de impactos em linguagem simples)."""
    if operation == "meta.ads.create":
        n = len(params.get("ads", []))
        if params.get("campaign_paused_expected"):
            return RISK_CONFIRM, [f"Cria {n} anúncio(s) numa campanha PAUSADA: gasto zero até ativar.",
                                  "Antes de criar, a campanha é conferida na Meta; se estiver ativa, a execução para."]
        return RISK_LICET, [f"Cria {n} anúncio(s) num conjunto que pode estar ativo: começam a gastar na hora.",
                            "Anúncio novo divide a verba com os atuais e passa pela fase de aprendizado."]
    if operation == "meta.launch.create_paused":
        n = len(params.get("ads", []))
        return RISK_CONFIRM, [
            "Cria campanha PAUSADA e um conjunto de anúncios: gasto zero até alguém ativar a campanha.",
            *( [f"Sobe {n} criativo(s) e cria {n} anúncio(s) dentro do conjunto (também sem gastar até a ativação)."] if n else []),
            f"O conjunto nasce com orçamento de {params.get('daily_budget_cents', 0)/100:.2f} {cfg_currency}/dia, "
            "que só começa a valer quando a campanha for ativada (ativação exige autorização de gasto).",
        ]
    if operation == "meta.adset.set_daily_budget":
        new, old = params.get("daily_budget_cents", 0), params.get("from_daily_budget_cents", 0)
        if not old:
            return RISK_LICET, ["Orçamento atual desconhecido: tratado como aumento de gasto (exige LICET)."]
        if new > old:
            return RISK_LICET, [f"Aumenta o gasto em {(new-old)/100:.2f} {cfg_currency}/dia.",
                                "Mudança de orçamento pode deixar o conjunto alguns dias em reaprendizado."]
        return RISK_CONFIRM, [f"Reduz o gasto em {(old-new)/100:.2f} {cfg_currency}/dia.",
                              "Menos entrega: menos conversas novas enquanto durar.",
                              "Mudança de orçamento pode deixar o conjunto alguns dias em reaprendizado."]
    if operation == "meta.object.set_status":
        if params.get("status") == "ACTIVE":
            return RISK_LICET, ["Começa a gastar até o orçamento definido no conjunto."]
        return RISK_CONFIRM, ["Interrompe a entrega e as conversas novas desse item.",
                              "Pausar não apaga nada e não reinicia o aprendizado; reativar exige autorização de gasto."]
    return RISK_LICET, ["Operação sem análise de impacto: tratada como de maior risco."]


class PolicyError(ValueError):
    """Proposta fora dos limites do cliente: não pode nem ser criada."""


def params_digest(params: dict) -> str:
    canon = json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


@dataclass
class Proposal:
    id: str
    client: str
    operation: str
    params: dict
    summary: str
    reason: str
    rollback: str
    daily_spend_delta_cents: int
    created_at: float
    expires_at: float
    status: str = "aguardando_aprovacao"
    digest: str = ""
    risk: str = RISK_LICET
    impact: list = field(default_factory=list)
    approval: dict = field(default_factory=dict)
    execution: dict = field(default_factory=dict)

    # ---- o que o humano autoriza no LICET (tem de bater 100% com o ledger) ----
    def licet_action(self) -> str:
        return f"{self.id} | {self.summary} | sha256:{self.digest[:16]}"

    def licet_target(self, cfg: ClientConfig) -> str:
        obj = self.params.get("object_id") or self.params.get("campaign_id") or "new"
        return f"meta:act_{cfg.ad_account_id}:{obj}"

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def _next_id(cfg: ClientConfig) -> str:
    day = time.strftime("%Y%m%d")
    cfg.proposals_dir.mkdir(parents=True, exist_ok=True)
    n = len(list(cfg.proposals_dir.glob(f"PA-{day}-*.json"))) + 1
    return f"PA-{day}-{n:03d}"


def check_policy(cfg: ClientConfig, operation: str, params: dict, current_daily_cents: int = 0):
    if operation not in OPERATIONS:
        raise PolicyError(f"Operação não permitida: {operation}")
    if not cfg.ad_account_id or not cfg.page_id:
        raise PolicyError("Conta de anúncios ou Página não configuradas (MISSING) em agencia/config.json.")
    cap = int(cfg.limits.get("max_daily_budget_cents") or 0)
    new = params.get("daily_budget_cents")
    if new is not None:
        if cap <= 0:
            raise PolicyError("Limite de orçamento diário não definido pelo cliente (limits.max_daily_budget_cents).")
        if new > cap:
            raise PolicyError(f"Orçamento {new/100:.2f} acima do limite do cliente ({cap/100:.2f}/dia).")
        if operation == "meta.adset.set_daily_budget" and current_daily_cents:
            max_pct = float(cfg.limits.get("max_increase_pct") or 20)
            if new > current_daily_cents * (1 + max_pct / 100) + 0.5:
                raise PolicyError(f"Aumento acima de {max_pct:.0f}% de uma vez (regra de escala). Divida em passos.")


def file_sha256(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _bind_ad_files(cfg: ClientConfig, params: dict):
    """Grava o SHA-256 de cada arquivo de criativo na proposta: o que foi autorizado é exatamente esse arquivo."""
    for ad in params.get("ads", []):
        for key in ("file", "thumbnail"):
            if ad.get(key):
                path = (cfg.folder / ad[key]).resolve()
                if cfg.folder.resolve() not in path.parents:
                    raise PolicyError(f"Arquivo fora da pasta do cliente: {ad[key]}")
                if not path.exists():
                    raise PolicyError(f"Arquivo de criativo não encontrado: {ad[key]}")
                ad[f"{key}_sha256"] = file_sha256(path)
        if ad.get("type") not in ("image", "video"):
            raise PolicyError(f"Anúncio '{ad.get('name')}': type deve ser image ou video.")
        if ad["type"] == "video" and not ad.get("thumbnail"):
            raise PolicyError(f"Anúncio de vídeo '{ad.get('name')}' precisa de uma imagem de capa (thumbnail).")
        for k in ("name", "primary_text", "headline"):
            if not ad.get(k):
                raise PolicyError(f"Anúncio sem '{k}'.")


def create(cfg: ClientConfig, operation: str, params: dict, summary: str, reason: str, rollback: str,
           daily_spend_delta_cents: int = 0, current_daily_cents: int = 0) -> Proposal:
    check_policy(cfg, operation, params, current_daily_cents)
    if params.get("ads"):
        if not cfg.instagram_user_id:
            raise PolicyError("ID da conta do Instagram não configurado (instagram_user_id MISSING) em agencia/config.json.")
        _bind_ad_files(cfg, params)
    now = time.time()
    p = Proposal(
        id=_next_id(cfg), client=cfg.name, operation=operation, params=params, summary=summary,
        reason=reason, rollback=rollback, daily_spend_delta_cents=daily_spend_delta_cents,
        created_at=now, expires_at=now + cfg.proposal_ttl_hours * 3600,
    )
    p.digest = params_digest({"operation": operation, "params": params})
    p.risk, p.impact = assess(operation, params, cfg.currency)
    save(cfg, p)
    audit(cfg, "proposta_criada", p.id, {"operation": operation, "summary": summary, "digest": p.digest})
    return p


def save(cfg: ClientConfig, p: Proposal):
    cfg.proposals_dir.mkdir(parents=True, exist_ok=True)
    (cfg.proposals_dir / f"{p.id}.json").write_text(p.to_json(), encoding="utf-8")


def load(cfg: ClientConfig, proposal_id: str) -> Proposal:
    path = cfg.proposals_dir / f"{proposal_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Proposta não encontrada: {proposal_id}")
    p = Proposal(**json.loads(path.read_text(encoding="utf-8")))
    if p.digest != params_digest({"operation": p.operation, "params": p.params}):
        raise PolicyError(f"{p.id}: arquivo da proposta foi alterado depois de criado (digest não confere).")
    p.risk, p.impact = assess(p.operation, p.params, cfg.currency)  # nunca confiar no risco gravado no arquivo
    if p.status == "aguardando_aprovacao" and time.time() > p.expires_at:
        p.status = "expirada"
        save(cfg, p)
    return p


def list_all(cfg: ClientConfig):
    if not cfg.proposals_dir.exists():
        return []
    return [load(cfg, f.stem) for f in sorted(cfg.proposals_dir.glob("PA-*.json"))]


def audit(cfg: ClientConfig, event: str, proposal_id: str, data: dict):
    cfg.agency_dir.mkdir(parents=True, exist_ok=True)
    line = {"ts": time.time(), "event": event, "proposal": proposal_id, **data}
    with open(cfg.audit_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")


def used_intent_hashes(cfg: ClientConfig) -> set:
    used = set()
    if cfg.audit_log.exists():
        for line in cfg.audit_log.read_text(encoding="utf-8").splitlines():
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("event") == "aprovada" and d.get("intent_hash"):
                used.add(d["intent_hash"])
    return used
