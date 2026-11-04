"""Relatório semanal: lê os números (API da Meta ou o CSV mais recente em `dados/`) e grava
`relatorios/AAAA-MM-DD.md` na pasta do cliente. Só leitura: nunca altera a conta.

A decisão da semana (HOLD/FIX/TEST/INVESTIGATE) é tomada pela skill `agency-reporting` em cima deste arquivo.
"""
import subprocess
import sys
import time
from pathlib import Path

from .config import ClientConfig
from .meta import MetaClient

CONVERSATION_ACTIONS = ("onsite_conversion.messaging_conversation_started_7d",)
META_CSV_SCRIPT = Path(__file__).resolve().parents[2] / "skills" / "agency-meta-ads" / "scripts" / "analisar_meta_csv.py"


def _conversations(row: dict) -> float:
    return sum(float(a.get("value", 0)) for a in row.get("actions", []) or [] if a.get("action_type") in CONVERSATION_ACTIONS)


def from_api(cfg: ClientConfig, meta: MetaClient, date_preset: str = "last_7d") -> str:
    data = meta.insights(cfg.ad_account_id, date_preset=date_preset, level="ad").get("data", [])
    target = int(cfg.limits.get("target_cost_per_conversation_cents") or 2000) / 100
    lines = [f"Fonte: API da Meta ({date_preset}). Custo-alvo por conversa: ${target:.2f}.\n",
             "| Anúncio | Conjunto | Gasto | Conversas | Custo/conversa | Frequência | Sinal |",
             "|---|---|---|---|---|---|---|"]
    total_spend = total_conv = 0.0
    for r in sorted(data, key=lambda r: -float(r.get("spend", 0))):
        spend, conv, freq = float(r.get("spend", 0)), _conversations(r), float(r.get("frequency", 0) or 0)
        total_spend += spend
        total_conv += conv
        sinais = []
        if spend >= 3 * target and conv == 0:
            sinais.append("gastou 3× o alvo sem conversa → trocar conceito")
        elif conv and spend / conv > 1.5 * target and spend >= 3 * target:
            sinais.append("custo > 1,5× o alvo → trocar")
        if freq > 2.5:
            sinais.append("frequência alta → preparar substituto")
        cpc = f"${spend / conv:.2f}" if conv else "—"
        lines.append(f"| {r.get('ad_name', '')[:40]} | {r.get('adset_name', '')[:30]} | ${spend:.2f} | {conv:.0f} | {cpc} | "
                     f"{freq:.2f} | {'; '.join(sinais) or 'esperar dados' if spend < 3 * target else '; '.join(sinais) or 'ok'} |")
    lines.insert(1, f"**Total:** ${total_spend:.2f} gastos · {total_conv:.0f} conversas · "
                    f"{('$%.2f por conversa' % (total_spend / total_conv)) if total_conv else 'sem conversas'}\n")
    return "\n".join(lines)


def from_csv(cfg: ClientConfig) -> str:
    dados = cfg.folder / "dados"
    csvs = sorted((p for p in dados.glob("*.csv") if "planilha" not in p.name.lower()), key=lambda p: p.stat().st_mtime)
    if not csvs:
        return "Nenhum CSV do Gerenciador em `dados/` (MISSING). Exporte a semana e salve lá."
    if not META_CSV_SCRIPT.exists():
        return f"Script de análise não encontrado em {META_CSV_SCRIPT}."
    out = subprocess.run([sys.executable, str(META_CSV_SCRIPT), str(csvs[-1])], capture_output=True, text=True,
                         encoding="utf-8", timeout=120)
    return f"Fonte: `{csvs[-1].name}` (exportação do Gerenciador).\n\n" + (out.stdout or out.stderr)


def write(cfg: ClientConfig, meta: MetaClient = None) -> Path:
    use_api = meta is not None and not meta.dry_run
    body = from_api(cfg, meta) if use_api else from_csv(cfg)
    day = time.strftime("%Y-%m-%d")
    path = cfg.folder / "relatorios" / f"{day}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Relatório semanal · {cfg.name} · {day}\n\n"
        "**Decisão da conta:** _a definir pela skill `agency-reporting` (HOLD / FIX / TEST / INVESTIGATE)_\n\n"
        f"## Números\n\n{body}\n\n"
        "## Vendas (planilha de conversas)\n\n_Cruzar com `dados/planilha-conversas.csv`: conversas qualificadas, "
        "propostas, vendas e custo por venda._\n\n"
        "## Fatos · Hipóteses · Dados faltando\n\n- Fatos:\n- Hipóteses:\n- MISSING:\n", encoding="utf-8")
    return path
