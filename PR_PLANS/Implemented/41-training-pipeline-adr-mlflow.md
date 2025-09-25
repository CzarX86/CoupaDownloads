# ADR 001: Uso do Banco de Dados Interno para Tracking de Experimentos de ML

- Status: Proposto
- Data: 2025-09-23
- Responsáveis: Gemini (Developer)

## Contexto
Para a implementação do novo pipeline de treinamento (`41-training-db-pipeline`), é necessário um sistema para rastrear experimentos, versionar modelos e armazenar métricas. As principais alternativas são:
1.  **Ferramenta externa dedicada (ex: MLflow, DVC)**: Adotar uma ferramenta padrão da indústria para o ciclo de vida de ML.
2.  **Banco de dados interno da aplicação**: Estender o schema do banco de dados existente para armazenar as informações de tracking.

## Decisão
Optamos por **usar o banco de dados interno da aplicação** para o tracking de experimentos de ML. Serão criadas ou modificadas tabelas como `training_runs`, `metrics`, e `model_versions` para armazenar todas as informações relevantes do pipeline de treinamento. Os artefatos dos modelos serão armazenados em um blob storage, e seus caminhos serão referenciados no banco de dados.

## Consequências
### Positivas
- **Reutilização de Infraestrutura**: Evita a necessidade de configurar e manter uma nova ferramenta e sua infraestrutura.
- **Consistência dos Dados**: Mantém todos os dados da aplicação, incluindo os de ML, em um único local, facilitando a gestão e a consistência.
- **Menor Complexidade**: Reduz a complexidade do projeto ao não adicionar uma nova dependência externa significativa.
- **Integração Simplificada**: A camada de serviço da aplicação pode interagir diretamente com as tabelas de tracking, simplificando o desenvolvimento.

### Negativas
- **Implementação Manual**: Funcionalidades que seriam "out-of-the-box" em ferramentas como o MLflow (ex: UI para comparação de execuções, APIs de consulta de experimentos) precisarão ser implementadas manualmente.
- **Menos Flexibilidade**: A solução é menos flexível e mais acoplada à aplicação do que uma ferramenta de tracking genérica.

### Mitigação
- A UI para visualização dos resultados do treinamento já está planejada (Plano 40), o que mitiga a falta de uma UI pronta.
- As funcionalidades de tracking a serem implementadas serão focadas nas necessidades específicas do projeto, evitando a complexidade de uma solução genérica.