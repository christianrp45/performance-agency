# Configuração do runtime (Meta + LICET)

O runtime transforma as skills em ação: o agente **propõe**, um humano **autoriza no LICET** (livre e
consciente, com prova verificável no ledger público) e só então o executor **age na Meta**.

```
skills (diretor + especialistas) ──> proposta PA-AAAAMMDD-NNN  (limites do cliente checados)
                                         │
                       humano autoriza no app LICET (action/agent_id/target exatos)
                                         │
              aprovar <proposta> <intent_hash> ──> portão: GET licet.dev/v1/ledger/verify
                                         │        (authorized, não revogado, mesmo agente/alvo/ação,
                                         │         vínculo de tela VERIFIED, validade, uso único)
              executar <proposta> ──> reverifica no LICET ──> API de Marketing da Meta (v26.0)
                                         │
                                agencia/auditoria.jsonl (tudo registrado)
```

## 1. Pasta do cliente

```
<pasta do cliente>/agencia/config.json   ← copie de runtime/templates/config.example.json
<pasta do cliente>/agencia/.env          ← segredos (NUNCA em repositório)
<pasta do cliente>/agencia/propostas/    ← criada automaticamente
```

`limits.max_daily_budget_cents` é o teto que o **cliente** definiu (ex.: 1500 = US$ 15/dia). Nenhuma proposta
acima disso pode nem ser criada. `max_increase_pct` (20) impede subir mais que 20% de uma vez.

## 2. Meta (uma vez por cliente, ~20 min, feito pelo dono da conta)

1. **business.facebook.com → Configurações do negócio → Usuários → Usuários do sistema → Adicionar**
   (função *Admin*), nome `performance-agency`.
2. **Contas → Apps → Adicionar → Criar app** (tipo *Empresa/Business*) e adicione o produto
   **Marketing API**. Conecte o app ao portfólio.
3. No usuário do sistema: **Atribuir ativos** → a **conta de anúncios** (controle total) e a **Página**.
4. **Gerar token** para o app, com as permissões `ads_management`, `ads_read` e `business_management`.
5. Copie o token para `<pasta do cliente>/agencia/.env`:
   ```
   META_ACCESS_TOKEN=EAAG...
   META_APP_SECRET=...   # opcional e recomendado (assina cada chamada com appsecret_proof)
   ```
6. Em `config.json`, preencha `ad_account_id` (só os números, sem `act_`) e `page_id`.

> O token dá acesso à conta de anúncios: não cole em chat, e-mail ou código. Fica só no `.env` da pasta do cliente.

## 3. LICET

Cada proposta mostra (`pedido <proposta>`) os três campos que o humano autoriza no app LICET:
`action` (com o código da proposta e o resumo do digest dos parâmetros), `agent_id` e `target`.
Depois de autorizar, copie o **intent hash** no app e rode `aprovar`.

**Pendência no app LICET:** hoje o app autoriza ações próprias (`agent_id=licet_wear`). Para a agência, o app
precisa receber o pedido de fora — link/QR `licet://authorize?action=…&agent_id=…&target=…` — e gerar o
`action_commitment` (vínculo de tela) sobre esses campos. Até lá, o portão recusa por segurança.

## 3.1 Nível de risco: quem autoriza o quê

Nada é autônomo. Toda escrita na conta precisa de autorização humana registrada; o nível de risco decide como:

| Ação | Risco | Autorização |
|---|---|---|
| Ativar campanha/conjunto/anúncio | **libera gasto** | **só LICET** |
| Aumentar orçamento (ou orçamento atual desconhecido) | **libera gasto** | **só LICET** |
| Pausar | altera a conta | LICET **ou** confirmação digitada `CONFIRMO <id>` |
| Reduzir orçamento | altera a conta | LICET **ou** confirmação digitada |
| Lançar campanha **pausada** | altera a conta | LICET **ou** confirmação digitada |

Cada proposta mostra o **impacto em linguagem simples** (ex.: "interrompe as conversas novas", "pode deixar o conjunto
alguns dias em reaprendizado"). O nível de risco é recalculado a cada leitura — nunca confia no que está gravado no arquivo.

**Antes de executar de verdade**, o executor confere o estado atual na Meta. Se o orçamento ou o status mudou desde a
proposta, ou se o item está numa situação inesperada, a execução é recusada e é preciso uma nova proposta (nova consulta).

### Enquanto o LICET não estiver ativo para o cliente

`"spend_approval": "humano"` no `config.json` permite autorizar gasto com a frase **`AUTORIZO GASTO <id>`** e o **nome**
de quem autoriza (registrado em `auditoria.jsonl`). É uma escolha explícita e temporária do cliente; ao voltar para
`"licet"`, autorizações digitadas de gasto ainda não executadas deixam de valer.

## 3.2 Exigências do portão LICET

- Ledger **íntegro**: `GET /ledger/integrity` precisa responder `INTACT`. Se responder `TAMPERED`, nenhuma aprovação é aceita
  (falha fechada). Configurável em `require_ledger_integrity` — não desligue em produção.
- **Nível de confiança mínimo** (`min_trust_level`, padrão `L1`) para execução real. `L0` (simulador) só vale em simulação.
- `authorized`, não revogado, mesmo `agent_id`/`target`/`action`, `ui_binding_status = VERIFIED`, dentro da validade
  da proposta, com até 60 min, e uso único do `intent_hash`. Tudo reverificado no momento de executar.

## 4. Simulação e modo real

Simulação é o padrão: o executor mostra a chamada que faria, sem token e sem enviar nada.
Modo real exige **as duas coisas**: `"dry_run": false` no `config.json` **e** `AGENCY_DRY_RUN=0` no ambiente.

## 5. Comandos

```bash
cd runtime
python -m performance_agency "<pasta do cliente>" status
python -m performance_agency "<pasta do cliente>" propor-lancamento "<pasta do cliente>/agencia/lancamento.json"
python -m performance_agency "<pasta do cliente>" pedido PA-20261104-001
python -m performance_agency "<pasta do cliente>" aprovar PA-20261104-001 <intent_hash>
python -m performance_agency "<pasta do cliente>" confirmar PA-20261104-002 "CONFIRMO PA-20261104-002" "Nome de quem confirmou"
python -m performance_agency "<pasta do cliente>" executar PA-20261104-001
python -m performance_agency "<pasta do cliente>" relatorio
python -m performance_agency "<pasta do cliente>" propor-orcamento <adset_id> 15 18 "custo por conversa abaixo da meta há 2 semanas"
python -m performance_agency "<pasta do cliente>" propor-status <campaign_id> ACTIVE "aprovado o plano Essencial"
```

Testes: `python -m unittest tests/test_agency.py` (LICET e Meta simulados).

## O que o runtime NÃO faz (de propósito)

Apagar campanhas · criar anúncios com criativos (por enquanto, os anúncios são adicionados no Gerenciador dentro
do conjunto criado) · gastar acima do teto do cliente · executar sem LICET · guardar token fora do `.env`.
