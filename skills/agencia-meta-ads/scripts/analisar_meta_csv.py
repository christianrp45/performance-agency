"""Diagnóstico de exportação CSV do Gerenciador de Anúncios da Meta.

Uso:
    python analisar_meta_csv.py arquivo.csv [--preco 6600] [--margem 0.40] [--fechamento 0.02,0.04]

Lê cabeçalhos em português ou inglês, ignora a linha de total e imprime um
relatório em Markdown com: gasto por objetivo, tabela por conjunto, e alertas
(sem venda medida, fase de aprendizado, criativo duplicado, campanhas ativas,
conjuntos sem entrega). Só usa a biblioteca padrão.
"""
import argparse
import csv
import re
import sys
import unicodedata
from collections import defaultdict

# Palavras-chave (sem acento, minúsculas) para achar cada coluna em PT ou EN.
COLUNAS = {
    "nome": [["nome da campanha"], ["campaign name"], ["nome do anuncio"], ["ad name"], ["nome do conjunto"], ["ad set name"]],
    "status": [["veiculacao"], ["delivery"]],
    "orcamento": [["orcamento do conjunto"], ["ad set budget"], ["orcamento"], ["budget"]],
    "tipo_orcamento": [["tipo de orcamento"], ["budget type"]],
    "resultados": [["resultados"], ["results"]],
    "indicador": [["indicador de resultados"], ["result indicator"]],
    "alcance": [["alcance"], ["reach"]],
    "impressoes": [["impressoes"], ["impressions"]],
    "gasto": [["valor gasto"], ["amount spent"]],
    "termino": [["termino"], ["ends"]],
    "inicio": [["inicio dos relatorios"], ["reporting starts"]],
}

OBJETIVOS = [
    ("purchase", "Compras"),
    ("lead", "Leads"),
    ("messaging_conversation_started", "Conversas por mensagem"),
    ("landing_page_view", "Visualizações da página"),
    ("link_click", "Cliques no link"),
    ("profile_visit", "Visitas ao perfil"),
    ("visit_instagram_profile", "Visitas ao perfil"),
    ("post_engagement", "Engajamento"),
    ("video_view", "Visualizações de vídeo"),
    ("reach", "Alcance"),
]
OBJETIVOS_DE_VENDA = {"Compras", "Leads"}
EVENTOS_POR_SEMANA_APRENDIZADO = 50


