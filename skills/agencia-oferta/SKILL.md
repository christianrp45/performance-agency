---
name: agencia-oferta
description: Especialista em oferta e viabilidade da agência de performance. Monta ou conserta a oferta (o que se vende, bônus, garantia, urgência verdadeira, nome, preço e parcelamento) e calcula quanto dá para pagar por venda a partir de preço, margem e frete. Use quando o pedido falar de oferta, preço de lançamento, promoção, desconto, parcelamento/financiamento, garantia, escassez, "por que não converte", "quanto posso gastar por venda", teto de CPA/CAC, ROAS de equilíbrio ou orçamento de teste. Parte da suíte agencia-*.
---

# Oferta e viabilidade

A oferta é o produto que o cliente realmente compra. Texto melhor em oferta fraca rende pouco;
oferta forte com texto médio converte já. Siga as regras da casa da skill `agencia`.

## 1. Viabilidade primeiro (sem ela, não há orçamento)

Rode `scripts/viabilidade.py` (pasta da skill `agencia`):

```bash
python viabilidade.py --preco 6600 --margem 0.40 --frete 0 --fechamento 0.02,0.04 --custo-conversa 15,25
```

| Conta | Fórmula |
|---|---|
| Lucro bruto por venda | preço × margem − frete (se o frete não está na margem) |
| Teto de custo por venda | ≈ 35–40% do lucro bruto (sobra lucro e absorve erro) |
| Custo máximo por conversa/lead | teto × taxa de fechamento |
| ROAS de equilíbrio | 1 ÷ margem (líquida de frete) |
| Orçamento de validação | (vendas desejadas ÷ fechamento) × custo por conversa, num só conjunto, 3–4 semanas |

Mostre sempre 2 cenários (conservador e otimista) e diga as premissas. Taxa de fechamento real
substitui a estimativa assim que existir.

## 2. A equação de valor (onde a oferta está fraca)

Valor percebido = **resultado desejado × chance percebida de conseguir** ÷ **tempo até o resultado × esforço/risco**.
Dê nota 1–10 a cada alavanca; a menor é o gargalo. "Baixe o preço" quase sempre é "aumente a
chance percebida" (prova, garantia) ou "diminua o esforço" (entrega, montagem, parcelamento).

## 3. Os seis componentes de uma oferta completa

| # | Componente | Pergunta | Produto caro / físico |
|---|---|---|---|
| 1 | Entrega principal | O que leva? | Especificação real: medida, material, prazo |
| 2 | Bônus | O que mais vem junto? | Entrega e montagem, cuidado/manutenção, peça complementar |
| 3 | Garantia | E se der errado? | Garantia por escrito, política de devolução clara |
| 4 | Urgência / escassez | Por que agora? | Peça única é escassez real; preço de lançamento com data de fim |
| 5 | Nome | Como se chama? | "Launch price", "Grand opening price", "Introductory price" |
| 6 | Preço e pagamento | Quanto e como? | **Parcelamento** ("as low as $X/month": Affirm, Klarna; no Brasil, parcelas no cartão) |

Para ticket alto, parcelamento e garantia costumam mover mais que qualquer desconto.

## 4. Ciclo de diagnóstico

1. Escreva a oferta atual em linguagem simples (nome, preço, o que leva, garantia, prazo).
2. Dê nota às 4 alavancas; ache a menor.
3. Veja qual dos 6 componentes falta.
4. Mude **um** componente por vez e teste.
5. Projete com honestidade: cada mudança rende ~10–40% relativos, e os efeitos multiplicam,
   não somam. Quem promete 5x está vendendo algo.

## 5. O que não fazer

- Escassez falsa (contador que reinicia, "só 3 vagas" mentiroso).
- "Preço normal" riscado que nunca foi praticado.
- Garantia exagerada que a margem não aguenta.
- Desconto para conquistar cliente novo (ancora o produto como barato).
- Palavras vazias: "revolucionário", "game-changing", "segredo", "100% garantido" sem condição.
  Use números, medidas e prazos reais.

## Entregável

Bloco de oferta pronto para anúncio e página (nome, preço, pagamento, garantia, urgência real,
bônus) + tabela de viabilidade + premissas + MISSING. Salvar na pasta do cliente e atualizar a ficha.

---
*Adaptado e reescrito a partir de `offers` e `ads/payback-period` de coreyhaines31/marketingskills (MIT). Equação de valor originalmente de Alex Hormozi. Ver NOTICE.md.*
