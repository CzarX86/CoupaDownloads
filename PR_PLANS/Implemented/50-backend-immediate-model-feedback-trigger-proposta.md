# PR 50 — Backend - Gatilho de Feedback Imediato do Modelo (backend-immediate-model-feedback-trigger)

- Status: implemented
- Implementação: concluída
- Data: 2025-09-23
- Responsáveis: Gemini
- Observações: Este PR é fundamental para fechar o ciclo de feedback humano-no-loop, permitindo que as correções do usuário melhorem diretamente a inteligência do sistema. Depende do PR 48 (Backend - Endpoints de Anotação Interativa).

## Estado da revisão (2025-09-25)

- [x] Implementado no código-base. O endpoint `/documents/{document_id}/feedback` foi criado em `src/server/pdf_training_app/api.py`, a orquestração de `create_training_run` gera dataset real e dispara `fine_tune_model`, salvando artefatos e métricas, conforme detalhado em `services.py` e `embeddinggemma_feasibility/contract_data_trainer.py`.

## Objetivo

Implementar um endpoint no backend que, ao receber anotações corrigidas ou novas, acione um processo de fine-tuning ou atualização incremental do modelo de extração de entidades, visando melhorar a precisão para documentos subsequentes de forma quase imediata.

## Escopo

- Criação de um novo endpoint POST `/documents/{document_id}/feedback` ou `/training-runs/feedback` que recebe as anotações atualizadas.
- Implementação da lógica de serviço para iniciar um processo de fine-tuning ou atualização do modelo usando as anotações fornecidas.
- Substituição da lógica de treinamento placeholder em `src/server/pdf_training_app/services.py`.
- Integração com o módulo `embeddinggemma_feasibility` para o processo de fine-tuning.

## Arquivos afetados

- `src/server/pdf_training_app/api.py` (adicionar o novo endpoint)
- `src/server/pdf_training_app/services.py` (modificar `create_training_run` e adicionar nova função de serviço para feedback)
- `embeddinggemma_feasibility/contract_data_trainer.py` (modificação para suportar fine-tuning incremental)
- `src/server/pdf_training_app/models.py` (adicionar modelo Pydantic para requisição de feedback)

## Critérios de aceitação

- O endpoint de feedback deve aceitar um `document_id` e as anotações corrigidas/novas para esse documento.
- Ao ser acionado, o endpoint deve iniciar um job assíncrono que realiza o fine-tuning ou atualização incremental do modelo.
- O modelo atualizado deve ser salvo e disponibilizado para futuras extrações.
- A lógica de treinamento placeholder em `create_training_run` deve ser substituída por uma implementação funcional.
- O endpoint deve retornar um `JobResponse` indicando o status do processo de feedback.

## Testes manuais

- Fazer upload de um PDF, acionar análise e corrigir/adicionar anotações via UI (após PR 49).
- Acionar o endpoint de feedback com as anotações atualizadas.
- Verificar nos logs do backend se o processo de fine-tuning foi iniciado.
- Fazer upload de um novo PDF similar e verificar se as predições do modelo mostram melhoria de precisão (teste qualitativo).

## Riscos e mitigação

- **Risco:** Complexidade do fine-tuning incremental e garantia de estabilidade do modelo. **Mitigação:** Começar com uma abordagem simples de fine-tuning (ex: re-treinar a última camada ou usar um conjunto de dados pequeno). Monitorar a performance do modelo após o fine-tuning. Pode ser necessário um ADR para definir a estratégia de fine-tuning.
- **Risco:** Tempo de resposta do feedback imediato. **Mitigação:** O processo de fine-tuning deve ser assíncrono e leve. O endpoint deve retornar rapidamente um status de job.

## Notas adicionais

Este PR é fundamental para fechar o ciclo de feedback humano-no-loop, permitindo que as correções do usuário melhorem diretamente a inteligência do sistema. A implementação inicial pode focar em um fine-tuning básico, com aprimoramentos futuros.