# Proposta de Mudança: Correção da Fronteira Async/Sync em ProcessingSession

## 1. Identificação
- **Número da Proposta**: 12
- **Título**: Correção da Fronteira Async/Sync em ProcessingSession.stop_processing()
- **Data de Criação**: 1 de abril de 2026
- **Autor**: GitHub Copilot
- **Status**: Aprovado — Em Implementação
- **Dependências**: Nenhuma

## 2. Contexto e Problema
`ProcessingSession.stop_processing()` em `src/worker_manager.py` implementa três caminhos de execução distintos para invocar `worker_pool.shutdown()`:
1. Loop detectado como **em execução** → `ThreadPoolExecutor` + `asyncio.run()` aninhado
2. Loop existente porém **parado** → `loop.run_until_complete()`
3. **Fallback** → `asyncio.run()` direto (no bloco `except` — pode falhar com `RuntimeError` se houver loop ativo)

O terceiro caminho é especialmente problemático: o `except` genérico captura qualquer exceção do bloco try/ThreadPoolExecutor, e então tenta `asyncio.run()` diretamente. Se chamado de dentro de um contexto com loop ativo (como Textual), isso lança `RuntimeError: This event loop is already running`.

A lógica de detecção é fragmentada:
- `asyncio.get_running_loop()` → `RuntimeError` se sem loop
- `asyncio.get_event_loop()` → retorna loop mesmo que parado  
- `loop.is_running()` → pode ser True se chamado de dentro de loop

## 3. Objetivo
Simplificar para dois caminhos bem definidos usando `asyncio.get_running_loop()`:
- Se há loop rodando → executor thread (evita aninhamento)
- Se não há loop rodando → `asyncio.run()` direto (cria novo loop)

## 4. Escopo
**Incluso:**
- Refatoração do bloco de execução em `stop_processing()`.
- Remoção do `loop.run_until_complete()` como caminho intermediário (desnecessário).
- Remoção do `import concurrent.futures` inline.

**Fora de escopo:**
- Mudanças na assinatura pública de `stop_processing()`.
- Alteração da lógica de `PersistentWorkerPool.shutdown()`.

## 5. Critérios de Aceitação
- `stop_processing()` não contém `loop.is_running()` nem `asyncio.get_event_loop()` para detecção de estado.
- Shutdown completa sem `RuntimeError` em modo normal e emergencial.
- `uv run pytest tests/unit/test_persistent_pool_shutdown.py` passa.

## 6. Solução Proposta
```python
import asyncio
try:
    asyncio.get_running_loop()
    # Running inside an async context — run in a separate thread to avoid loop nesting
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, self.worker_pool.shutdown(emergency=emergency))
        future.result(timeout=15 if emergency else 60)
except RuntimeError:
    # No running loop — safe to call asyncio.run() directly
    asyncio.run(self.worker_pool.shutdown(emergency=emergency))
```

## 7. Riscos e Mitigações
- **Risco**: ThreadPoolExecutor overhead para shutdown emergencial.
  - **Mitigação**: `max_workers=1` é mínimo possível; overhead é ~1ms.
- **Risco**: `asyncio.run()` cria novo event loop após loop anterior encerrado.
  - **Mitigação**: comportamento correto e esperado para shutdown.

## 8. Plano de Validação
- `uv run pytest` completo.
- Smoke test: executar fluxo e interromper com Ctrl+C — shutdown deve completar sem `RuntimeError` nos logs.
