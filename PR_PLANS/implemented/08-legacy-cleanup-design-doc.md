# Documento de Design: Limpeza de Legado com Backup de Referência

## 1. Contexto
A base continha duas fontes de configuração (`lib/config.py` e `config/app_config.py`), além de rotas legadas no `WorkerManager` e fallback de persistência em CSV via `ExcelProcessor`. Isso elevava complexidade e risco de divergência.

## 2. Decisão Técnica
### 2.1 Configuração única
- Usar `src/config/app_config.py` como fonte única.
- Exportar singleton de runtime (`Config`) para manter padrão atual de consumo.
- Expandir compatibilidade uppercase para cobrir campos usados em runtime (`PAGE_DELAY`, `CLOSE_EDGE_PROCESSES`, `BATCH_FINALIZATION_*`, `PROC_WORKERS_CAP`, `MSG_TO_PDF_*`, etc.).

### 2.2 Remoção de legado de runtime
- Remover `src/lib/config.py` e `src/config/defaults.py` do runtime.
- Arquivar ambos em `docs/legacy/` com sufixo de data.

### 2.3 WorkerManager
- Remover `_legacy_rename_folder_with_status` e `process_parallel_legacy`.
- Manter finalização moderna (`FolderHierarchyManager.finalize_folder`).
- Em falha de finalização, manter pasta original e registrar warning.

### 2.4 Persistência
- Consolidar `CSVHandler` para fluxo SQLite único.
- Remover caminho `enable_legacy_updates` e fallback de update via `ExcelProcessor` no handler.

### 2.5 Deduplicação
- Remover implementação duplicada de `_compose_csv_message` em `main.py`.
- Reutilizar utilitário compartilhado (`src/core/utils.py`) no `WorkerManager`.

## 3. Impactos em Interface Interna
- Módulos passam a importar `Config` de `src/config/app_config.py`.
- APIs internas legadas removidas de `WorkerManager`.
- Sem alteração de contrato CLI externo.

## 4. Fluxo Atualizado
1. Runtime carrega `Config` único de `app_config`.
2. Workers/processos leem e atualizam configuração runtime pelo mesmo singleton.
3. Persistência incremental ocorre somente em SQLite.
4. Finalização de pasta usa apenas caminho moderno.

## 5. Estratégia de Backup
- Branch: `codex/legacy-backup-20260304`.
- Tag: `legacy-pre-cleanup-20260304`.
- Arquivo de referência local: `docs/legacy/README.md`.

## 6. Validação
- Executar `uv run pytest`.
- Validar fluxo com PO sem documento no PO (fallback PR).
- Validar fluxo com PO com anexos e finalização de pasta.
