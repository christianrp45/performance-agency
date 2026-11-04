"""Portão LICET: só deixa executar o que um humano autorizou, livre e consciente, no LICET.

A verificação é feita no ledger público do LICET (`GET /ledger/verify?hash=<intent_hash>`), nunca
no que o app ou o agente "dizem". O registro precisa bater exatamente com a proposta.
"""
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from .config import ClientConfig
from .proposals import Proposal

HEX64 = re.compile(r"^[0-9a-f]{64}$")


@dataclass
class GateResult:
    ok: bool
    reasons: list = field(default_factory=list)
    record: dict = field(default_factory=dict)


def fetch_ledger_record(cfg: ClientConfig, intent_hash: str, timeout: float = 15.0) -> dict:
    url = f"{cfg.licet_base_url.rstrip('/')}/ledger/verify?hash={urllib.parse.quote(intent_hash)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "performance-agency/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}
        raise


def verify(cfg: ClientConfig, p: Proposal, intent_hash: str, used_hashes: set = frozenset(),
           fetch=fetch_ledger_record, now: float = None, at_execution: bool = False) -> GateResult:
    now = time.time() if now is None else now
    reasons = []
    intent_hash = (intent_hash or "").strip().lower()
    if not HEX64.match(intent_hash):
        return GateResult(False, ["intent_hash inválido (esperado SHA-256 em hexadecimal, 64 caracteres)."])
    if not at_execution and intent_hash in used_hashes:
        return GateResult(False, ["Esta autorização LICET já foi usada em outra proposta (uso único)."])

    try:
        rec = fetch(cfg, intent_hash)
    except Exception as e:  # rede, TLS, JSON
        return GateResult(False, [f"Não foi possível consultar o ledger LICET: {type(e).__name__}. Nada executado."])
    if not rec:
        return GateResult(False, ["Autorização não encontrada no ledger LICET."])

    def expect(cond, msg):
        if not cond:
            reasons.append(msg)

    expect(rec.get("authorized") is True, "LICET negou a autorização (authorized=false).")
    expect(not rec.get("revoked"), f"Autorização revogada no LICET: {rec.get('revocation_reason') or 'sem motivo'}.")
    expect(rec.get("intent_hash", "").lower() == intent_hash, "Registro do ledger não corresponde ao hash informado.")
    expect(rec.get("agent_id") == cfg.agent_id, f"agent_id diferente: {rec.get('agent_id')!r} ≠ {cfg.agent_id!r}.")
    expect(rec.get("target") == p.licet_target(cfg), f"Alvo diferente: {rec.get('target')!r} ≠ {p.licet_target(cfg)!r}.")
    expect(rec.get("action") == p.licet_action(), "A ação autorizada no LICET não é exatamente esta proposta.")
    if cfg.require_ui_binding:
        expect(rec.get("ui_binding_status") == "VERIFIED",
               f"Vínculo de tela não verificado (ui_binding_status={rec.get('ui_binding_status')!r}).")
    ts = float(rec.get("timestamp") or 0)
    expect(p.created_at - 120 <= ts <= p.expires_at, "Autorização feita fora da validade da proposta.")
    expect(now - ts <= cfg.approval_max_age_minutes * 60,
           f"Autorização com mais de {cfg.approval_max_age_minutes} min: peça uma nova no LICET.")
    return GateResult(not reasons, reasons, rec)
