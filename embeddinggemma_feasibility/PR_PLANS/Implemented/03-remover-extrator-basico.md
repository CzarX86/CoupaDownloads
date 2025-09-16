# PR 03 — Remover extrator básico e referências (embeddinggemma_feasibility)

## Objetivo
Remover o extrator "básico" (`coupa_field_extractor.py`) para simplificar o subprojeto e evitar manutenção duplicada, mantendo apenas o extrator avançado. Atualizar scripts e documentação que ainda referenciam o extrator básico.

## Escopo
- Remover `embeddinggemma_feasibility/coupa_field_extractor.py`.
- Remover/atualizar `embeddinggemma_feasibility/extract_coupa_fields.py` (script que usa o extrator básico):
  - Opção A: remover o script.
  - Opção B: redirecionar para o extrator avançado (mensagem de depreciação + chamada do avançado). Preferimos A para reduzir ambiguidade.
- Atualizar docs que mencionam o extrator básico para apontar o avançado.
- Não alterar o `advanced_coupa_field_extractor.py` neste PR.

## Arquivos afetados
- Removido: `embeddinggemma_feasibility/coupa_field_extractor.py`
- Removido: `embeddinggemma_feasibility/extract_coupa_fields.py` (ou convertido para shim de depreciação)
- Alterado: `embeddinggemma_feasibility/COUPA_FIELDS_GUIDE.md` (trechos que citam o básico)

## Pseudodiff (representativo)
```
- embeddinggemma_feasibility/coupa_field_extractor.py
- embeddinggemma_feasibility/extract_coupa_fields.py
~ embeddinggemma_feasibility/COUPA_FIELDS_GUIDE.md
-  from coupa_field_extractor import CoupaPDFFieldExtractor
+  from advanced_coupa_field_extractor import AdvancedCoupaPDFFieldExtractor
```

## Critérios de aceitação
- Arquivos do extrator básico e seu script deixam de existir no repositório.
- Nenhuma importação quebrada: busca global por `coupa_field_extractor` não retorna referências ativas de código.
- Documentação atualizada sem instruções que apontem para o extrator básico.

## Testes manuais
1) `rg -n "coupa_field_extractor"` retorna vazio em arquivos de código (excluindo docs históricos).
2) Rodar o extrator avançado com PDFs de exemplo e confirmar geração do CSV.

## Mensagem + branch sugeridos
- Branch (plan): `plan/03-remover-extrator-basico`
- Commit (plan): `docs(pr-plan): PR 03 — remover extrator básico e referências`
- Branch (impl): `chore/03-remover-extrator-basico`
- Commit (impl): `chore(rag): PR 03 — remover extrator básico e referências`
