# Proposta de Mudança: Cobertura de Testes de Integração

## 1. Identificação
- **Número da Proposta**: 15
- **Título**: Testes de Integração: Concorrência, Auto-scaling e Timeouts
- **Data de Criação**: 1 de abril de 2026
- **Autor**: GitHub Copilot
- **Status**: Aprovado — Em Implementação
- **Dependências**: Beneficia-se das Propostas 11–14, mas pode ser implementada em paralelo.

## 2. Contexto e Problema
A suite possui 25 arquivos unitários mas apenas 2 de integração. Os comportamentos de maior risco em produção não têm cobertura:
- Contenção de threads em `CommunicationManager`
- Auto-scaling por CPU/RAM em `PersistentWorkerPool`
- Restart de worker com falha
- Timeout de finalização (6 retries × 20s)
- Shutdown sob carga

## 3. Objetivo
Adicionar testes de integração que exercitem os caminhos de maior risco sem depender de browser real.

## 4. Escopo
**Incluso:**
- `tests/integration/test_pool_concurrency.py` — N workers, métricas corretas, sem race conditions
- `tests/integration/test_resource_scaling.py` — mock de psutil, valida scale up/down
- `tests/integration/test_worker_restart.py` — worker falha, pool reinicia e continua
- `tests/integration/test_shutdown_under_load.py` — shutdown com tarefas pendentes
- `tests/integration/test_finalization_retry.py` — ACK não recebido, valida retries e fallback

**Fora de escopo:**
- Testes E2E com browser real.
- Mudanças em código de produção nesta proposta.

## 5. Critérios de Aceitação
- Todos os 5 arquivos passam em `uv run pytest tests/integration/ -v`.
- Nenhum teste depende de browser, rede ou Coupa.
- Tempo total da suite de integração ≤ 60s.

## 6. Estratégia de Implementação
- Workers fake: processam tarefas sintéticas sem browser
- Mock de psutil: `patch("psutil.cpu_percent", side_effect=[...])` para scaling
- PoolConfig com `stagger_delay=0.0` e `task_timeout=5` para velocidade

## 7. Plano de Validação
- `uv run pytest tests/integration/ -v --tb=short` — todos passam.
- Executar 3 vezes seguidas; zero falhas flaky.
