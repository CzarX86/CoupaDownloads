# 43 - Auditoria de Integração da UI

## 1. Bateria de testes executada
- Comando: `poetry run pytest`
- Resultado: falha durante a coleta (4 erros). Os testes que quebraram dependem de módulos que não existem ou não estão publicados no pacote atual:
  - `embeddinggemma_feasibility/test_single_pdf.py` importa `advanced_coupa_field_extractor`, ausente no ambiente atual.【cf3fb5†L1-L37】【F:embeddinggemma_feasibility/test_single_pdf.py†L9-L41】
  - `src/utils/GeminiTests/test_main_app_robustness.py` espera `src.main.MainApp`, mas o pacote `src.main` não é distribuído (a orquestração vive hoje em `src/Core_main.py`).【cf3fb5†L1-L37】【F:src/utils/GeminiTests/test_main_app_robustness.py†L14-L55】
  - `src/utils/test_po16518898_main.py` e `src/utils/test_single_po.py` importam `DownloadManager`/`LoginManager` de `core.downloader`, classes que não existem depois da refatoração para a classe única `Downloader` (`Core_main` instancia essa classe diretamente).【cf3fb5†L1-L37】【F:src/utils/test_po16518898_main.py†L13-L48】【F:src/utils/test_single_po.py†L15-L60】【F:src/Core_main.py†L18-L166】

## 2. Fluxos já conectados à SPA
A UI implementada em React/Vite (`src/spa`) está focada no assistente de treinamento de PDFs, usando React Query para conversar com o gateway FastAPI.

- Página principal `PdfTrainingWizard` cria o `QueryClientProvider` e exibe tabela de documentos, cartão de anotação e histórico de treinamento, com seleção de documento mantida em estado local.【F:src/spa/src/pages/PdfTrainingWizard.tsx†L1-L34】
- `DocumentTable` lista documentos e faz upload por drag & drop chamando `getDocuments`/`uploadDocument`; `TrainingHistory` usa `getTrainingRuns`; `AnnotationCard` envia anotações para a API; `WarningsPanel` exibe alertas gerados no cliente.【F:src/spa/src/components/DocumentTable.tsx†L1-L66】【F:src/spa/src/components/TrainingHistory.tsx†L1-L24】【F:src/spa/src/components/AnnotationCard.tsx†L1-L47】【F:src/spa/src/components/WarningsPanel.tsx†L1-L20】
- O gateway FastAPI (`src/server/pdf_training_app`) disponibiliza upload/listagem de documentos, disparo de análises assíncronas, ingestão de anotações e criação de execuções de treinamento usando repositório e job manager assíncronos.【F:src/server/pdf_training_app/api.py†L42-L165】【F:src/server/pdf_training_app/services.py†L86-L205】【F:src/server/pdf_training_app/jobs.py†L1-L86】
- O repositório SQLAlchemy mantém documentos, versões, anotações, jobs e execuções com tabelas relacionais e enums de status reutilizados pela API.【F:src/server/db/models.py†L1-L126】【F:src/server/db/models.py†L171-L244】

## 3. Lacunas entre SPA e backend
Apesar de existir uma base integrada, há desalinhamentos que impedem a UI de operar ponta-a-ponta:

1. **Contratos de API divergentes**
   - A API retorna `DocumentListResponse` (`{"items": [...]}`) e status no formato `PENDING/IN_REVIEW/...`, enquanto a SPA espera um array direto com status `new/extracted/reviewing/completed` e IDs numéricos.【F:src/server/pdf_training_app/api.py†L56-L60】【F:src/server/pdf_training_app/services.py†L61-L104】【F:src/spa/src/api/pdfTraining.ts†L5-L29】
   - O endpoint de ingestão recebe `UploadFile` via campo `export_json`, mas o front envia JSON puro em `POST /documents/{id}/annotations`, sem multipart.【F:src/server/pdf_training_app/api.py†L78-L89】【F:src/spa/src/api/pdfTraining.ts†L52-L54】
   - O frontend chama `GET /api/pdf-training/training-runs`, porém o backend expõe apenas `POST /training-runs` e rotas por ID; além disso a view tenta usar `get_training_run_dataset`/`get_training_run_model_path`, que não foram importadas no router (resulta em `NameError`).【F:src/server/pdf_training_app/api.py†L15-L37】【F:src/server/pdf_training_app/api.py†L92-L114】【F:src/spa/src/api/pdfTraining.ts†L42-L45】

2. **Tipagem do cliente incompatível**
   - Interfaces do cliente tratam IDs como `number` e campos `artifacts/metrics`, que não são devolvidos pelo backend atual.【F:src/spa/src/api/pdfTraining.ts†L5-L24】【F:src/server/pdf_training_app/services.py†L61-L205】

3. **Estados e avisos não preenchidos**
   - O front-end mantém `warnings` apenas em memória local sem conectar ao endpoint `/system-status` que já entrega contagem de documentos e estado do banco.【F:src/spa/src/pages/PdfTrainingWizard.tsx†L11-L33】【F:src/server/pdf_training_app/api.py†L131-L165】

## 4. Funcionalidades relevantes fora da UI
- O download massivo de POs continua sendo um fluxo CLI/console em `src/Core_main.py`, orquestrando Selenium, processamento de planilhas e estruturação de pastas sem expor ações pela SPA.【F:src/Core_main.py†L1-L188】
- O pipeline de feedback e anotações (criação de CSVs, ingestão de Label Studio, fine-tuning) vive em `tools/feedback_cli.py`, incluindo integrações com serviços do backend, mas pensado para uso em terminal.【F:tools/feedback_cli.py†L1-L120】
- Scripts de testes utilitários em `src/utils/` e `embeddinggemma_feasibility/` dependem de componentes não empacotados, sugerindo que ainda são experimentais ou aguardam refatoração para se alinhar à estrutura atual.【F:embeddinggemma_feasibility/test_single_pdf.py†L9-L41】【F:src/utils/test_single_po.py†L15-L60】

## 5. Recomendações
1. Alinhar contratos REST (shape e nomenclatura de campos) e autenticar uploads de anotações para destravar a SPA.
2. Revisitar a suíte de testes para remover ou adaptar dependências ausentes (`DownloadManager`, `advanced_coupa_field_extractor`, `src.main`) garantindo que `pytest` execute sem erro.
3. Documentar claramente quais fluxos permanecem apenas via CLI e quais estarão expostos na web, preparando roadmap para expor o downloader na UI se desejado.
