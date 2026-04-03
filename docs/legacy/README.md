# Arquivo de Legado

Este diretório preserva arquivos removidos do runtime durante a limpeza de legado da proposta 08.

## Referências de backup Git

- Branch de backup: `codex/legacy-backup-20260304`
- Tag de backup: `legacy-pre-cleanup-20260304`
- Branch de trabalho da limpeza: `codex/legacy-cleanup-20260304`

## Arquivos arquivados

- `docs/legacy/lib_config_20260304.py`
  - Origem: `src/lib/config.py`
  - Motivo: módulo duplicado/depreciado; configuração consolidada em `src/config/app_config.py`.
- `docs/legacy/config_defaults_20260304.py`
  - Origem: `src/config/defaults.py`
  - Motivo: factories de defaults legadas; substituídas por configuração central e defaults locais no `ProfileManager`.
- `docs/legacy/inventory_20260304.md`
  - Conteúdo: mapeamento de imports removidos e itens limpos durante a execução da proposta 08.

## Impacto esperado

- Imports de configuração migrados para `src/config/app_config.py`.
- Caminhos legados de execução removidos de `WorkerManager`.
- Persistência CSV simplificada para fluxo único via SQLite.

## Como recuperar um arquivo legado

1. Ver o snapshot completo na branch/tag de backup.
2. Copiar o arquivo deste diretório para uma branch de investigação, sem reintroduzir como dependência de runtime.
