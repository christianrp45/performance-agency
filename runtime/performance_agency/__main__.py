"""Linha de comando da Performance Agency.

    python -m performance_agency <pasta do cliente> <comando> [...]

Comandos:
  status                              mostra configuração (sem segredos) e propostas
  propor-lancamento <spec.json>       cria proposta: campanha PAUSADA + conjunto (não gasta até ativar)
  propor-orcamento <adset_id> <atual_usd> <novo_usd> <motivo>
  propor-status <object_id> <PAUSED|ACTIVE> <motivo>
  aprovar <proposta> <intent_hash>    verifica a autorização no ledger LICET e aprova
  confirmar <proposta> "<frase>" <nome>  autorização digitada: "CONFIRMO <id>" (não libera gasto) ou
                                      "AUTORIZO GASTO <id>" (libera gasto, se spend_approval = "humano")
  executar <proposta>                 reverifica no LICET e executa na Meta (simulação por padrão)
  pedido <proposta>                   mostra exatamente o que autorizar no app LICET
  relatorio                           grava relatorios/AAAA-MM-DD.md (API da Meta ou CSV mais recente em dados/)
"""
import json
import sys
from pathlib import Path

from . import config, executor, proposals, report


def cents(usd: str) -> int:
    return int(round(float(usd.replace(",", ".")) * 100))


def show_request(cfg, p):
    if p.risk == proposals.RISK_LICET and cfg.spend_approval == "humano":
        print("\nRisco: LIBERA GASTO — autorização humana digitada (LICET ainda não ativo para este cliente).")
        print(f'Para autorizar: confirmar {p.id} "AUTORIZO GASTO {p.id}" <seu nome>')
    elif p.risk == proposals.RISK_LICET:
        print("\nRisco: LIBERA GASTO — só pode ser autorizada pelo LICET.")
    else:
        print("\nRisco: altera a conta sem liberar gasto — LICET ou confirmação digitada.")
    for item in p.impact:
        print(f"  • {item}")
    if p.risk == proposals.RISK_CONFIRM:
        print(f'Para confirmar sem LICET: confirmar {p.id} "CONFIRMO {p.id}" <seu nome>')
    print(f"\nAutorize no app LICET exatamente isto:\n"
          f"  action   : {p.licet_action()}\n"
          f"  agent_id : {cfg.agent_id}\n"
          f"  target   : {p.licet_target(cfg)}\n"
          f"Depois copie o intent hash e rode: aprovar {p.id} <intent_hash>\n"
          f"Validade da proposta: até {__import__('time').strftime('%d/%m %H:%M', __import__('time').localtime(p.expires_at))}.")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2:
        print(__doc__)
        return 2
    sys.stdout.reconfigure(encoding="utf-8")
    cfg = config.load(Path(argv[0]))
    cmd, args = argv[1], argv[2:]

    if cmd == "status":
        print(f"Cliente: {cfg.name} | conta: act_{cfg.ad_account_id or 'MISSING'} | página: {cfg.page_id or 'MISSING'}")
        print(f"Simulação: {'LIGADA (nada é enviado à Meta)' if cfg.dry_run else 'DESLIGADA'} | "
              f"limite diário: {cfg.limits.get('max_daily_budget_cents', 0)/100:.2f} {cfg.currency} | "
              f"aumento máx.: {cfg.limits.get('max_increase_pct')}% | autorização de gasto: "
              f"{'LICET' if cfg.spend_approval == 'licet' else 'humana digitada (LICET depois)'}")
        for p in proposals.list_all(cfg):
            print(f"- {p.id} [{p.status}] [{p.risk}] {p.summary}")
        return 0

    if cmd == "propor-lancamento":
        spec = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        p = proposals.create(cfg, "meta.launch.create_paused", spec["params"], spec["summary"], spec["reason"],
                             spec.get("rollback", "Campanha nasce pausada; para desfazer, arquive-a no Gerenciador."))
        print(f"Proposta {p.id} criada: {p.summary}")
        show_request(cfg, p)
        return 0

    if cmd == "propor-orcamento":
        adset, atual, novo, motivo = args[0], cents(args[1]), cents(args[2]), " ".join(args[3:])
        p = proposals.create(cfg, "meta.adset.set_daily_budget",
                             {"object_id": adset, "daily_budget_cents": novo, "from_daily_budget_cents": atual},
                             f"Orçamento do conjunto {adset}: {atual/100:.2f} → {novo/100:.2f} {cfg.currency}/dia", motivo,
                             f"Voltar para {atual/100:.2f}/dia com nova proposta.", (novo - atual), current_daily_cents=atual)
        print(f"Proposta {p.id} criada: {p.summary}")
        show_request(cfg, p)
        return 0

    if cmd == "propor-status":
        obj, status, motivo = args[0], args[1].upper(), " ".join(args[2:])
        p = proposals.create(cfg, "meta.object.set_status", {"object_id": obj, "status": status},
                             f"{'Ativar' if status == 'ACTIVE' else 'Pausar'} {obj}", motivo,
                             f"Proposta inversa: {'PAUSED' if status == 'ACTIVE' else 'ACTIVE'}.")
        print(f"Proposta {p.id} criada: {p.summary}")
        show_request(cfg, p)
        return 0

    if cmd == "pedido":
        show_request(cfg, proposals.load(cfg, args[0]))
        return 0

    if cmd == "aprovar":
        p = executor.approve(cfg, args[0], args[1])
        print(f"{p.id} APROVADA pelo LICET (ledger #{p.approval.get('ledger_id')}, {p.approval.get('trust_level')}).")
        return 0

    if cmd == "relatorio":
        meta = None if cfg.dry_run else executor.client_for(cfg)
        print(f"Relatório gravado em {report.write(cfg, meta)}")
        return 0

    if cmd == "confirmar":
        p = executor.confirm(cfg, args[0], args[1], " ".join(args[2:]))
        print(f"{p.id} CONFIRMADA por {p.approval.get('by') or 'humano'} (sem liberar gasto).")
        return 0

    if cmd == "executar":
        p, result = executor.execute(cfg, args[0])
        print(f"{p.id}: {'SIMULADO — nada foi enviado à Meta' if p.execution.get('dry_run') else 'EXECUTADO'}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(__doc__)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (proposals.PolicyError, executor.ExecutionRefused, FileNotFoundError) as e:
        print(f"RECUSADO: {e}")
        sys.exit(1)
