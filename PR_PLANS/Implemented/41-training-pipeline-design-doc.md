# Arquitetura 41 — Pipeline de Treinamento via Banco de Dados (training-db-pipeline)

- Status: draft
- Data: 2025-09-23
- Responsáveis: Gemini (Developer)
- Observações: Detalhes técnicos para a implementação do pipeline de treinamento baseado em banco de dados.

## Resumo executivo
Este documento detalha a arquitetura para refatorar o pipeline de treinamento de modelos. O novo design abandona a abordagem baseada em arquivos CSV e passa a consumir anotações diretamente de um banco de dados. O pipeline será orquestrado por uma camada de serviços na aplicação do servidor, que será responsável por gerar datasets, treinar modelos, e registrar métricas e artefatos no próprio banco de dados e em um blob storage.

## Objetivos e não objetivos
### Objetivos
- Orquestrar o pipeline de treinamento através de uma camada de serviço (`src/server/pdf_training_app/services.py`).
- Ler dados de anotações diretamente do banco de dados.
- Armazenar métricas, logs e caminhos para os artefatos do modelo no banco de dados.
- Manter a CLI como um wrapper fino para a nova camada de serviço.

### Não Objetivos
- Implementar a interface de visualização (SPA), que é parte do plano 40.
- Migrar dados legados ou descontinuar a CLI antiga, que são parte do plano 42.

## Estado atual
O pipeline de treinamento atual depende de um fluxo manual que envolve a exportação de anotações para arquivos CSV. Os scripts em `tools/` (`cmd_ingest`, `cmd_eval`, `cmd_train_st`) consomem esses arquivos para treinar os modelos. As métricas e os modelos gerados não são versionados ou rastreados de forma sistemática.

## Visão proposta
A nova arquitetura centraliza a lógica do pipeline em uma camada de serviço, tornando o processo mais robusto e automatizado.

### Componentes e responsabilidades
- **`src/server/db/repository.py`**: Conterá as queries para buscar as anotações e para salvar os resultados do treinamento (métricas, status, etc).
- **`DatasetBuilder` (novo componente, possivelmente em `src/server/pdf_training_app/datasets.py`)**: Responsável por consultar o banco de dados através do repositório e transformar os dados em estruturas prontas para o treinamento (DataFrames, etc).
- **`src/server/pdf_training_app/services.py`**: Orquestrará o fluxo: chamar o `DatasetBuilder`, iniciar o `TrainingJob`, e registrar os resultados.
- **`TrainingJob` (lógica de treinamento, a ser refatorada de `tools/`)**: Executará o treinamento do modelo e produzirá os artefatos (modelo treinado) e as métricas.
- **`tools/feedback_cli.py`**: Será um "cliente" da camada de serviço, com os comandos da CLI sendo wrappers que chamam os serviços via API ou diretamente.

### Fluxos (diagramas, mermaid, sequência)

```mermaid
graph TD
    subgraph "Fluxo de Treinamento"
        A[Interface (SPA ou CLI)] -- Inicia Treinamento --> B(API: /training-runs)
        B --> C(Training Service)
        C -- Chama --> D(Dataset Builder)
        D -- Consulta --> E[DB: annotations]
        E --> D
        D -- Retorna Dataset --> C
        C -- Inicia --> F(Training Job)
        F -- Gera --> G[Artefato do Modelo]
        F -- Gera --> H[Métricas]
        C -- Salva --> I[DB: metrics, model_versions]
        C -- Salva --> J[Blob Storage: /models]
    end

    classDef db fill:#E8F5E9,stroke:#1B5E20,color:#1B5E20
    class E,I db
    classDef storage fill:#FFF9C4,stroke:#F57F17,color:#F57F17
    class J storage
```

### Pseudocódigo
```python
# src/server/pdf_training_app/services.py

async def run_training(training_run_id: UUID, db: AsyncSession) -> None:
    # 1. Construir o dataset a partir do banco de dados
    dataset_builder = DatasetBuilder(db)
    training_data = await dataset_builder.build_from_annotations(training_run_id)

    # 2. Executar o treinamento
    trainer = ModelTrainer() # Lógica de treinamento refatorada
    model_artifact, metrics = await trainer.train(training_data)

    # 3. Salvar resultados
    repo = Repository(db)
    model_path = await blob_storage.save(model_artifact)
    await repo.save_training_results(
        run_id=training_run_id,
        metrics=metrics,
        model_path=model_path
    )
```

## Plano de implementação
1.  **Extração do Dataset**: Implementar o `DatasetBuilder` que consulta as anotações e gera os datasets.
2.  **Orquestração do Treinamento**: Refatorar a lógica de `cmd_ingest`/`cmd_eval`/`cmd_train_st` para dentro de uma camada de serviço que aceita uma sessão do banco de dados e um `training_run_id`.
3.  **Logging de Métricas**: Implementar a lógica para salvar as métricas na tabela `metrics` e os caminhos dos artefatos na tabela `model_versions`.
4.  **Endpoints de Exportação**: Criar endpoints na API para fazer o download dos datasets e modelos.
5.  **Testes e Documentação**: Criar testes de unidade e integração para os novos serviços e atualizar a documentação.

## Decisões, trade-offs e alternativas consideradas
A principal decisão é usar o banco de dados da própria aplicação para tracking em vez de uma ferramenta externa como o MLflow.
- **Prós**: Reutiliza a infraestrutura existente, mantém a consistência dos dados, e evita adicionar uma nova dependência complexa.
- **Contras**: Exige a implementação manual de funcionalidades que ferramentas como o MLflow oferecem prontas (ex: UI para comparação de experimentos).
- **Justificativa**: Para o escopo atual, a integração com o banco de dados é mais simples e atende às necessidades do projeto. A UI de visualização já está planejada (Plano 40) e será construída sobre os dados do nosso banco.

## Pendências e próximos passos
- [ ] Criar a ADR para formalizar a decisão de usar o banco de dados para tracking.
- [ ] Iniciar a implementação da Fase 1 (DatasetBuilder).
- [ ] Definir o schema exato das tabelas `metrics` e `model_versions`.