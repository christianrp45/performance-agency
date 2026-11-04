"""Diagnóstico de exportação do Google Ads (termos de pesquisa, palavras-chave ou campanhas).

Uso:
    python analisar_google_csv.py relatorio.csv [--cpa-teto 990] [--taxa-conv 0.03] [--min-cliques 3]

Aceita CSV/TSV em UTF-8 ou UTF-16 (o padrão do Google Ads), com cabeçalhos em português ou inglês
e as linhas de título/período e de "Total" que o Google coloca. Imprime Markdown com: resumo,
linhas por gasto, termos com gasto e zero conversão (com quantos cliques ainda faltam para julgar)
e a taxa de conversão de equilíbrio. Só usa a biblioteca padrão.
"""
import argparse
import csv
import io
import sys
import unicodedata

COLUNAS = {
    "termo": ["termo de pesquisa", "search term"],
    "palavra": ["palavra-chave", "keyword"],
    "campanha": ["campanha", "campaign"],
    "grupo": ["grupo de anuncios", "ad group"],
    "tipo": ["tipo de correspondencia", "match type"],
    "cliques": ["cliques", "clicks"],
    "impressoes": ["impr.", "impressoes", "impressions"],
    "custo": ["custo", "cost"],
    "conversoes": ["conversoes", "conversions"],
    "valor": ["valor conv.", "conv. value", "valor de conv"],
}


