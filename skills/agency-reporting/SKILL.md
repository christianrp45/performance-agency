---
name: agency-reporting
description: 'Analista de performance da agência. Faz a revisão semanal (ou diária) das contas de anúncio e termina sempre com UMA decisão — HOLD, FIX, TEST ou INVESTIGATE — e um resumo de até 200 palavras para o cliente; também audita contas com nota honesta (separando saúde de cobertura de evidência). Use quando o pedido for relatório, "como está a campanha", análise do CSV da semana, auditoria de conta, "o que pausar/escalar", resultados do mês, ou quando uma rotina agendada precisar fechar a semana. Parte da suíte agency-*.'
---

# Relatório e decisão

Regras da casa: skill `agency`. Scripts: `agency-meta-ads/scripts/analisar_meta_csv.py`,
`agency-google-ads/scripts/analisar_google_csv.py`, `agency/scripts/viabilidade.py`.
Modelo: `agency/templates/relatorio-semanal.md`. Salvar em `<pasta do cliente>/relatorios/AAAA-MM-DD.md`.

## Entradas (mesma janela sempre: esta semana vs anterior)

Gasto e ritmo por campanha · impressões, cliques, CPC, CTR, CPM, parcela de impressões perdida ·
conversões e custo, **com a janela de atribuição de cada plataforma** · planilha de vendas (etapas e
vendas reais) · frequência e CTR dos anúncios com mais gasto · conversão da página por dispositivo ·
histórico de alterações. Faltou algo → **MISSING**, segue sem estimar.

## A revisão, em ordem (pare na primeira causa real)

| # | Pergunta | Olhar |
|---|---|---|
| 1 | O gasto mudou? | ritmo vs orçamento, limite atingido, conta limitada, cobrança |
| 2 | O tráfego mudou? | cliques, CPC, CTR, CPM, termos/posicionamentos novos |
| 3 | As conversões mudaram? | taxa, custo, qualidade (planilha), atraso dos últimos dias |
| 4 | O criativo cansou? | frequência, CTR vs pico do anúncio, gasto concentrado em anúncios velhos |
| 5 | A página quebrou? | velocidade, botões, formulário, celular vs desktop |
| 6 | O rastreio quebrou? | plataforma vs planilha vs analytics, eventos duplicados |

Cruze cada movimento com o histórico de alterações. Os últimos dias sempre estão incompletos.

## A decisão (exatamente uma por conta)

| Decisão | Quando |
|---|---|
| **HOLD** | variação normal, amostra pequena, aprendizado ou atraso — diga por quê e o que mudaria a decisão |
| **FIX** | problema conhecido com correção conhecida (formulário quebrado, orçamento travando campanha boa, anúncio reprovado) |
| **TEST** | hipótese que vale dinheiro — com métrica e regra de parada |
| **INVESTIGATE** | os dados não batem; **vence todas as outras** |

Nenhuma decisão move dinheiro sozinha: vira proposta `estado atual → mudança → efeito → como desfazer`.

## O resumo para o cliente (≤ 200 palavras)

1. Resultado vs meta (verde/amarelo/vermelho) por canal — **custo por venda vs teto**.
2. O que mudou e por quê (2–3 itens, com confiança alta/média/baixa).
3. Decisões da próxima semana (HOLD/FIX/TEST/INVESTIGATE, uma linha cada, aguardando aprovação).
Fechar com **fatos / hipóteses / dados faltando**.

## Auditoria de conta (quando pedida)

Detalhes: [references/auditoria.md](references/auditoria.md). O essencial: cada item é Passou / Falhou /
Desconhecido / Não se aplica; **desconhecido reduz a cobertura, nunca a saúde**; com cobertura < 60%
não se dá nota. Sem relatório de termos não existe lista de negativas. Benchmark de mercado é pista,
não veredito.

---
*Revisão ordenada, as quatro decisões e o resumo adaptados de `ads` (operating-check.md, audit-guardrails.md) de coreyhaines31/marketingskills (MIT), que credita Marek Dąbrowski e claude-ads de Daniel Agrici (MIT). Ver NOTICE.md.*
