# Human-in-the-Loop (HITL) Feedback Workflow

> ⚠️ **Importante:** a partir da arquitetura 42 o fluxo de planilhas `review.csv`
> foi descontinuado. As instruções abaixo mostram como operar o ciclo de
> feedback utilizando o banco de dados, a API FastAPI e o SPA React.

## Visão geral

1. **Migrar dados legados (opcional)** — execute `poetry run python
   scripts/migrate_review_csv.py --training-run <nome> '<glob>'` para importar
   planilhas antigas. Os registros são convertidos em documentos, anotações e
   `training_runs` no banco.
2. **Revisar e anotar** — utilize a página “PDF Training Wizard” no SPA. A
   tabela de documentos carrega os PDFs migrados, o painel lateral exibe o
   formulário de anotação e o `PdfViewer` permite validar diretamente no
   documento.
3. **Gerar datasets automaticamente** — ao concluir as anotações o backend gera
   `supervised.jsonl`, `st_pairs.jsonl`, `training_analysis.json` e demais
   artefatos no blob store (`storage/pdf_training/blobs`).
4. **Acompanhar treinamentos** — acione `POST /api/pdf-training/training-runs`
   ou o botão **Train selected documents** no SPA. O histórico mostra status,
   métricas e links para baixar datasets/modelos (`/training-runs/{id}/dataset`
   e `/training-runs/{id}/model`).
5. **Avaliar métricas** — cada `training_run` persiste `metrics.md` e o
   respectivo JSON de métricas. Use o painel “Training history” ou os endpoints
   `/api/pdf-training/training-runs` para consultar.
6. **Exportar para ferramentas externas** — utilize `/api/pdf-training/documents/{id}/content`
   para baixar o PDF e `/api/pdf-training/documents/{id}/entities` para obter as
   entidades pré-processadas. Caso seja necessário criar um projeto no
   Label Studio, parta desses artefatos já armazenados no banco.

## Boas práticas

- Configure `PDF_TRAINING_STORAGE_ROOT` em ambientes locais para direcionar o
  armazenamento de blobs antes de rodar o script de migração.
- Verifique o painel de saúde (`/api/pdf-training/system-status`) antes de
  iniciar novos treinamentos.
- Utilize os testes automatizados (`poetry run pytest -k pdf_training`) ao
  evoluir o fluxo para garantir que os endpoints continuem íntegros.
