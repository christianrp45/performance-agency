# Como interpretar o diagnóstico

O script aponta sintomas. Antes de entregar, transforme em achados com **causa → efeito → ação**,
ordenados pelo que mais custa dinheiro.

## Ordem de prioridade

1. **Venda não medida.** Sem isso, todo o resto é palpite. Ação: rastreio (a skill `agency-tracking`)
   ou, no mínimo, planilha simples de "conversa → orçamento → venda" com a data.
2. **Orçamento pulverizado / fase de aprendizado.** A Meta precisa de ~50 eventos de
   otimização por semana em cada conjunto. Conjunto com R$/US$ 10/dia otimizando para
   conversa de $15 nunca aprende. Ação: um conjunto, orçamento concentrado.
3. **Criativo duplicado em vários conjuntos.** Os conjuntos disputam o mesmo leilão e o mesmo
   público. Diferença grande de custo para o mesmo criativo = cansaço ou sobreposição.
4. **Impulsionar post.** Pouco controle; trocar por campanha criada no Gerenciador.
5. **Objetivo errado para a fase.** Clique no link e visita ao perfil são baratos e não
   indicam compra. Para produto caro, otimizar para conversa, lead ou compra.
6. **Campanhas esquecidas ativas** e conjuntos sem entrega.

## Leitura das métricas

| Métrica | O que diz | Sinal de alerta |
|---|---|---|
| CPM | preço do leilão para aquele público/objetivo | sobe semana a semana com o mesmo público |
| Taxa resultado/impressão | quanto o criativo convence | cai enquanto a frequência sobe |
| Frequência (impr./alcance) | quantas vezes a mesma pessoa viu | > 3 em público frio |
| Custo por resultado | eficiência do objetivo escolhido | acima do teto de viabilidade |
| Custo por venda | o único que paga as contas | acima do teto 2 semanas seguidas |

CPM mais alto em campanha de mensagem do que em clique é normal: a Meta cobra mais
para entregar a quem tende a conversar. Compare custo **por venda**, não CPM.

## O que o CSV padrão não traz

Data por dia, posicionamento, idade/sexo, criativo individual. Para isso, peça ao usuário
exportação com **detalhamento por dia** e **por anúncio**, ou leitura pela API de Marketing
(token só de leitura, guardado no backend).

## Formato da entrega

- Começar pelo número que importa (gasto total, o que voltou).
- Tabela "para onde foi o dinheiro" por objetivo.
- 4–6 achados numerados por prioridade, cada um com a ação.
- O que funcionou (criativos com melhor taxa) — para reaproveitar.
- Perguntas que faltam (preço, margem, quantas conversas viraram venda).
