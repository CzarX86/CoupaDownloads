# PR 41 — Pipeline de Treinamento via Banco de Dados (training-db-pipeline)

- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: Gemini (Developer)
- Observações: Esta proposta formaliza a migração do pipeline de treinamento de um fluxo baseado em CSV para um que consome anotações diretamente do banco de dados.

## Objetivo
Reconstruir o pipeline de treinamento para que ele leia as anotações revisadas diretamente do banco de dados do aplicativo, gere os datasets, treine os modelos e registre as métricas e versões de volta no banco de dados, substituindo o fluxo de trabalho atual baseado em arquivos CSV.

## Escopo
- Implementar "dataset builders" que consultem o banco de dados (tabelas `annotations`, `annotation_events`) para gerar DataFrames ou arquivos JSONL em memória para treinamento e avaliação.
- Atualizar a orquestração de treinamento para operar através de serviços, gravando os resultados (sumário dos datasets, métricas) em tabelas do banco de dados e caminhos em um blob storage.
- Criar um sistema de relatórios de avaliação que armazene métricas de acurácia e cobertura na tabela `metrics`, vinculada às tabelas `training_runs` e `model_versions`.
- Fornecer endpoints de API para download/exportação de datasets e modelos para fins de auditoria.

**Fora do escopo:**
- A interface (SPA) para visualizar o histórico de treinamento (definida no Plano 40).
- A migração de dados e a descontinuação da CLI legada (definido no Plano 42).

## Arquivos afetados
- `tools/feedback_utils.py`
- `tools/pdf_annotation.py`
- `src/server/pdf_training_app/services.py`
- `src/server/db/repository.py`
- `src/server/pdf_training_app/api.py`
- `docs/USER_GUIDE.md`
- `docs/refactor/pr32-refactor-spa-blueprint.md`

## Critérios de aceitação
1. O "dataset builder" deve consultar as anotações do banco de dados (utilizando os valores aceitos mais recentes) e produzir datasets de treino/avaliação sem a necessidade de gerar arquivos CSV.
2. O serviço de treinamento deve persistir os caminhos dos artefatos, as métricas e o status nas tabelas do banco de dados.
3. Os comandos da CLI devem delegar para os serviços que interagem com o banco de dados (o fluxo legado via CSV deve ser opcional, ativado por uma flag).
4. Testes devem cobrir a lógica de consulta do dataset builder e o serviço de treinamento.
5. A documentação deve ser atualizada para explicar o novo pipeline baseado em banco de dados.

## Testes manuais
- Executar `poetry run pytest tools/tests/test_training_service.py`.
- Disparar um treinamento manualmente pela interface (SPA) e verificar se as tabelas `training_runs`, `metrics`, e `model_versions` foram populadas corretamente.
- Opcionalmente, verificar a execução via CLI: `poetry run python tools/feedback_cli.py train-st --use-db --training-run <id>`.

## Riscos e mitigação
- **Risco**: A complexidade das consultas ao banco de dados pode impactar a performance da geração de datasets.
- **Mitigação**: Otimizar as queries e considerar a criação de snapshots intermediários dos datasets em formato Parquet ou JSONL no blob storage.

## Notas adicionais
Este plano está alinhado com o `plano 40` (UI de histórico) e precede o `plano 42` (deprecation da CLI legada).