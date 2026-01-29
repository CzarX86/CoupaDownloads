# Documento de Design: Refatoração - Quebrar main.py em Módulos Menores

## 1. Visão Geral
Este documento detalha o design para a Proposta 03: refatorar `src/main.py` de um arquivo monolítico (~2000 linhas) em módulos menores e coesos. O foco é extrair responsabilidades para classes dedicadas, mantendo compatibilidade e facilitando futuras implementações (ex.: Propostas 01/02).

## 2. Arquitetura Atual
- **Estrutura**: Funções globais (ex.: `process_po_worker`, `_interactive_setup`) e classe `MainApp` sobrecarregada.
- **Problemas**: Mistura de setup, processamento, UI e CSV; difícil testar e manter.
- **Componentes Principais**:
  - Funções globais: Setup, workers, helpers.
  - `MainApp`: Processamento, UI (Rich), CSV, orquestração.
  - Dependências: Selenium, Rich, CSV handlers.

## 3. Arquitetura Proposta
- **Módulos Novos**:
  - `src/setup_manager.py`: Classe `SetupManager` para configuração interativa/não-interativa.
  - `src/worker_manager.py`: Classe `WorkerManager` para lógica de workers e processamento paralelo.
  - `src/ui_controller.py`: Classe `UIController` para componentes Rich e display.
  - `src/processing_controller.py`: Classe `ProcessingController` para orquestração de processamento.
  - `src/csv_manager.py`: Classe `CSVManager` para handlers de CSV.
- **Refatoração de MainApp**: Quebrar em `AppRunner` (entrypoint) que compõe os managers/controllers.
- **Princípios**: Composição, responsabilidade única, compatibilidade backward.

## 4. Componentes e Interfaces
- **SetupManager**:
  - Métodos: `interactive_setup()`, `apply_env_overrides()`, `scan_local_drivers()`.
  - Entrada: Configs de ambiente.
  - Saída: Sessão de setup com prefs headless e paths.
- **WorkerManager**:
  - Métodos: `process_po_worker()`, `wait_for_downloads()`, `derive_status()`.
  - Interface: Recebe lista de POs, retorna resultados.
- **UIController**:
  - Métodos: `build_progress_table()`, `update_header()`, `start_live_display()`.
  - Usa Rich para renderização; injetado em AppRunner.
- **ProcessingController**:
  - Métodos: `process_po_entries()`, `initialize_csv_handler()`.
  - Orquestra workers e UI.
- **CSVManager**:
  - Métodos: `build_csv_updates()`, `shutdown_handler()`.
  - Gerencia backup e write queue.
- **AppRunner** (novo, substitui MainApp):
  - Compõe todos os managers; mantém `run()` e `close()`.

## 5. Fluxo de Dados
1. `main()` chama `AppRunner.run()`.
2. `AppRunner` usa `SetupManager` para config.
3. `ProcessingController` lê POs e delega para `WorkerManager`.
4. `UIController` atualiza display em tempo real.
5. `CSVManager` persiste resultados.
6. Cleanup via `close()`.

## 6. Considerações de Segurança
- Manter isolamento de processos/workers.
- Não expor credenciais em logs/UI.
- Validar paths para evitar injeção.

## 7. Plano de Implementação (Fases Detalhadas)
Ver seção 7 da Proposta 03 para faseamento incremental.

## 8. Testes e Validação
- **Unit Tests**: Testar cada manager isoladamente (ex.: SetupManager com mocks).
- **Integration Tests**: Executar fluxo completo; validar UI, CSV e processamento.
- **Benchmarks**: Medir performance antes/depois.

## 9. Riscos e Mitigações
- **Quebra de Estado Global**: Usar injeção de dependência.
- **Regressões**: Testes abrangentes por fase.

## 10. Métricas de Sucesso
- Redução de linhas em `main.py` >80%.
- Cobertura de testes >90%.
- Tempo de build/teste inalterado.