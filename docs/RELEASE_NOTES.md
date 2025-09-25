# Release Notes — Fluxo PDF-First e UX de Pré-processamento

## Destaques
- **Remoção completa das rotinas CSV**: eliminamos `scripts/migrate_review_csv`, o pacote auxiliar e o `feedback_cli`. O treinamento passa a depender exclusivamente da interface de anotação em PDF e do backend orientado ao banco. 【F:tools/legacy/feedback_cli.py†L1-L17】
- **Pré-processamento automático com telemetria**: o upload de um documento dispara o job de análise em segundo plano, registra o progresso no banco e reaproveita essa telemetria para atualizar a UI em tempo real. 【F:src/server/pdf_training_app/services.py†L49-L139】【F:src/server/db/repository.py†L241-L266】
- **API de jobs filtrável**: `/api/pdf-training/jobs` agora aceita filtros por recurso, permitindo que o SPA acompanhe especificamente os jobs de análise de cada documento. 【F:src/server/pdf_training_app/api.py†L69-L116】
- **Indicadores visuais no SPA**: a tela do wizard exibe um painel de status com spinner, mensagens de etapa e alertas em caso de falha, além de sobrepor feedback no viewer enquanto o PDF ainda não está pronto. 【F:src/spa/src/components/DocumentProcessingStatus.tsx†L1-L89】【F:src/spa/src/components/PdfViewer.tsx†L1-L68】【F:src/spa/src/styles.css†L1-L67】
- **Assistente LLM conectado ao wizard**: o backend expõe `/documents/{id}/support/llm` para gerar sugestões assíncronas e a UI ganhou um painel dedicado que mostra decisões, custos estimados e status em tempo real. 【F:src/server/pdf_training_app/support.py†L1-L217】【F:src/server/pdf_training_app/api.py†L1-L144】【F:src/spa/src/components/LLMSupportPanel.tsx†L1-L152】

## Itens de Acompanhamento
- Integrar testes de frontend que verifiquem o polling de jobs e as mensagens exibidas durante o pré-processamento.
- Documentar boas práticas de troubleshooting para jobs de análise que retornem status `FAILED`.
