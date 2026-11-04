---
name: agencia-meta-ads
description: Gestor de tráfego da Meta (Facebook, Instagram, Messenger, WhatsApp) da agência de performance. Diagnostica exportações CSV do Gerenciador de Anúncios, desenha estrutura de campanha, escolhe objetivo e destino (mensagens, formulário, site), monta o passo a passo campo a campo, define quando pausar, manter, trocar ou escalar cada anúncio e cuida da fadiga de criativo. Use quando o pedido mencionar Meta Ads, Facebook Ads, Instagram Ads, Gerenciador de Anúncios, impulsionar, anúncio de WhatsApp/click-to-WhatsApp, conjunto de anúncios, público, Advantage+, fase de aprendizado, frequência, CPM, custo por conversa, CSV de campanhas da Meta ou "onde errei nos anúncios". Parte da suíte agencia-*.
---

# Meta Ads

Regras da casa: skill `agencia`. Viabilidade (teto de custo por venda): `agencia-oferta`.

## Diagnóstico de CSV

```bash
python scripts/analisar_meta_csv.py "<pasta do cliente>/dados/<arquivo>.csv" --preco 6600 --margem 0.40
```
Lê cabeçalhos em PT ou EN, ignora a linha de total, agrupa por objetivo e gera alertas (sem venda
medida, aprendizado travado, criativo duplicado, impulsionamento, campanhas esquecidas, frequência).
Interprete com [references/diagnostico.md](references/diagnostico.md): o script aponta sintomas,
você explica causa e ação, em ordem de quanto dinheiro cada problema custa.

## Estrutura que vende (padrão)

- **Uma campanha, 1–2 conjuntos, 3–4 criativos competindo.** Mais conjuntos só quando um deles
  estiver abaixo do teto e houver verba para outro sair do aprendizado.
- **Criar pelo Gerenciador**, nunca pelo "Impulsionar".
- **Público amplo, criativo específico.** Desde o Andromeda (2025) o algoritmo segmenta pelo
  criativo: o conhecimento do público vai ~80% para o texto/visual e ~20% para filtros. Empilhar
  interesses atrapalha.
- **Conjunto quente separado e pequeno** (quem interagiu com IG/FB em 365 dias, visitou o site,
  viu 50% do vídeo), com expansão de público desligada.
- Detalhes, objetivo por fase e segmentação: [references/estrutura.md](references/estrutura.md).

## Objetivo e destino

| Situação | Objetivo → destino |
|---|---|
| Venda consultiva, produto caro, sem Pixel com vendas | Engajamento → **Apps de mensagens** (destinos combinados quando o público não é dominado por um app) |
| Ponto físico | Leads → formulário de **maior intenção** para agendar visita |
| Site com evento de compra/lead medido | Vendas/Leads com Pixel + API de Conversões |
| Retargeting | Mesmo objetivo, oferta **diferente** (objeção, prova, outra peça) |

Qual app de mensagem usar depende do país: [references/canais-por-pais.md](references/canais-por-pais.md).
A Meta não tem SMS como destino; SMS entra pela landing page e pelo atendimento.

## Decisões (pausar, manter, trocar, escalar)

Ancore tudo num número: **CVA = custo-alvo por venda** (ou por conversa/lead qualificado = teto ×
fechamento). Regras completas em [references/decisao.md](references/decisao.md). Resumo:

- **Teto de anúncios ativos** = (orçamento diário × 14) ÷ (2 × custo-alvo por conversa). Acima disso nenhum anúncio recebe verba suficiente para ser julgado.
- **Dia 7, entrega:** anúncio que a Meta quase não serviu (menos da metade da fatia justa) → trocar o gancho/visual.
- **Julgamento:** só depois de gastar **3×** o custo-alvo. Zero resultado nesse ponto → abandonar o conceito.
- **Qualidade:** conversa que não vira proposta/visita é sinal de público errado → mudar ângulo e filtro no texto (preço, região).
- **Fadiga:** frequência > 2,5 (frio) ou CTR −20% em 7 dias ou CPM +30% em 2 semanas → preparar substituto.
- **Escala:** +20% a cada 3–5 dias, só com custo por venda ≤ teto por 2 semanas e 2–3 criativos de reserva. Nunca +30% de uma vez.
- **Nunca editar** um anúncio que está performando (reinicia o aprendizado): crie um novo ao lado.
- **Nenhuma regra fixa de pausa** sem olhar tamanho de amostra e atraso de conversão.

## Passo a passo para o cliente

Entregue um arquivo `passo-a-passo-meta.md` na pasta do cliente, campo a campo: antes de começar
(contas ligadas à Página: Instagram, WhatsApp Business; forma de pagamento; atendimento combinado),
campanha, conjuntos, cada anúncio (arquivo por posicionamento, texto principal, título, descrição,
CTA, modelo de mensagem com saudação e perguntas prontas), desligar melhorias automáticas que
alteram texto ou cortam preço, revisão e teste no celular, e as regras dos primeiros 7 dias.
Avise que os nomes dos menus da Meta mudam e que vale a opção equivalente.

## Erros que custam mais

Orçamento pulverizado em muitos conjuntos · mesmo post impulsionado várias vezes · sem preço no
anúncio de produto caro · otimizar para clique/visita ao perfil · campanha esquecida ativa ·
mexer em público e orçamento no mesmo dia · julgar antes de 3 dias.

---
*Sistema de decisão e práticas Andromeda adaptados de `ads` (references/meta-decision-system.md e meta-andromeda-playbook.md) de coreyhaines31/marketingskills (MIT), que credita Ivan Falco. Diagnóstico, canais por país e objetivos por fase: autoria própria. Ver NOTICE.md.*
