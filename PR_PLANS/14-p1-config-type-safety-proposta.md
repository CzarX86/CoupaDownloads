# Proposta de Mudança: Type Safety na Configuração

## 1. Identificação
- **Número da Proposta**: 14
- **Título**: Eliminar getattr(Config, ...) — Acesso Tipado à Configuração
- **Data de Criação**: 1 de abril de 2026
- **Autor**: GitHub Copilot
- **Status**: Aprovado — Em Implementação
- **Dependências**: Nenhuma obrigatória.

## 2. Contexto e Problema
O código possui mais de 40 ocorrências de `getattr(Config, "NOME_DA_CHAVE", default)` em múltiplos arquivos. Esse padrão:
- Não é verificado pelo mypy ou pyright — typos propagam silenciosamente até o runtime.
- Centraliza defaults em múltiplos locais — quem define o default "real" de `CSV_OUTPUT_SUFFIX`?
- Dificulta refatoração: renomear um campo requer grep manual em todo o codebase.

Todos os campos acessados via `getattr` já possuem propriedades legacy no `AppConfig` (ex: `Config.CSV_OUTPUT_SUFFIX`, `Config.FINALIZATION_ACK_TIMEOUT_SECONDS`). Portanto esta proposta é uma **limpeza sintática** — não requer novos campos no modelo.

## 3. Objetivo
Substituir todos os `getattr(Config, "X", default)` por `Config.X` nos arquivos de produção em `src/`.

## 4. Escopo
**Incluso:**
- `src/csv_manager.py`: 5 ocorrências
- `src/main.py`: múltiplas ocorrências (MSG_TO_PDF, USE_PROCESS_POOL, PROC_WORKERS, etc.)
- `src/worker_manager.py`: múltiplas ocorrências (FINALIZATION_*, BATCH_FINALIZATION_*, DOWNLOAD_FOLDER, PROC_WORKERS)
- `src/workers/persistent_pool.py`: múltiplas ocorrências (FINALIZATION_*, BATCH_FINALIZATION_*)
- `src/workers/worker_process.py`: DOWNLOAD_FOLDER, BATCH_FINALIZATION_ENABLED
- `src/config/profile_config.py`: EDGE_PROFILE_DIR, EDGE_PROFILE_NAME
- `src/lib/excel_processor.py`: EXCEL_FILE_PATH, SQLITE_ONLY_PERSISTENCE
- `src/lib/downloader.py`: múltiplas ocorrências (selectors, timeouts, PR fallback)
- `src/lib/direct_http_downloader.py`, `src/lib/playwright_downloader.py`: selectors

**Fora de escopo:**
- Criação de novos campos no AppConfig.
- Mudanças de comportamento ou lógica de negócio.

## 5. Critérios de Aceitação
- Zero ocorrências de `getattr(Config,` e `getattr(ExperimentalConfig,` e `getattr(_Cfg,` em `src/`.
- `uv run pytest` sem regressões.

## 6. Riscos e Mitigações
- **Risco**: property retorna tipo diferente do expected default no getattr.
  - **Mitigação**: verificar tipo e valor default de cada campo antes de substituir.

## 7. Plano de Validação
- `grep -r "getattr(Config\|getattr(ExperimentalConfig\|getattr(_Cfg" src/` deve retornar zero resultados.
- `uv run pytest` completo.
