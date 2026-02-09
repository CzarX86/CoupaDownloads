# Documento de Design: Persistência Somente em SQLite e Exportação Final para Cópia do CSV

## 1. Contexto
O processamento paralelo usa `CSVHandler` para persistir resultados. Hoje, se o SQLite não estiver disponível ou se updates legacy estiverem habilitados, o CSV pode ser modificado durante a execução (incluindo criação de `_progress.csv`). O requisito é manter o CSV de input somente leitura e persistir tudo em SQLite até o final.

## 2. Decisão Técnica
Aplicar **modo SQLite-only**:
- Desabilitar updates legacy (ExcelProcessor) durante o run.
- Manter `SQLiteHandler` como persistência única.
- Exportar resultados para uma cópia do CSV ao final do processamento.

## 3. Alterações Planejadas
### 3.1 Configuração
Novas chaves (com defaults):
- `SQLITE_ONLY_PERSISTENCE = True`
- `CSV_OUTPUT_SUFFIX = "_processed"`
- `CSV_OUTPUT_INCLUDE_TIMESTAMP = True`
- `CSV_OUTPUT_DIR = None` (usa pasta do input)

### 3.2 CSVHandler
- Novo parâmetro `enable_legacy_updates`.
- Quando `SQLITE_ONLY_PERSISTENCE=True`, o handler **não** chama `ExcelProcessor.update_po_status`.

### 3.3 CSVManager
- Guardar `input_path` e `output_copy_path`.
- Gerar saída com sufixo + timestamp.
- Exportar resultados para a cópia (`output_path`) ao final.

### 3.4 ExcelProcessor
- Evitar updates de status em CSV durante validação de PO inválida quando SQLite-only estiver ativo.

## 4. Fluxo Atualizado
1. Ler input CSV.
2. Inicializar `CSVHandler` com SQLite-only.
3. Processar POs; cada resultado atualiza SQLite.
4. No final, exportar resultados para cópia do CSV.
5. Limpar SQLite temporário.

## 5. Impactos
- O CSV de input não é modificado.
- Resultados ficam disponíveis em um novo arquivo com timestamp.
- Sem updates incrementais no CSV durante execução.

## 6. Testes / Validação
- Execução completa com CSV de input.
- Conferir que o input não foi alterado.
- Verificar criação da cópia final com resultados atualizados.
