# Dossiê — Worker Pool (Persistente) e Fluxo Sequencial (1 worker)

Este dossiê centraliza verificações, evidências e conclusões sobre:
- Regressões no fluxo principal sequencial (1 worker)
- Integração e comportamento do PersistentWorkerPool
- Autenticação/URLs do Coupa
- Threshold de memória (memory pressure)
- Isolamento de perfis e inicialização de WebDrivers
- Erros de event loop assíncrono em rotas de restart

O objetivo é consolidar dados para, ao final, criar um novo specify com um prompt claro e completo.

---

## 1) Contexto e objetivo

- Data: 2025-10-01
- Branch: `005-persistent-worker-pool`
- Ambiente-alvo: macOS + Python 3.12 (Poetry)
- Objetivo: identificar e delimitar regressões em “fluxo sequencial de download (1 worker)” e problemas do worker pool persistente, com passos de reprodução e evidências.

## 2) Escopo das verificações

- [ ] Fluxo sequencial (1 worker) usando o entrypoint estável (`src/Core_main.py`)
- [ ] Execução do pipeline experimental (`EXPERIMENTAL/core/main.py`) com/sem UI interativa
- [ ] URLs e autenticação Coupa (uso de `BASE_URL` e variáveis de ambiente)
- [ ] Threshold de memória e disparo de “memory pressure”
- [ ] Isolamento de perfis (Edge user-data-dir) e conflitos
- [ ] Erros de event loop ao reiniciar worker (no running event loop)

## 3) Configuração atual (preencher)

- Python: 3.12.x
- Poetry: (preencher)
- Edge / msedgedriver: (preencher versão)
- Variáveis de ambiente relevantes:
  - `COUPA_BASE_URL` = (preencher)
  - `COUPA_LOGIN_URL` = (se aplicável)
  - `MAX_PARALLEL_WORKERS` = (preencher)
  - `ENABLE_INTERACTIVE_UI` = (true/false)
- Perfil base do Edge:
  - `EDGE_PROFILE_DIR` = (preencher)
  - `EDGE_PROFILE_NAME` = (preencher)

## 4) Achados atuais (até o momento)

- URLs Coupa
  - Substituição de placeholders concluída em componentes experimentais:
    - `EXPERIMENTAL/workers/browser_session.py` e `EXPERIMENTAL/workers/worker_process.py` agora usam `COUPA_BASE_URL` (env) ou `EXPERIMENTAL.corelib.config.Config.BASE_URL` como fallback. Login pode usar `COUPA_LOGIN_URL` ou o `BASE_URL` (SSO-friendly).
  - Paths ajustados para `order_headers/{po}` (coerente com o restante do projeto).

- Network/DNS
  - Antes: `net::ERR_NAME_NOT_RESOLVED` ao usar domínio placeholder.
  - Esperado: com `COUPA_BASE_URL` real, DNS deve resolver e a página de login/SSO deve carregar.

- Threshold de memória
  - Padrão elevado de 75% → 85% (`PoolConfig.memory_threshold = 0.85`).
  - `MemoryMonitor` corrigido para comparar `usage_percent` (0–100) com `threshold * 100`, e default atualizado para 0.85.

- Isolamento de perfis
  - Conflito anterior "user data directory is already in use" aparentemente mitigado após ajustes em `ProfileManager`. Limpeza de perfis reportada no shutdown.

- Event loop (restart)
  - Ao falhar autenticação, restart do worker disparou `RuntimeError: no running event loop` (criação de tarefa async a partir de thread). Necessário marshalling para o loop principal do pool.

- Fluxo sequencial (regressão reportada)
  - Observação do autor: “o fluxo principal de download sequencial com 1 worker foi desfigurado e não funciona como deveria”.
  - Nota: o caminho sequencial do módulo experimental (`ProcessingSession._process_sequential`) está simulado (não baixa de fato). O entrypoint estável `src/Core_main.py` deve ser a referência para validar regressões do modo sequencial real.

## 5) Testes propostos e evidências

### 5.1 Sequencial — entrypoint estável (referência)

- Objetivo: confirmar se o fluxo original (1 worker, sequencial) funciona como antes.
- Passos sugeridos:

```zsh
# (Opcional) ativar venv do Poetry
# poetry shell

# Executar o entrypoint estável sequencial
poetry run python -m src.Core_main
```

- Evidências (cole aqui saída relevante do terminal/logs):

```
[cole logs aqui]
```

