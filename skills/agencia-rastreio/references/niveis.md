# Rastreio: fazer a Meta aprender com quem compra

Sem devolver a venda para a Meta, ela otimiza para quem clica ou conversa, não para quem compra.

## Nível 1 — sem código (começar já)

Planilha com uma linha por contato: data, canal, anúncio de origem (se souber), produto,
status (conversa → orçamento → visita → venda), valor. Semanalmente, cruzar com o
gasto para achar o custo por venda real.

## Nível 2 — Pixel na landing page

- Criar o Pixel no Gerenciador de Eventos; o ID é público, pode ir no frontend.
- Eventos: `PageView`; `Contact` no clique em SMS/ligação/WhatsApp; `Schedule` no
  agendamento; `Lead` em formulário enviado.
- Testar com a ferramenta "Testar eventos" do Gerenciador de Eventos.

## Nível 3 — API de Conversões (servidor)

- Envia eventos do servidor (mais confiável que só o Pixel, que perde dados com
  bloqueadores e iOS).
- Para conversas por mensagem, existe a API de Conversões para mensagens comerciais:
  marca o evento (ex.: `Purchase`, `LeadSubmitted`) na conversa que virou venda.
  No WhatsApp Business, etiquetas de pedido/pagamento podem alimentar isso, dependendo
  da integração disponível na conta — verificar na documentação atual da Meta (use
  Context7/WebFetch) antes de prometer o fluxo.
- **Token de acesso fica no backend**, nunca no navegador nem no repositório
  (security-baseline). Use variável de ambiente.
- Deduplicar Pixel + servidor com o mesmo `event_id`.

## Depois de rastrear

Com ~50 vendas/leads qualificados por semana possíveis, trocar a otimização para o evento
de venda. Antes disso, usar as vendas para criar público semelhante (lookalike) de compradores.
