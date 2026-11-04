"""Propostas: toda ação que mexe em dinheiro nasce como proposta e só anda com aprovação LICET.

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
}
MONEY_OPERATIONS = {"meta.adset.set_daily_budget", "meta.object.set_status"}


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


def create(cfg: ClientConfig, operation: str, params: dict, summary: str, reason: str, rollback: str,
           daily_spend_delta_cents: int = 0, current_daily_cents: int = 0) -> Proposal:
    check_policy(cfg, operation, params, current_daily_cents)
    now = time.time()
    p = Proposal(
        id=_next_id(cfg), client=cfg.name, operation=operation, params=params, summary=summary,
        reason=reason, rollback=rollback, daily_spend_delta_cents=daily_spend_delta_cents,
        created_at=now, expires_at=now + cfg.proposal_ttl_hours * 3600,
    )
    p.digest = params_digest({"operation": operation, "params": params})
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
