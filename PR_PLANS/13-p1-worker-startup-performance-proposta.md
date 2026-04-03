# Proposta de Mudança: Performance de Startup dos Workers (P1)

## 1. Identificação
- **Número da Proposta**: 13
- **Título**: Startup Paralelo de Workers: Stagger Async + Import Lazy do Selenium
- **Data de Criação**: 1 de abril de 2026
- **Autor**: GitHub Copilot
- **Status**: Aprovado — Em Implementação
- **Dependências**: Nenhuma obrigatória.

## 2. Contexto e Problema

### 2.1 Stagger duplo bloqueia startup dos workers
`WorkerProcess._initialize_browser_session()` em `src/workers/worker_process.py` executa `time.sleep(init_delay)` (2.0–4.0 segundos por worker). O pool já possui stagger async via `persistent_pool.py` (`await asyncio.sleep(self.config.stagger_delay)`). O resultado é atraso duplo em cada worker: pool stagger + worker sleep = N × (stagger_pool + 2–4s).

### 2.2 Selenium importado no topo do módulo do worker
`src/workers/worker_process.py` importa `selenium.webdriver`, `Options` e `Service` no topo do módulo. Cada processo filho paga o custo de import (~400–600ms) ao ser spawnado, antes mesmo de saber se usará Selenium ou Playwright. Isso ocorre N vezes em paralelo, causando pico de CPU no startup.

## 3. Objetivo
- Eliminar o `time.sleep()` redundante em `WorkerProcess`.
- Tornar os imports de Selenium lazy — importados somente na função de inicialização Selenium.
- Reduzir tempo total de warm-up em N × 2–4s.

## 4. Escopo
**Incluso:**
- Remoção do `time.sleep(init_delay)` e das linhas auxiliares em `_initialize_browser_session()`.
- Refatoração dos imports de Selenium para dentro de `_initialize_selenium_driver()` (ou equivalente).

**Fora de escopo:**
- Mudanças no valor de `stagger_delay` do pool.
- Alterações na lógica de seleção de modo.

## 5. Critérios de Aceitação
- `time.sleep` não aparece na função de inicialização do browser em `WorkerProcess`.
- `from selenium import webdriver` não aparece no topo de `worker_process.py`.
- `uv run pytest` sem regressões.

## 6. Solução Proposta
Remover as linhas de stagger sleep. Mover imports de Selenium para dentro da função que cria o driver Edge:
```python
def _initialize_selenium_driver(self, ...):
    from selenium import webdriver                         # lazy
    from selenium.webdriver.edge.options import Options   # lazy
    from selenium.webdriver.edge.service import Service   # lazy
    ...
```

## 7. Riscos e Mitigações
- **Risco**: sem stagger no worker, múltiplos browsers inicializam simultaneamente.
  - **Mitigação**: o stagger do pool (`persistent_pool.py`) continua ativo e é suficiente.
- **Risco**: lazy import quebra type checkers.
  - **Mitigação**: adicionar `TYPE_CHECKING` guard para annotations de tipo se necessário.

## 8. Plano de Validação
- `uv run pytest` completo sem erros.
- Smoke test com 2 workers: stagger do pool (config) é o único atraso observado nos logs.
