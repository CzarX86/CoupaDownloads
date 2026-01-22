# Fluxo de Anotação em PDF

Este guia mostra como substituir a revisão manual na planilha `review.csv` por
uma experiência visual usando o Label Studio, com PDFs renderizados e campos
pré-preenchidos.

```mermaid
digraph PDFReview {
  rankdir=LR
  ReviewCSV["CSV de revisão"] -> PrepareCmd["`annotate-pdf prepare`"] -> LSProject["Projeto Label Studio"]
  LSProject -> Reviewer["Revisor ajusta campos no PDF"] -> ExportJSON["Exportação JSON"]
  ExportJSON -> IngestCmd["`annotate-pdf ingest`"] -> UpdatedCSV["`review.csv` atualizado"]
}
```

## Explicação em linguagem simples
Pense neste fluxo como transformar a planilha em “tarefas com figura”. Um
comando gera um pacote contendo PDFs, miniaturas e um formulário visual. No
Label Studio você abre cada documento, confere os campos (já preenchidos com as
previsões) e corrige diretamente ali. No fim, outro comando junta tudo de volta
na planilha para que o pipeline de ingestão/treino siga igual.

## Pré-requisitos
- Ambiente Python configurado (Poetry ou `venv`).
- Dependências para este fluxo (instaladas por padrão com `poetry install`):
  - `label-studio-sdk` e `pymupdf`
  - Se precisar reinstalar manualmente: `pip install label-studio-sdk pymupdf`
- Pasta com os PDFs originais (use `--pdf-root` para apontar onde eles estão).
- Label Studio instalado (`pip install label-studio` ou `brew install label-studio`).

## 1. Preparar o projeto de anotação
```bash
poetry run python tools/feedback_cli.py annotate-pdf prepare \
  --review-csv reports/feedback/review.csv \
  --out-dir reports/feedback/pdf_annotation \
  --pdf-root embeddinggemma_feasibility/data/sample_documents
```

O comando acima cria:
- `config.xml`: interface do Label Studio com campos e dicas.
- `tasks.json`: tarefas com metadados, valores preditos e campo para corrigir.
- `pdfs/`: cópias dos PDFs localizados (nomes numerados para evitar conflito).
- `thumbnails/`: miniaturas da primeira página (se `pymupdf` estiver disponível).
- `README.md`: lembrete rápido dos próximos passos.

Se algum PDF não for encontrado, o relatório lista os nomes faltantes. Você
pode ajustar o `--pdf-root` ou copiar manualmente os arquivos para a pasta
`pdfs/` antes de importar no Label Studio.

## 2. Revisar no Label Studio
1. Inicie o Label Studio (`label-studio start`).
2. Crie um projeto vazio e, na aba **Labeling Setup**, faça upload de `config.xml`.
3. Em **Tasks**, importe `tasks.json`.
4. Configure **Local Storage** apontando para a pasta `pdfs/` gerada pelo comando.
5. Abra cada tarefa: o thumbnail aparece do lado esquerdo, os campos no painel à direita.
6. Ajuste os valores nos `TextArea` e defina o status na lista de opções (ou deixe em branco para manter o valor original).
7. Use o campo “Reviewer notes” para explicar decisões ou apontar dúvidas.

## 3. Exportar e reingestar no CSV
Após revisar, exporte o projeto em formato JSON (ex.: `export-2024-annotated.json`).
Em seguida, rode:

```bash
poetry run python tools/feedback_cli.py annotate-pdf ingest \
  --export-json export-2024-annotated.json \
  --review-csv reports/feedback/review.csv \
  --out reports/feedback/review_annotated.csv
```

O script atualiza as colunas `_gold`, `_status`, `annotator`, `notes` e `timestamp`
para cada linha com anotação correspondente (`row_id` ou índice). O resultado é
um novo CSV pronto para seguir com `ingest`/`eval`/`train-st`.

Se o CLI relatar alertas após o merge, verifique os campos citados: eles indicam
valores editados sem status, status inválido ou combinações conflitantes (por
exemplo, marcar `OK` mas ter alterado o texto). Resolva os apontamentos dentro
do Label Studio e exporte novamente para garantir que o pipeline enxergue os
ajustes corretamente.

> **Dica**: A SPA local (`src/spa`) reproduz essas etapas com interface estilo AI Builder.
> Ao rodar `npm run dev` (frontend) e `PYTHONPATH=src poetry run python -m server.pdf_training_app.main`
> (backend), você ganha um assistente em quatro fases que orienta upload, auto-tag,
> revisão e retraining sem precisar digitar os comandos acima.

## Boas práticas
- **Backups**: mantenha uma cópia da planilha original antes do merge.
- **Conferência rápida**: ao finalizar, abra o novo CSV e valide se os campos
  anotados refletem o esperado.
- **Integração com pipeline**: após o merge, execute `feedback_cli ingest` para
  regenerar `supervised.jsonl` e demais artefatos de treino.
- **Erros de correspondência**: se houver tarefas sem `row_id`, o comando
  reporta quantas ficaram de fora. Corrija o ID (ou o `Source File`) e reingeste.
- **Miniaturas ausentes**: instale `pymupdf` (extra `annotation`) para habilitar
  as imagens; caso contrário, apenas o link do PDF será exibido.

## Solução de problemas
| Sintoma | Causa provável | Ação sugerida |
| --- | --- | --- |
| Erro “Invalid Label Studio export JSON” | arquivo exportado em formato diferente (ex.: CSV) | refaça a exportação em JSON | 
| Campo não atualiza no CSV | `row_id` ausente ou não bate com o original | verifique se a planilha traz `row_id` e se o task inclui o valor | 
| PDFs vazios no Label Studio | armazenamento local não configurado | em Settings → Storage adicione **Local storage** apontando para `pdfs/` | 
| Miniaturas não aparecem | falta de `pymupdf` ou PDF com zero páginas | reinstale dependências com `poetry install` ou abra manualmente a cópia do PDF | 

---

Com esse fluxo, a revisão deixa de ser uma maratona no Excel e vira um processo
visual, mais rápido de auditar e fácil de treinar novos revisores.
