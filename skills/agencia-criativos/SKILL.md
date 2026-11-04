---
name: agencia-criativos
description: Diretor de criação da agência de performance. Cria e itera criativos de anúncio (ganchos, textos, imagens estáticas, carrosséis, vídeos curtos) para Meta, Google (RSA, PMax, YouTube) e outros canais, a partir do comprador real e da oferta; organiza a matriz de ganchos, os formatos e tamanhos por posicionamento, diagnostica por que um anúncio não performa e garante identidade visual sem "cara de IA". Use quando o pedido falar de criativo, anúncio, arte, vídeo para anúncio, Reels/Stories, carrossel, gancho, headline, copy de anúncio, variações para teste, fadiga de criativo ou "o anúncio não converte". Parte da suíte agencia-*.
---

# Criativos que vendem

Regras da casa: skill `agencia`. Oferta: `agencia-oferta`. Identidade visual: ficha do cliente
(e a skill `design-sem-cara-de-ia`, se instalada).

## Princípios

1. **O criativo é a segmentação.** Na Meta e no PMax o algoritmo entrega cada criativo para quem
   se parece com ele. Cinco criativos para cinco segmentos > um criativo com cinco filtros.
2. **Ancorado no comprador real.** Ganchos saem de palavras de clientes (conversas, avaliações,
   comentários), não de "voz de marketing". Nada inventado: depoimento, número, material, prazo.
3. **Diversidade de conceito > variações de texto.** Dez ganchos para dez combinações
   segmento × motivação valem mais que trinta reescritas do mesmo.
4. **Preço e região no criativo de produto caro.** Filtra curioso e baixa o custo por venda.
5. **Fotos e vídeos do próprio produto.** Foto de terceiro ou gerada por IA (marca d'água ✦ do Gemini)
   é risco de confiança e de política de anúncio.
6. **Identidade do cliente, não modelo genérico.** Nada de fundo quase preto com degradê e acento
   neon, nem de "template de IA". Use cores, fontes e frase da marca da ficha.

## A matriz de ganchos

`Segmento → Motivação (palavras do cliente) → Formato → Gancho (3 partes)`

| # | Segmento | Motivação (fonte) | Formato | Visual 0–3 s | Fala/primeira linha | Legenda na tela |
|---|---|---|---|---|---|---|

No vídeo, o gancho são três partes ao mesmo tempo — o que acontece na tela, a primeira frase e o
texto na tela — e elas **se completam, não se repetem**. Em imagem estática: visual + título, e o
título não descreve a imagem. Movimentos de abertura e diagnóstico: [references/ganchos.md](references/ganchos.md).

## Escada de produção

- **Hipótese → baixa fidelidade, em 1–2 dias:** estático, texto na tela, narração sobre imagens.
- **Ângulo validado → alta fidelidade:** filmagem, criador, demonstração.
Nunca gastar produção cara em ângulo não testado.

## Hierarquia de teste

1. Conceito/ângulo (maior impacto) → 2. gancho/título → 3. estilo visual → 4. texto → 5. CTA.
Mudar **uma** coisa por ciclo.

## Formatos e medidas

| Posicionamento | Formato | Medida |
|---|---|---|
| Feed Meta | 4:5 | 1080×1350 |
| Stories/Reels | 9:16 (zona segura: 250 px em cima, 300 px embaixo) | 1080×1920 |
| Carrossel | 1:1 ou 4:5, 2–10 cards, último card = oferta | 1080×1080 |
| Google PMax/Demand Gen | 1,91:1, 1:1, 4:5 + logo + vídeo próprio | 1200×628, 1200×1200 |
| YouTube Shorts | 9:16 | 1080×1920 |

Vídeo de 15–30 s: gancho (0–3 s) → problema/desejo (3–8) → produto e prova (8–20) → CTA. Sempre com
legenda (a maioria assiste sem som). Música só da biblioteca da plataforma.
Mais detalhes: [references/formatos.md](references/formatos.md).

## Diagnóstico de anúncio fraco

| Etapa | Métrica | Se está fraca, o problema é | Corrigir |
|---|---|---|---|
| Parar | 3 s / thumbstop | visual de abertura | novo visual, resto igual |
| Ficar | retenção 3→15 s | o que vem depois do gancho | refazer os segundos 3–15 |
| Clicar | CTR | promessa/oferta pouco clara | prova, preço, CTA |
| Converter | conversão pós-clique | página não continua o anúncio | `agencia-landing` |

Gancho que prende mas atrai a pessoa errada aparece como thumbstop alto e conversão baixa.

## Texto de anúncio

- Primeira linha = gancho (até ~125 caracteres antes do "ver mais" na Meta).
- Fórmulas: Problema → agitação → solução; Antes → depois → ponte; Prova primeiro.
- Específico > superlativo: medida, preço, prazo, cidade.
- Google RSA: limites e mistura de títulos em `agencia-google-ads/references/rsa.md`.
- Para PT-BR, revisar com `humanizer-pt-br`; para EN, cortar clichês ("unlock", "elevate", "game-changing").

## Entregável

Na pasta do cliente (`criativos/`): arquivos nomeados por anúncio e formato
(`<marca>-<anuncio>-<formato>.jpg/mp4`), a matriz de ganchos usada, os textos por anúncio e, se as
peças forem geradas por script, o script junto (para refazer quando a oferta mudar).

---
*Sistema de ganchos e escada de produção adaptados de `ad-creative` (hook-system.md) de coreyhaines31/marketingskills (MIT). Ver NOTICE.md.*