def sem_acento(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower().strip()


def mapear_colunas(cabecalho):
    norm = [sem_acento(c) for c in cabecalho]
    mapa = {}
    for campo, opcoes in COLUNAS.items():
        for palavras in opcoes:
            for i, c in enumerate(norm):
                if i in mapa.values():
                    continue
                if all(p in c for p in palavras) and not ("inicial" in c or "initial" in c):
                    # "resultados" não pode casar com "custo por resultados" nem "indicador de resultados".
                    if campo == "resultados" and ("custo" in c or "cost" in c or "indicador" in c or "indicator" in c):
                        continue
                    if campo == "orcamento" and ("tipo" in c or "type" in c):
                        continue
                    mapa[campo] = i
                    break
            if campo in mapa:
                break
    return mapa


def numero(valor):
    if valor is None:
        return None
    v = valor.strip()
    if not v:
        return None
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return None


def objetivo(indicador):
    ind = (indicador or "").lower()
    for chave, nome in OBJETIVOS:
        if chave in ind:
            return nome
    return indicador or "Sem resultado"


def criativo(nome):
    n = re.sub(r"^(post do instagram|instagram post|publicacao do instagram|facebook post)\s*:\s*", "", sem_acento(nome))
    n = re.sub(r"[.…]+$", "", n).strip()
    # Nomes truncados pela Meta variam no fim; compara pelas primeiras palavras.
    return " ".join(n.split()[:4])


def moeda(v):
    return "—" if v is None else f"${v:,.2f}"


def ler(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.reader(f))
    if not linhas:
        sys.exit("CSV vazio.")
    mapa = mapear_colunas(linhas[0])
    faltando = [c for c in ("nome", "gasto", "impressoes") if c not in mapa]
    if faltando:
        sys.exit(f"Não achei as colunas {faltando}. Cabeçalho lido: {linhas[0]}")
    moeda_conta = re.search(r"\((\w{3})\)", linhas[0][mapa["gasto"]])
    conjuntos = []
    for linha in linhas[1:]:
        if not any(linha):
            continue
        get = lambda k: linha[mapa[k]] if k in mapa and mapa[k] < len(linha) else ""
        nome = get("nome").strip().replace("|", "/")  # "|" quebra a tabela em Markdown
        if not nome:  # linha de total
            continue
        gasto = numero(get("gasto")) or 0.0
        resultados = numero(get("resultados"))
        conjuntos.append({
            "nome": nome,
            "status": get("status").strip().lower(),
            "orcamento": numero(get("orcamento")),
            "tipo_orcamento": get("tipo_orcamento").strip(),
            "resultados": resultados or 0.0,
            "objetivo": objetivo(get("indicador")) if resultados else "Sem resultado",
            "alcance": numero(get("alcance")) or 0.0,
            "impressoes": numero(get("impressoes")) or 0.0,
            "gasto": gasto,
            "termino": get("termino").strip(),
        })
    return conjuntos, (moeda_conta.group(1) if moeda_conta else "")


def relatorio(conjuntos, moeda_conta, preco, margem, fechamentos):
    out = []
    p = out.append
    total = sum(c["gasto"] for c in conjuntos)
    imp = sum(c["impressoes"] for c in conjuntos)
    p(f"# Diagnóstico da conta ({len(conjuntos)} conjuntos, {moeda_conta or 'moeda da conta'})\n")
    p(f"Gasto total: **{moeda(total)}** · Impressões: {imp:,.0f} · CPM médio: {moeda(total / imp * 1000 if imp else None)}\n")

    # Por objetivo
    grupos = defaultdict(lambda: {"gasto": 0.0, "res": 0.0, "imp": 0.0, "n": 0})
    for c in conjuntos:
        g = grupos[c["objetivo"]]
        g["gasto"] += c["gasto"]; g["res"] += c["resultados"]; g["imp"] += c["impressoes"]; g["n"] += 1
    p("## Gasto por objetivo\n")
    p("| Objetivo | Conjuntos | Gasto | % | Resultados | Custo/resultado | CPM |")
    p("|---|---|---|---|---|---|---|")
    for nome, g in sorted(grupos.items(), key=lambda kv: -kv[1]["gasto"]):
        if g["gasto"] == 0 and g["res"] == 0:
            continue
        p(f"| {nome} | {g['n']} | {moeda(g['gasto'])} | {g['gasto'] / total * 100 if total else 0:.0f}% | {g['res']:,.0f} | "
          f"{moeda(g['gasto'] / g['res'] if g['res'] else None)} | {moeda(g['gasto'] / g['imp'] * 1000 if g['imp'] else None)} |")
    p("")

    # Por conjunto
    p("## Por conjunto\n")
    p("| Nome | Status | Objetivo | Orçamento | Gasto | Resultados | Custo/res. | Taxa res./impr. | CPM | Freq. |")
    p("|---|---|---|---|---|---|---|---|---|---|")
    for c in sorted(conjuntos, key=lambda c: -c["gasto"]):
        taxa = c["resultados"] / c["impressoes"] * 100 if c["impressoes"] else 0
        freq = c["impressoes"] / c["alcance"] if c["alcance"] else 0
        orc = f"{moeda(c['orcamento'])} {c['tipo_orcamento']}".strip() if c["orcamento"] else "—"
        p(f"| {c['nome'][:45]} | {c['status'] or '—'} | {c['objetivo']} | {orc} | {moeda(c['gasto'])} | {c['resultados']:,.0f} | "
          f"{moeda(c['gasto'] / c['resultados'] if c['resultados'] else None)} | {taxa:.2f}% | "
          f"{moeda(c['gasto'] / c['impressoes'] * 1000 if c['impressoes'] else None)} | {freq:.2f} |")
    p("")

    # Alertas
    alertas = []
    if not any(c["objetivo"] in OBJETIVOS_DE_VENDA for c in conjuntos):
        alertas.append(("CRÍTICO", "Nenhum conjunto mede venda ou lead. Não dá para saber o retorno do gasto. "
                        "Instalar Pixel/API de Conversões ou marcar vendas vindas das conversas."))

    presos = []
    for c in conjuntos:
        if not c["resultados"] or not c["orcamento"] or c["tipo_orcamento"].lower() not in ("diário", "diario", "daily"):
            continue
        por_semana = c["orcamento"] * 7 / (c["gasto"] / c["resultados"])
        if por_semana < EVENTOS_POR_SEMANA_APRENDIZADO:
            presos.append(f"{c['nome'][:40]} [{c['objetivo']}] (~{int(por_semana)}/semana)")
    if presos:
        alertas.append(("ALTO", f"{len(presos)} conjunto(s) com orçamento diário que não chega a "
                        f"{EVENTOS_POR_SEMANA_APRENDIZADO} resultados/semana, então não saem da fase de aprendizado: "
                        + "; ".join(presos) + ". Concentrar orçamento em menos conjuntos."))

    por_criativo = defaultdict(list)
    for c in conjuntos:
        por_criativo[criativo(c["nome"])].append(c)
    for chave, grupo in por_criativo.items():
        if len(grupo) < 2:
            continue
        objetivos = defaultdict(list)
        for c in grupo:
            if c["resultados"]:
                objetivos[c["objetivo"]].append(c["gasto"] / c["resultados"])
        detalhe = ""
        for obj, custos in objetivos.items():
            if len(custos) > 1 and min(custos) > 0:
                detalhe += f" Em '{obj}' o custo variou de {moeda(min(custos))} a {moeda(max(custos))} ({max(custos) / min(custos):.1f}x)."
        alertas.append(("MÉDIO", f"O mesmo criativo \"{grupo[0]['nome'][:45]}\" aparece em {len(grupo)} conjuntos "
                        f"(disputam o mesmo público e dividem o aprendizado).{detalhe}"))

    if any(sem_acento(c["nome"]).startswith(("post do instagram", "instagram post")) for c in conjuntos):
        alertas.append(("MÉDIO", "Nomes no padrão 'Post do Instagram: ...' indicam campanhas criadas pelo botão "
                        "Impulsionar, com pouco controle de público e posicionamento. Criar pelo Gerenciador."))

    ativos = [c for c in conjuntos if c["status"] == "active"]
    if ativos:
        diario = sum(c["orcamento"] or 0 for c in ativos if c["tipo_orcamento"].lower() in ("diário", "diario", "daily"))
        alertas.append(("INFO", f"{len(ativos)} conjunto(s) ainda ativos (~{moeda(diario)}/dia): "
                        + "; ".join(c["nome"][:40] for c in ativos) + ". Confirmar se é intencional."))

    mortos = [c for c in conjuntos if c["impressoes"] <= 10]
    if mortos:
        alertas.append(("INFO", "Sem entrega (≤10 impressões): " + "; ".join(c["nome"][:40] for c in mortos)
                        + ". Ver se foi reprovado ou ficou sem orçamento."))

    altos = [c for c in conjuntos if c["alcance"] and c["impressoes"] / c["alcance"] > 3]
    if altos:
        alertas.append(("MÉDIO", "Frequência acima de 3 (público cansando): " + "; ".join(c["nome"][:40] for c in altos)))

    p("## Alertas\n")
    if not alertas:
        p("Nenhum alerta automático.\n")
    for nivel, texto in alertas:
        p(f"- **{nivel}:** {texto}")
    p("")

    if preco and margem:
        lucro = preco * margem
        teto = lucro * 0.375
        p("## Viabilidade\n")
        p(f"Lucro bruto por venda: {moeda(lucro)} · Teto sugerido de custo por venda (37,5% do lucro): **{moeda(teto)}**\n")
        p("| Taxa de fechamento | Custo máximo por conversa/lead |")
        p("|---|---|")
        for f in fechamentos:
            p(f"| {f * 100:.0f}% | {moeda(teto * f)} |")
        conv = grupos.get("Conversas por mensagem")
        if conv and conv["res"]:
            atual = conv["gasto"] / conv["res"]
            p(f"\nCusto atual por conversa nesta conta: {moeda(atual)}. Com esse custo, cada venda sai a "
              + ", ".join(f"{moeda(atual / f)} ({f * 100:.0f}%)" for f in fechamentos) + ".")
        p("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--preco", type=float)
    ap.add_argument("--margem", type=float, help="ex.: 0.40 para 40%%")
    ap.add_argument("--fechamento", default="0.02,0.04", help="taxas de fechamento separadas por vírgula")
    a = ap.parse_args()
    conjuntos, moeda_conta = ler(a.csv)
    fechamentos = [float(x) for x in a.fechamento.split(",") if x.strip()]
    sys.stdout.reconfigure(encoding="utf-8")
    print(relatorio(conjuntos, moeda_conta, a.preco, a.margem, fechamentos))


if __name__ == "__main__":
    main()
