---
name: agency-tracking
description: 'Especialista em medição da agência de performance. Garante que cada venda seja contada e devolvida às plataformas: planilha de vendas, Pixel da Meta, API de Conversões (inclusive para conversas no WhatsApp/Messenger), tag do Google Ads e GA4, importação de conversões offline (GCLID), UTMs e deduplicação. Use quando o pedido falar de Pixel, CAPI, API de Conversões, tag do Google, GA4, GTM, UTM, conversão offline, "não sei de onde vieram as vendas", atribuição, ou quando um diagnóstico mostrar que a conta não mede venda. Parte da suíte agency-*.'
---

# Rastreio: medir venda, não clique

Regras da casa: skill `agency` (inclusive: **token de API nunca no frontend**; IDs de Pixel e de tag
podem ir na página).

Sem devolver a venda para a plataforma, ela otimiza para quem clica ou conversa, não para quem compra.
Comece pelo nível mais simples que já mede venda e suba de nível. Detalhes de cada nível:
[references/niveis.md](references/niveis.md).

## Os níveis

| Nível | O que é | Quando |
|---|---|---|
| 1. Planilha de vendas | Uma linha por contato: data, canal, origem/anúncio, produto, etapa, valor | **Sempre**, desde o 1º dia (modelo em `agency/templates/planilha-vendas.csv`) |
| 2. Pixel + tag na página | Pixel da Meta e tag do Google (gtag) com eventos de contato | Quando houver landing page |
| 3. Servidor | API de Conversões da Meta; conversões offline/aprimoradas do Google | Quando a venda acontece fora do site (WhatsApp, telefone, loja) |
| 4. Otimizar por venda | Plataformas otimizando o evento de venda/lead qualificado | Com volume (~50/semana na Meta; ~30/mês por campanha no Google) |

## Eventos padrão na landing page

| Ação | Meta (Pixel) | Google (gtag/GA4) |
|---|---|---|
| Página vista | `PageView` | `page_view` |
| Clique em WhatsApp / SMS / ligar | `Contact` | conversão "contato" (`generate_lead` ou evento próprio) |
| Agendou visita | `Schedule` | conversão "agendamento" |
| Formulário enviado | `Lead` | `generate_lead` |
| Venda (vinda da planilha/CRM) | `Purchase` com `value` e `currency` via CAPI | conversão offline com valor |

Use o **mesmo `event_id`** no navegador e no servidor para a Meta deduplicar.

## UTMs (padrão da agência)

`utm_source` = meta | google · `utm_medium` = paid_social | cpc · `utm_campaign` = nome da campanha
(igual ao do gerenciador) · `utm_content` = anúncio (`{{ad.name}}` na Meta) · `utm_term` = palavra-chave
(`{keyword}` no Google). Ative também o **auto-tagging** do Google (GCLID).

## Venda que acontece na conversa

- **Meta:** API de Conversões para mensagens comerciais — marcar na conversa quando vira lead
  qualificado e venda. Verifique na documentação atual da Meta (Context7/WebFetch) o fluxo disponível
  para a conta antes de prometer.
- **Google:** guardar o GCLID quando o contato vem da landing page (campo oculto ou parâmetro levado
  para a mensagem) e importar a venda com valor.
- **Mínimo viável:** perguntar e anotar "como nos encontrou?" e o anúncio, na planilha.

## Teste antes de lançar

- [ ] Ferramenta "Testar eventos" da Meta mostra os eventos do site.
- [ ] Assistente de tag do Google / modo debug do GA4 mostra as conversões.
- [ ] Um clique real em cada botão gerou o evento uma vez (sem duplicar).
- [ ] UTMs chegam na URL e no relatório.
- [ ] Banner de consentimento (quando exigido) não bloqueia a tag antes do aceite de forma errada.

## Nunca

Somar conversões da Meta (7 dias clique/1 dia visualização) com as do Google (30 dias) — reportar lado
a lado e usar a planilha como fonte neutra. Colar token de acesso em código de página ou repositório.

---
*Inspirado em `conversion-tracking` de coreyhaines31/marketingskills (MIT); níveis e fluxo de vendas por mensagem: autoria própria. Ver NOTICE.md.*
