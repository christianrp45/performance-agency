"""Conta de viabilidade de uma campanha de vendas.

Uso:
    python viabilidade.py --preco 6600 --margem 0.40 [--frete 0] [--fatia-teto 0.375]
                          [--fechamento 0.02,0.04] [--custo-conversa 15,25]
                          [--vendas-meta 2] [--orcamento-dia 60]

Responde: lucro bruto por venda, teto de custo por venda, custo máximo por conversa/lead,
ROAS de equilíbrio e quanto orçamento é preciso para ver as primeiras vendas.
Só usa a biblioteca padrão.
"""
import argparse
import sys


def moeda(v):
    return f"${v:,.2f}"


def lista(texto):
    return [float(x) for x in texto.split(",") if x.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preco", type=float, required=True)
    ap.add_argument("--margem", type=float, required=True, help="margem bruta, ex.: 0.40")
    ap.add_argument("--frete", type=float, default=0.0, help="custo de entrega por venda NÃO incluído na margem")
    ap.add_argument("--fatia-teto", type=float, default=0.375, help="parte do lucro bruto aceita como custo de anúncio")
    ap.add_argument("--fechamento", default="0.02,0.04", help="taxas de fechamento (conversa→venda)")
    ap.add_argument("--custo-conversa", default="15,25", help="custos por conversa/lead a simular")
    ap.add_argument("--vendas-meta", type=float, default=2, help="vendas para considerar a oferta validada")
    ap.add_argument("--orcamento-dia", type=float, default=0, help="orçamento diário planejado (opcional)")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    lucro = a.preco * a.margem - a.frete
    if lucro <= 0:
        sys.exit(f"Lucro bruto por venda é {moeda(lucro)}: com esse frete a venda não paga anúncio.")
    teto = lucro * a.fatia_teto
    roas_eq = a.preco / lucro
    fech = lista(a.fechamento)
    cpcs = lista(a.custo_conversa)

    print("# Viabilidade\n")
    print(f"- Preço: {moeda(a.preco)} · margem {a.margem:.0%} · frete fora da margem {moeda(a.frete)}")
    print(f"- **Lucro bruto por venda: {moeda(lucro)}**")
    print(f"- **Teto de custo por venda ({a.fatia_teto:.1%} do lucro): {moeda(teto)}**")
    print(f"- ROAS de equilíbrio (gasto = lucro): {roas_eq:.2f} · ROAS no teto: {a.preco / teto:.2f}\n")

    print("## Custo máximo por conversa/lead")
    print("| Fechamento | Máximo por conversa |")
    print("|---|---|")
    for f in fech:
        print(f"| {f:.0%} | {moeda(teto * f)} |")

    print("\n## Cenários")
    print("| Custo por conversa | Fechamento | Custo por venda | Sobra por venda | Dentro do teto? | Conversas p/ "
          f"{a.vendas_meta:g} vendas | Orçamento p/ {a.vendas_meta:g} vendas |")
    print("|---|---|---|---|---|---|---|")
    for c in cpcs:
        for f in fech:
            cpv = c / f
            conv = a.vendas_meta / f
            print(f"| {moeda(c)} | {f:.0%} | {moeda(cpv)} | {moeda(lucro - cpv)} | {'sim' if cpv <= teto else 'NÃO'} | "
                  f"{conv:.0f} | {moeda(conv * c)} |")

    if a.orcamento_dia:
        print(f"\n## Com {moeda(a.orcamento_dia)}/dia")
        for c in cpcs:
            semana = a.orcamento_dia * 7 / c
            print(f"- Conversa a {moeda(c)}: ~{semana:.0f} conversas/semana; "
                  + ", ".join(f"1ª venda em ~{(1 / f) / semana:.1f} semanas ({f:.0%})" for f in fech))

    print("\nPremissas: taxas de fechamento e custos por conversa são hipóteses até existir dado real do cliente.")


if __name__ == "__main__":
    main()
