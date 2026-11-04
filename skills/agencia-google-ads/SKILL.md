---
name: agencia-google-ads
description: Gestor de Google Ads da agência de performance. Monta e opera campanhas de Pesquisa (palavras-chave por intenção, tipos de correspondência, negativas, anúncios responsivos RSA, extensões), Local (Perfil de Empresa, chamadas, "perto de mim"), Performance Max e YouTube com travas; lê relatórios de termos de pesquisa e de campanha exportados em CSV; define lances por volume de conversões e importação de vendas offline. Use quando o pedido mencionar Google Ads, AdWords, anúncio no Google, campanha de pesquisa, palavra-chave, palavra-chave negativa, termos de pesquisa, RSA, Performance Max, PMax, YouTube Ads, Local Services, CPC, índice de qualidade, parcela de impressões ou CSV do Google Ads. Parte da suíte agencia-*.
---

# Google Ads

Regras da casa: skill `agencia`. Teto de custo por venda: `agencia-oferta`.

**A Pesquisa colhe a demanda que já existe; não cria demanda.** Se quase ninguém busca o produto,
diga isso e ponha a verba na Meta/YouTube. Quando existe busca ("live edge dining table Dallas"),
a Pesquisa costuma ser o dinheiro mais eficiente da conta.

## A escada de intenção (abrir degrau por degrau)

1. **Marca** — buscas pelo nome. Barato, sempre ligado, orçamento próprio e limitado.
2. **Alta intenção sem marca** — quem quer comprar ("waterfall dining table", "solid wood dining table 10 ft", "+ near me"/cidade). Onde mora a maior parte da verba.
3. **Concorrente** — "[concorrente] alternative". CPC alto; só com página de comparação.
4. **Problema** — "how to choose a dining table size". Retorno lento; só depois do 1 e 2.
5. **Demanda/consciência** — Display, YouTube, Demand Gen. Por último, com sobra.

Não pule degraus.

## Estrutura mínima (cada uma com orçamento próprio)

- **Marca** · **Alta intenção** (grupos por tema, 5–15 palavras com a mesma promessa, 2–3 RSAs cada)
  · **Concorrente** (se houver) · **Remarketing** (separado da Pesquisa).
- Orçamento compartilhado deixa a Marca comer tudo e cega o resto.
- Campanha que não chega a ~15–30 conversões/mês não alimenta lance automático: juntar.
- **Configurações em toda campanha nova:** desligar Parceiros de pesquisa e Rede de Display;
  localização = **"Presença"** (quem está na região, não quem "se interessa" por ela);
  idioma segue o idioma da interface do usuário.
- Mesma palavra no mesmo tipo de correspondência em dois grupos = competir consigo mesmo.

## Palavras-chave e correspondência

- Fonte: como o **comprador** descreve o que quer (conversas de venda, termos de pesquisa,
  anúncios de concorrentes). 50 buscas com intenção clara valem mais que 5.000 misturadas.
- Comece com **Frase + Exata**. **Ampla só depois** de: 30+ conversões/mês na campanha + lance
  automático ligado + lista de negativas forte. O mesmo vale para o **AI Max**.
- Produto local/físico: inclua cidade, estado e "near me"; use extensões de local e de chamada.

## Negativas — nunca inventar

Sem relatório de termos de pesquisa, **não existe lista de negativas** (peça o relatório).
Listas iniciais aceitáveis no lançamento, por serem genéricas: emprego/vagas, grátis, DIY/"como fazer",
curso, PDF, usado (se não vende usado), aluguel (se não aluga), a própria marca nas campanhas sem marca.
Cuidado com a mecânica: negativa ampla exige todas as palavras; frase bloqueia a sequência; exata, só a busca exata.
Ritual semanal e leitura do relatório: [references/pesquisa.md](references/pesquisa.md).

## Lances por volume

| Conversões/mês na campanha | Estratégia |
|---|---|
| 0–15 | CPC manual ou Maximizar conversões (sem meta) |
| 15–30 | Maximizar conversões |
| 30+ estável | CPA desejado perto do real dos últimos 30 dias |
| Valor real de venda voltando | ROAS desejado |

Mude metas em passos de ±10–15% e espere 1–2 semanas. A campanha pode gastar até 2× o diário
num dia (o Google equilibra no mês).

## Conversões que importam

O maior salto de uma conta: **importar vendas offline** (GCLID / Google Click ID, ou integração com o
CRM/planilha) com o valor real. Sem isso o lance automático otimiza para clique em "ligar" e
formulário qualquer. Configure com a skill `agencia-rastreio`.

## Anúncios responsivos (RSA)

Siga [references/rsa.md](references/rsa.md): até 15 títulos de **30 caracteres**, 4 descrições de
**90**, caminhos de 15, sempre com grupos, negativas sugeridas (só genéricas), sitelinks, frases de
destaque e conferência de limites antes de entregar. Preço e região nos títulos para filtrar.

## Performance Max — com travas

Ordem de valor: Marca > Alta intenção > Remarketing > PMax > Demand Gen. PMax nunca é a primeira
campanha, nem com rastreio fraco ou verba pequena. Quando usar: exclusão de marca na conta, sinais de
público com dados próprios, vídeo próprio (senão o Google gera um ruim), vendas offline importadas
antes de escalar, e checar a sobreposição com a Pesquisa (termos de pesquisa do PMax vs palavras da Pesquisa).

## Local (negócio com ponto físico)

**Perfil de Empresa no Google** completo (categoria, fotos reais, horário, produtos, avaliações) antes
de anunciar; extensão de local na Pesquisa; campanhas com objetivo de visitas/ligações quando o
showroom estiver aberto. Local Services Ads só existe para algumas categorias — verificar elegibilidade.

## Análise de CSV

```bash
python scripts/analisar_google_csv.py "<pasta do cliente>/dados/<relatorio>.csv" --cpa-teto 30 --taxa-conv 0.03
```
`--cpa-teto` é o máximo por **conversão como a conta define**. Se a conversão é contato/lead (não
venda), use teto de custo por venda × taxa de fechamento (ex.: $990 × 3% ≈ $30).
Aceita relatório de **termos de pesquisa** ou de **campanhas/palavras-chave** (PT ou EN). Mostra gasto
por linha, CPA, termos com gasto e zero conversão, a **taxa de conversão de equilíbrio** e quantos
cliques ainda faltam para julgar cada termo. Lembre: o relatório mostra só os termos divulgados;
diga a parcela de cliques que ele cobre.

## Placar semanal (8 números)

gasto · conversões (leads/ligações/conversas) · custo por conversão · conversão→venda (planilha) ·
vendas · custo por venda · parcela de impressões · termos com desperdício.
Parcela perdida por **orçamento** ≠ perdida por **classificação**: problemas e soluções diferentes.

---
*Adaptado de `ads` (google-search-playbook.md, reading-google-ads-data.md, rsa-output-spec.md) de coreyhaines31/marketingskills (MIT), que credita Ivan Falco. Script e adaptação para venda local/ticket alto: autoria própria. Ver NOTICE.md.*
