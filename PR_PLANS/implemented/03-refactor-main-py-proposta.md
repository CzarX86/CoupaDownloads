# Proposta de Mudança: Refatoração - Quebrar main.py em Módulos Menores

## 1. Identificação
- **Número da Proposta**: 03
- **Título**: Refatoração - Quebrar main.py em Módulos Menores
- **Data de Criação**: 28 de janeiro de 2026
- **Autor**: GitHub Copilot (baseado em consulta do usuário)
- **Status**: Em Revisão
- **Dependências**: Pré-requisito para Propostas 01 e 02 (implementar após aprovação).

## 2. Contexto e Problema
O arquivo `src/main.py` é monolítico (~2000+ linhas), com funções globais longas (ex.: `process_po_worker`, `_interactive_setup`) e uma classe `MainApp` sobrecarregada com métodos extensos. Isso dificulta manutenção, testes e implementação de novas features como as Propostas 01/02.

Problemas:
- Funções globais misturam lógica de setup, processamento e UI.
- `MainApp` tem responsabilidades múltiplas (config, processamento, UI, CSV).
- Alto risco de bugs durante mudanças.

## 3. Objetivo
Refatorar `main.py` em módulos menores e coesos:
- Extrair funções globais para classes/módulos dedicados (ex.: `SetupManager` para config, `WorkerManager` para processamento).
- Quebrar `MainApp` em subclasses ou módulos (ex.: `UIController` para Rich UI, `CSVManager` para handlers).
- Manter compatibilidade com código existente; usar composição em vez de herança.

Benefícios:
- Código mais legível e testável.
- Facilita implementação de 01/02 sem conflitos.
- Redução de complexidade ciclomática.

## 4. Escopo
- **In Scope**:
  - Extrair `_interactive_setup`, `_apply_env_overrides` para `SetupManager`.
  - Mover lógica de workers para `WorkerManager`.
  - Separar UI (Rich components) para `UIController`.
  - Quebrar `MainApp` em `ProcessingController` e `AppRunner`.
  - Manter entrypoint `main()` intacto.
- **Out of Scope**:
  - Mudanças em bibliotecas externas.
  - Alterações em `process_po_worker` (deixar para 01/02).

## 5. Critérios de Aceitação
- `main.py` reduzido para <500 linhas, com imports claros.
- Todos os testes existentes passam.
- Funcionalidade idêntica (setup, processamento, UI).
- Novo código segue PEP 8 e type hints.

## 6. Riscos e Mitigações
- **Risco**: Quebrar imports/compatibilidade.
  - **Mitigação**: Usar aliases e testes de integração.
- **Risco**: Overhead de refatoração.
  - **Mitigação**: Fazer em commits pequenos; validar incrementalmente.

## 7. Plano de Implementação
### Faseamento em Grupos Incrementais
A refatoração será dividida em fases pequenas para minimizar riscos, com testes entre cada grupo. Cada fase visa extrair responsabilidades específicas sem quebrar funcionalidade.

#### Fase 1: Extração de Setup e Configuração (1-2 dias)
- **Mudanças**:
  - Criar `src/setup_manager.py` com classe `SetupManager`.
  - Mover `_interactive_setup()`, `_apply_env_overrides()` e `_scan_local_drivers()` para `SetupManager`.
  - Atualizar imports em `main.py`.
- **Testes**: Executar setup interativo e não-interativo; validar configs aplicadas.
- **Critério**: Setup funciona sem erros; `main.py` reduzido em ~200 linhas.

#### Fase 2: Extração de Lógica de Workers e Processamento (2-3 dias)
- **Mudanças**:
  - Criar `src/worker_manager.py` com classe `WorkerManager`.
  - Mover `process_po_worker()`, helpers de download (ex.: `_wait_for_downloads_complete()`) e funções de status para `WorkerManager`.
  - Refatorar `MainApp._process_po_entries()` para usar `WorkerManager`.
- **Testes**: Processar lote pequeno de POs; validar isolamento e downloads.
- **Critério**: Processamento paralelo/sequencial intacto; sem vazamentos de estado.

#### Fase 3: Separação de UI e Componentes Rich (1-2 dias)
- **Mudanças**:
  - Criar `src/ui_controller.py` com classe `UIController`.
  - Mover métodos de UI (ex.: `_build_progress_table()`, `_update_header()`, `Live` logic) para `UIController`.
  - Injetar `UIController` em `MainApp`.
- **Testes**: Executar UI com progresso; validar display em console.
- **Critério**: UI responde corretamente; sem erros de renderização.

#### Fase 4: Quebra de MainApp e Integração Final (2-3 dias)
- **Mudanças**:
  - Criar `src/processing_controller.py` com `ProcessingController` (lógica de processamento).
  - Criar `src/csv_manager.py` com `CSVManager` (handlers de CSV).
  - Quebrar `MainApp` em `AppRunner` (orquestração) e delegar para controllers.
  - Limpar imports e remover código duplicado.
- **Testes**: Execução completa com lote grande; validar CSV, UI e processamento.
- **Critério**: `main.py` <500 linhas; todos testes passam; funcionalidade idêntica.

#### Fase 5: Limpeza e Otimização (1 dia)
- **Mudanças**: Remover código obsoleto, otimizar imports, adicionar docstrings.
- **Testes**: Benchmark de performance; validar sem regressões.
- **Critério**: Código limpo e documentado; pronto para 01/02.

Cada fase inclui commits separados, revertíveis se necessário. Total estimado: 7-11 dias.

## 8. Dependências
- Aprovar antes de 01/02.

## 9. Próximos Passos
- Aprovar proposta.
- Criar Documento de Design detalhando novos módulos.
- Implementar refatoração e gerar Relatório de Implementação.