def norm(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn").lower().strip()


def ler_texto(caminho):
    raw = open(caminho, "rb").read()
    for enc in ("utf-16", "utf-8-sig", "latin-1"):
        if enc == "utf-16" and not raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
            continue
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def numero(v):
    v = (v or "").strip().replace(" ", "").replace("$", "").replace("R$", "").replace("US", "").replace("%", "")
    if v in ("", "--", "-", "—"):
        return 0.0
    # 1.234,56 (pt) vs 1,234.56 (en)
    if "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".") if v.rfind(",") > v.rfind(".") else v.replace(",", "")
    elif "," in v:
        partes = v.split(",")
        v = v.replace(",", ".") if len(partes[-1]) in (1, 2) else v.replace(",", "")
    try:
        return float(v)
    except ValueError:
        return 0.0


def achar_cabecalho(linhas):
    for i, l in enumerate(linhas[:15]):
        n = [norm(c) for c in l]
        if any(c in ("cliques", "clicks") for c in n) and any(c in ("custo", "cost") for c in n):
            return i
    sys.exit("Não achei o cabeçalho (preciso das colunas Cliques/Clicks e Custo/Cost).")


def mapear(cab):
    n = [norm(c) for c in cab]
    m = {}
    for campo, nomes in COLUNAS.items():
        for i, c in enumerate(n):
            if c in nomes or any(c.startswith(x) for x in nomes if len(x) > 6):
                if campo == "custo" and ("/" in c or "por" in c or "per" in c):
                    continue
                if campo == "conversoes" and ("custo" in c or "cost" in c or "taxa" in c or "rate" in c or "todas" in c or "all" in c or "valor" in c or "value" in c):
                    continue
                m.setdefault(campo, i)
    return m


def moeda(v):
    return "—" if v is None else f"${v:,.2f}"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--cpa-teto", type=float,
                    help="custo máximo por conversão como a conta a define (lead/contato: teto por venda × fechamento)")
    ap.add_argument("--taxa-conv", type=float, default=0.03, help="taxa de conversão esperada (para cliques necessários)")
    ap.add_argument("--min-cliques", type=int, default=3)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    texto = ler_texto(a.csv)
    amostra = texto[:4000]
    delim = "\t" if amostra.count("\t") > amostra.count(",") else ","
    linhas = list(csv.reader(io.StringIO(texto), delimiter=delim))
    h = achar_cabecalho(linhas)
    m = mapear(linhas[h])
    chave = "termo" if "termo" in m else ("palavra" if "palavra" in m else "campanha")
    rotulo = {"termo": "Termo de pesquisa", "palavra": "Palavra-chave", "campanha": "Campanha"}[chave]

    dados = []
    for l in linhas[h + 1:]:
        if not l or not any(c.strip() for c in l):
            continue
        g = lambda k: l[m[k]] if k in m and m[k] < len(l) else ""
        nome = g(chave).strip()
        if not nome or norm(nome).startswith("total"):
            continue
        dados.append({
            "nome": nome.replace("|", "/"),
            "campanha": g("campanha").strip(),
            "tipo": g("tipo").strip(),
            "cliques": numero(g("cliques")),
            "impr": numero(g("impressoes")),
            "custo": numero(g("custo")),
            "conv": numero(g("conversoes")),
            "valor": numero(g("valor")),
        })
    if not dados:
        sys.exit("Nenhuma linha de dados encontrada.")

    custo = sum(d["custo"] for d in dados)
    cliques = sum(d["cliques"] for d in dados)
    conv = sum(d["conv"] for d in dados)
    impr = sum(d["impr"] for d in dados)
    cpc = custo / cliques if cliques else 0
    print(f"# Diagnóstico Google Ads — {len(dados)} linhas ({rotulo.lower()})\n")
    print(f"Gasto **{moeda(custo)}** · cliques {cliques:,.0f} · impressões {impr:,.0f} · CTR "
          f"{(cliques / impr * 100 if impr else 0):.2f}% · CPC médio {moeda(cpc)} · conversões {conv:,.1f} · "
          f"custo/conv. {moeda(custo / conv if conv else None)}")
    if chave == "termo":
        print("\n> O relatório de termos mostra só os termos divulgados pelo Google. Compare os cliques acima com os "
              "cliques totais da campanha para saber quanto ele cobre.")

    if a.cpa_teto:
        eq = cpc / a.cpa_teto if a.cpa_teto else 0
        print(f"\nTaxa de conversão de equilíbrio (CPC {moeda(cpc)} ÷ teto {moeda(a.cpa_teto)}): **{eq:.2%}**. "
              f"Termos que convertem abaixo disso custam mais que o teto.")
    precisa = 3 / a.taxa_conv if a.taxa_conv else 0
    print(f"Cliques para julgar um termo com {a.taxa_conv:.0%} de conversão esperada: ~{precisa:.0f}.\n")

    print(f"## Maiores gastos\n\n| {rotulo} | Campanha | Tipo | Cliques | Gasto | Conv. | Custo/conv. |")
    print("|---|---|---|---|---|---|---|")
    for d in sorted(dados, key=lambda d: -d["custo"])[:20]:
        print(f"| {d['nome'][:50]} | {d['campanha'][:30]} | {d['tipo'] or '—'} | {d['cliques']:.0f} | {moeda(d['custo'])} | "
              f"{d['conv']:.1f} | {moeda(d['custo'] / d['conv'] if d['conv'] else None)} |")

    zero = [d for d in dados if d["conv"] == 0 and d["cliques"] >= a.min_cliques]
    print(f"\n## Gasto sem conversão ({len(zero)} linhas com ≥ {a.min_cliques} cliques, "
          f"{moeda(sum(d['custo'] for d in zero))} no total)\n")
    if zero:
        print(f"| {rotulo} | Cliques | Gasto | Decisão sugerida |")
        print("|---|---|---|---|")
        for d in sorted(zero, key=lambda d: -d["custo"])[:25]:
            faltam = max(0, precisa - d["cliques"])
            dec = ("revisar: amostra suficiente — negativar se for irrelevante" if faltam == 0
                   else f"esperar ~{faltam:.0f} cliques, a menos que seja claramente irrelevante")
            if a.cpa_teto and d["custo"] >= a.cpa_teto:
                dec = "gastou ≥ 1 teto sem converter — revisar já"
            print(f"| {d['nome'][:50]} | {d['cliques']:.0f} | {moeda(d['custo'])} | {dec} |")
        print("\nNegativar só o que é claramente irrelevante para o negócio. Incerto ≠ irrelevante.")

    if a.cpa_teto:
        caros = [d for d in dados if d["conv"] > 0 and d["custo"] / d["conv"] > a.cpa_teto * 1.5]
        if caros:
            print(f"\n## Convertendo acima de 1,5× o teto\n")
            for d in sorted(caros, key=lambda d: -d["custo"])[:15]:
                print(f"- {d['nome'][:60]} — {moeda(d['custo'] / d['conv'])} por conversão ({d['conv']:.1f} conv.)")

    print("\nFatos: os números acima. Hipóteses e dados faltando (vendas reais, termos ocultos, atraso de "
          "conversão nos últimos dias) devem ser listados na resposta.")


if __name__ == "__main__":
    main()
