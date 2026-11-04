# Especificação de entrega de RSA (anúncio responsivo de pesquisa)

Nenhum RSA sai fora destes limites. Confira com `scripts/checar_rsa.py` antes de entregar.

## Limites por RSA

- **Títulos:** 15, cada um com **até 30 caracteres** (espaços contam). Mostrar `1. texto (NN)`.
- **Descrições:** 4, cada uma com **até 90 caracteres**.
- **Caminhos:** até 2, cada um com **até 15 caracteres**.
- **URL final** com https.
- **Fixação (pin):** só quando necessário e dita explicitamente. Fixar reduz combinações.
- Máximo de **3 RSAs por grupo de anúncios**.

## Ordem da entrega (o que mais importa primeiro, para não se perder se o texto for longo)

1. **Estrutura de grupos:** tema, palavras-chave com tipo de correspondência, quais RSAs.
2. **Negativas:** em conta nova, só genéricas de lançamento (≥ 8), marcadas
   *"lançamento — revisar com o relatório de termos de pesquisa em 7 dias"*. Em conta rodando,
   só a partir do relatório real.
3. **Sitelinks** (≥ 4): título ≤ 25, duas linhas ≤ 35, URL.
4. **Frases de destaque** (≥ 4, ≤ 25 cada).
5. **Snippets estruturados**, se fizerem sentido (Tipos, Modelos, Serviços).
6. **RSAs.**

## Como escrever bons títulos

Misture, entre os 15:
- 3–4 com a **palavra-chave** do grupo (relevância e índice de qualidade);
- 2–3 com **preço/oferta** ("$6,600 Launch Price", "Free Delivery in Dallas");
- 2–3 com **diferencial concreto** ("Carved From One Tree", "7 to 12 ft, One Price");
- 2 com **prova/confiança** ("Showroom in Dallas, TX", avaliações reais se houver);
- 2 com **chamada para ação** ("Text Us for Photos", "Get a Quote Today");
- 1–2 com **região** ("Waterfall Tables in Texas").
Sem repetir a mesma ideia com outras palavras. Sem "#1", "best", "guaranteed" sem prova.

Descrições: uma com oferta completa, uma com diferencial + prova, uma com processo (como comprar),
uma com objeção respondida (entrega, garantia, parcelamento) — só com fatos confirmados.

## Modelo

```
Estrutura de grupos:
- GA1 [tema]: "palavra" (frase), [palavra] (exata) → RSA1, RSA2

Negativas (lançamento — revisar em 7 dias):
  Campanha: - ...
  Grupo GA1: - ...

Sitelinks:
  - Título | linha 1 | linha 2 | URL

Frases de destaque:
  - ...

RSA1 — GA1
  URL final: https://...
  Caminho 1: ...  Caminho 2: ...
  Títulos (15, ≤30):
    1. ... (NN)
  Descrições (4, ≤90):
    1. ... (NN)
  Fixação: nenhuma
```

## Conferência antes de enviar

- [ ] 15 títulos e 4 descrições por RSA, todos dentro do limite (rodar o script).
- [ ] Negativas rotuladas como de lançamento ou vindas do relatório.
- [ ] Nada de afirmação que o cliente não confirmou.
- [ ] Idioma do público do anúncio.

*Adaptado de rsa-output-spec.md de coreyhaines31/marketingskills (MIT).*
