"""Configuração por cliente.

Cada cliente tem, na própria pasta, `agencia/config.json` (limites e IDs, sem segredos) e
`agencia/.env` (segredos: token da Meta). Nada disso entra no repositório.
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULTS = {
    "meta_api_version": "v26.0",
    "licet_base_url": "https://licet.dev/v1",
    "agent_id": "performance-agency/meta-media-buyer",
    "proposal_ttl_hours": 24,
    "approval_max_age_minutes": 60,
    "require_ui_binding": True,
    "min_trust_level": "L1",
    "require_ledger_integrity": True,
    "spend_approval": "licet",  # "licet" ou "humano" (autorização digitada enquanto o LICET não está ativo)
    "dry_run": True,
    "limits": {"max_daily_budget_cents": 0, "max_increase_pct": 20},
}


@dataclass
class ClientConfig:
    folder: Path
    name: str
    ad_account_id: str = ""
    page_id: str = ""
    instagram_user_id: str = ""
    currency: str = "USD"
    meta_api_version: str = DEFAULTS["meta_api_version"]
    licet_base_url: str = DEFAULTS["licet_base_url"]
    agent_id: str = DEFAULTS["agent_id"]
    proposal_ttl_hours: int = DEFAULTS["proposal_ttl_hours"]
    approval_max_age_minutes: int = DEFAULTS["approval_max_age_minutes"]
    require_ui_binding: bool = DEFAULTS["require_ui_binding"]
    min_trust_level: str = DEFAULTS["min_trust_level"]
    require_ledger_integrity: bool = DEFAULTS["require_ledger_integrity"]
    spend_approval: str = DEFAULTS["spend_approval"]
    dry_run: bool = DEFAULTS["dry_run"]
    limits: dict = field(default_factory=lambda: dict(DEFAULTS["limits"]))

    @property
    def agency_dir(self) -> Path:
        return self.folder / "agencia"

    @property
    def proposals_dir(self) -> Path:
        return self.agency_dir / "propostas"

    @property
    def audit_log(self) -> Path:
        return self.agency_dir / "auditoria.jsonl"


def load(folder) -> ClientConfig:
    folder = Path(folder)
    path = folder / "agencia" / "config.json"
    if not path.exists():
        raise FileNotFoundError(f"Sem configuração: {path}. Crie a partir de templates/config.example.json.")
    data = json.loads(path.read_text(encoding="utf-8"))
    limits = dict(DEFAULTS["limits"])
    limits.update(data.pop("limits", {}))
    known = {k: v for k, v in data.items() if k in ClientConfig.__dataclass_fields__ and k not in ("folder", "limits")}
    cfg = ClientConfig(folder=folder, limits=limits, **known)
    # Desligar a simulação exige "dry_run": false no config E AGENCY_DRY_RUN=0 no ambiente.
    if cfg.spend_approval not in ("licet", "humano"):
        raise ValueError('spend_approval deve ser "licet" ou "humano".')
    if os.environ.get("AGENCY_DRY_RUN") != "0":
        cfg.dry_run = True
    return cfg


def load_secrets(cfg: ClientConfig) -> dict:
    """Lê `agencia/.env` (CHAVE=valor). Variáveis de ambiente têm prioridade."""
    secrets = {}
    env_file = cfg.agency_dir / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                secrets[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("META_ACCESS_TOKEN", "META_APP_SECRET"):
        if os.environ.get(k):
            secrets[k] = os.environ[k]
    return secrets
