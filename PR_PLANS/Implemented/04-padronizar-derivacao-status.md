# PR 4 — Padronizar derivação de STATUS (mesma lógica em todos os modos)

Objetivo
- Garantir que a derivação de STATUS use a mesma lógica (`_parse_counts_from_message` + `_derive_status_label`) no sequencial e no worker.

Escopo
- Arquivo: `src/main.py`

Arquivos afetados
- `src/main.py`

Pseudodiff (referencial)
```
*** Update File: src/main.py
@@ def process_single_po(...):
- final_status = _derive_status_label(success, message)
+ dl, total = _parse_counts_from_message(message or '')
+ final_status = _derive_status_label(success, message)  # usa dl/total internamente
```

Critérios de aceitação
- Mesma mensagem “X/Y” resulta em COMPLETED quando X==Y e PARTIAL quando X<Y, em qualquer modo.

Teste manual
- POs com diferentes quantidades de anexos; validar STATUS idêntico nos dois modos.

Mensagem de commit sugerida
- `refactor(status): unify status derivation across sequential and worker`

Branch sugerido
- `refactor/status-derivation`

