# Human-in-the-Loop (HITL) Feedback Workflow

> ⚠️ **Importante:** a partir da arquitetura 42 o fluxo de planilhas `review.csv`
> foi descontinuado. As instruções abaixo mostram como operar o ciclo de
> feedback utilizando o banco de dados, a API FastAPI e o SPA React.

## Visão geral

1. **Cadastrar documentos** — envie os PDFs diretamente pelo wizard ou via
   `POST /api/pdf-training/documents`. O backend cria a anotação inicial,
   dispara o pré-processamento e registra eventos no histórico do documento.
2. **Revisar e anotar** — utilize a página “PDF Training Wizard” no SPA. A
   tabela de documentos carrega os PDFs migrados, o painel lateral exibe o
   formulário de anotação e o `PdfViewer` permite validar diretamente no
   documento.
   - O painel **LLM Helper** pode ser acionado sob demanda para gerar sugestões
     automáticas com base nas previsões atuais, exibindo as recomendações em
     tempo real na própria UI.
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
   Label Studio, parta desses artefatos armazenados no banco ou gere novas
   tarefas a partir das entidades capturadas.

## Boas práticas

- Configure `PDF_TRAINING_STORAGE_ROOT` em ambientes locais para direcionar o
  armazenamento de blobs antes de subir o backend.
- Verifique o painel de saúde (`/api/pdf-training/system-status`) antes de
  iniciar novos treinamentos.
- Utilize os testes automatizados (`poetry run pytest -k pdf_training`) ao
  evoluir o fluxo para garantir que os endpoints continuem íntegros.

## Assistente LLM integrado

- Acesse o painel **LLM Helper** na coluna direita do wizard para disparar um
  job assíncrono que consome o mesmo `review.csv` usado no pré-processamento.
- O backend executa o helper em modo *dry-run* por padrão (`PDF_TRAINING_LLM_DRY_RUN=true`).
  Defina as variáveis `PDF_TRAINING_LLM_PROVIDER`, `PDF_TRAINING_LLM_MODEL` e a
  chave (`PDF_TRAINING_LLM_API_KEY` ou `DEEPSEEK_API_KEY`/`OPENAI_API_KEY`) para
  habilitar chamadas reais.
- Use o botão “Generate suggestions” sempre que desejar atualizar as propostas;
  o painel lista campo, decisão e confiança, mantendo a revisão humana como
  etapa final antes de persistir as alterações.
