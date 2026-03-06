# Inventário de Limpeza de Legado (2026-03-04)

## Mapeamento realizado

### Configuração
- Todos os imports de `lib.config` no runtime (`src/` e `tests/`) foram migrados para `config.app_config`.
- `src/lib/config.py` foi removido do runtime e arquivado em `docs/legacy/lib_config_20260304.py`.

### Defaults
- `src/config/defaults.py` foi removido do runtime e arquivado em `docs/legacy/config_defaults_20260304.py`.
- `src/workers/profile_manager.py` deixou de depender de `get_default_timeouts()` e passou a usar defaults locais explícitos.

### WorkerManager
- Removidos: `process_parallel_legacy` e `_legacy_rename_folder_with_status`.
- Finalização de pastas mantém apenas `FolderHierarchyManager.finalize_folder`.

### CSV
- `src/core/csv_handler.py` consolidado para persistência SQLite única.
- `enable_legacy_updates` removido.

### Mensageria CSV
- `src/main.py` deixou de manter `_compose_csv_message` próprio.
- `src/worker_manager.py` passou a reutilizar `src/core/utils.py::_compose_csv_message`.