- Resultado/Diagnóstico:
- Ações sugeridas:

### 5.2 Experimental — execução sem UI interativa

- Objetivo: validar inicialização de workers, autenticação e uso correto de `BASE_URL`, sem prompts interativos.
- Passos sugeridos:

```zsh
# Desativar UI e limitar workers (ex.: 2)
export ENABLE_INTERACTIVE_UI=false
export MAX_PARALLEL_WORKERS=2

# Definir tenant
export COUPA_BASE_URL="https://<seu-tenant>.coupahost.com"
# (Opcional) se o SSO exigir URL específica de login
# export COUPA_LOGIN_URL="https://<seu-tenant>.coupahost.com/user/sessions/new"

poetry run python -m EXPERIMENTAL.core.main
```

- Evidências (cole aqui):

```
[cole logs aqui]
```

- Resultado/Diagnóstico:
- Ações sugeridas:

### 5.3 Memory pressure — validação do threshold 85%

- Objetivo: verificar se o threshold em logs aparece como `85.0` e só dispara acima de 85%.
- Observável esperado: `threshold_percent=85.0` nas mensagens de warning de memory pressure.

- Evidências:

```
[cole logs aqui]
```

### 5.4 Restart de worker — event loop

- Objetivo: reproduzir `RuntimeError: no running event loop` ao falhar autenticação e registrar stacktrace completo.
- Evidências:

```
[cole stacktrace aqui]
```

- Ação técnica prevista: mover a criação de tarefas de restart para o loop do pool (usar `asyncio.run_coroutine_threadsafe` com referência ao loop principal, ou fila de comandos thread-safe processada por uma task do loop).

### 5.5 Isolamento de perfis — múltiplos workers

- Objetivo: garantir criação de perfis temporários únicos e limpeza no shutdown.
- Evidências:

```
[cole logs/paths de perfis aqui]
```

## 6) Hipóteses e ações recomendadas (em aberto)

- [ ] Corrigir restart assíncrono: encapsular reinício do worker no loop do pool (evitar `create_task` fora do loop).
- [ ] Confirmar que o fluxo sequencial de referência (`src/Core_main.py`) segue intacto; se houver divergências, alinhar com o comportamento original (download, renomeio de pastas, atualização do Excel, etc.).
- [ ] Adicionar caminho “não interativo” robusto ao experimental para evitar prompts em execuções automatizadas.
- [ ] Verificar tratamento de erro de autenticação (timeout, DNS, SSO) com backoff/retry apropriado.

## 7) Itens para o specify (rascunho)

Quando os testes acima estiverem documentados, vamos consolidar em um specify. Estrutura proposta do prompt (rascunho):

```
Contexto:
- Projeto CoupaDownloads; macOS + Python 3.12; Selenium Edge; Poetry.
- Regressões no fluxo sequencial (1 worker) e problemas no worker pool persistente.

Problema:
- [Descrever o comportamento atual] (inclua logs resumidos)

Comportamento esperado:
- [Descrever o comportamento correto do fluxo sequencial e do worker pool]

Escopo e critérios de aceitação:
- [Lista objetiva de critérios: ex. download, renomeio de pastas, atualização de planilha, autenticação SSO, etc.]

Passos de reprodução:
- [Comandos e condições do ambiente]

Telemetria e logs:
- [Resumos + anexos referenciados neste dossiê]

Riscos/Restrições:
- [SSO, rede corporativa, limitação de headless, etc.]

Entregáveis:
- Código + testes + docs; validação manual guiada; evidências em `docs/reports/`.
```

Quando tivermos os dados preenchidos, eu preparo uma versão final do prompt para o comando `specify` com todo o contexto necessário.

---

## 8) Anexos e referências

- Arquivos alterados relevantes:
  - `EXPERIMENTAL/workers/browser_session.py` — base/login URL configuráveis; paths `order_headers`.
  - `EXPERIMENTAL/workers/worker_process.py` — base URL configurável; path `order_headers`.
  - `EXPERIMENTAL/workers/models/config.py` — `memory_threshold` padrão 0.85.
  - `EXPERIMENTAL/workers/memory_monitor.py` — comparação corrigida e default 0.85.
- Entrypoints:
  - Estável: `src/Core_main.py` (fluxo sequencial referência)
  - Experimental: `EXPERIMENTAL/core/main.py`

> Use este arquivo para colar logs, prints e comentários livres. Com isso, vamos consolidar e gerar o specify.
