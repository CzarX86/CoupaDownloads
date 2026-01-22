# PR 6 — Escrita segura de CSV (verificação + ordem de colunas)

Objetivo
- Confirmar e consolidar a escrita segura no CSV: coerções de tipo, criação de colunas faltantes, preservação do delimitador e codificação. Adicionar uma ordenação estável de colunas para alinhar CSV/Excel.

Escopo
- Estado atual já contém coerções e parâmetros corretos em `ExcelProcessor.update_po_status` (CSV path). Este PR apenas garante ordem estável de colunas e documenta o comportamento.

Arquivos afetados
- `src/core/excel_processor.py`

Pseudodiff (referencial)
```
*** Update File: src/core/excel_processor.py
@@ def update_po_status(...):
     df, detected_sep, _enc = ExcelProcessor._read_csv_auto(excel_file_path)
@@
     for col in string_cols:
         if col not in df.columns:
             df[col] = ""
         else:
             df[col] = df[col].astype('string').fillna("")
@@
     for col in int_cols:
         if col not in df.columns:
             df[col] = 0
         else:
             df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Ensure a stable, human-friendly column order matching Excel layout
    desired_order = [
        'PO_NUMBER','STATUS','SUPPLIER','ATTACHMENTS_FOUND','ATTACHMENTS_DOWNLOADED',
        'AttachmentName','LAST_PROCESSED','ERROR_MESSAGE','DOWNLOAD_FOLDER','COUPA_URL'
    ]
    existing = [c for c in desired_order if c in df.columns]
    remaining = [c for c in df.columns if c not in desired_order]
    df = df[existing + remaining]
@@
     df.to_csv(
         excel_file_path,
         index=False,
         sep=detected_sep,
         encoding="utf-8-sig",
         lineterminator="\n",
         quoting=csv.QUOTE_MINIMAL
     )
```

Critérios de aceitação
- Sem FutureWarnings/SettingWithCopy; arquivo abre corretamente no Excel mantendo o delimitador original.
- Cabeçalho em ordem estável: PO_NUMBER, STATUS, SUPPLIER, ATTACHMENTS_FOUND, ATTACHMENTS_DOWNLOADED, AttachmentName, LAST_PROCESSED, ERROR_MESSAGE, DOWNLOAD_FOLDER, COUPA_URL.

Teste manual
- Usar um CSV com “;” e outro com “,”; processar 1–2 POs e verificar: ordem de colunas, codificação (BOM), novas colunas adicionadas sem quebras.

Mensagem de commit sugerida
- `chore(csv): PR 06 — lock column order and keep safe write settings`

Branch sugerido
- `chore/06-csv-safe-write`

Checklist
- [x] Objetivo e Escopo claros e limitados
- [x] Arquivos afetados listados
- [x] Pseudodiff pequeno e representativo
- [x] Critérios de aceitação e testes manuais
- [x] Mensagem de commit e branch

