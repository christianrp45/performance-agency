# Auditoria honesta de conta

## Notas
| Resultado | Significa |
|---|---|
| Passou | vi a evidência e está certa |
| Falhou | vi a evidência e está errada |
| Desconhecido | não tive a evidência |
| Não se aplica | o item não vale para a conta |

- **Saúde** = passou ÷ (passou + falhou).
- **Cobertura** = itens verificados ÷ itens aplicáveis.
- Cobertura ≥ 80% → nota válida · 60–79% → nota provisória (listar o que falta) · < 60% → sem nota, só achados.
- Plataforma sem acesso fica **fora** do total ("Meta auditada; Google não auditado — sem acesso"), nunca como zero.

## Não conta contra a saúde
Desconhecidos · recursos indisponíveis para a conta · não usar recurso novo · estar fora de um benchmark amplo.

## Recomendações seguras
- Nunca pausar só porque o custo passou de um múltiplo fixo: olhar amostra e atraso de conversão.
- Não reestruturar campanha em aprendizado por pânico.
- Não recomendar recurso sem confirmar que a conta tem acesso.
- Não inventar negativas.
- Menor mudança reversível primeiro: pausar em vez de apagar, 20% em vez de dobrar.

## Pedidos que recebem "não" com alternativa
| Pedido | Resposta |
|---|---|
| "Some as conversões da Meta e do Google" | Lado a lado, cada uma com sua janela; total pela planilha de vendas |
| "Me dê negativas para cortar desperdício" (sem relatório) | Pedir o relatório de termos; zero negativas inventadas |
| "Pause tudo acima de $X agora" | Mostrar o que essa regra teria cortado de bom e ruim; propor regra com os dados da conta |
| "Qual a nota da conta?" (com muitos buracos) | Achados + cobertura, sem número único |

## Benchmarks
Preferência: dados da própria conta (mesmo objetivo, mesma janela) → teste/holdout da conta → planilha de
vendas → pares com método claro → benchmark amplo (só direção). Dizer de onde vem e se é de fornecedor.

*Adaptado de audit-guardrails.md de coreyhaines31/marketingskills (MIT), que remixa claude-ads de Daniel Agrici (MIT).*
