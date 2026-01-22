# PR 42 — Migração de Dados Legados e Descontinuação do Fluxo CSV (migration-and-decommission)

- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: Gemini (Developer)
- Observações: Esta proposta formaliza o processo de migração dos dados de `review.csv` para o banco de dados e a remoção completa do fluxo de trabalho legado baseado em CSV.

## Estado da revisão (2025-09-25)

- [ ] Implementado no código-base. Embora exista um esboço de `scripts/migrate_review_csv.py`, a CLI (`tools/feedback_cli.py`) ainda aceita parâmetros baseados em CSV por padrão e a documentação não foi atualizada para exigir o modo banco de dados, portanto a migração/decomissionamento não ocorreu.

## Objetivo
Migrar os datasets `review.csv` existentes para o novo banco de dados, atualizar a documentação e os processos, e desativar os caminhos legados da CLI e do fluxo de trabalho baseados em CSV, uma vez que o novo fluxo de trabalho orientado ao banco de dados esteja validado.

## Escopo
- Construir um script de migração para ingerir os arquivos `review.csv` históricos (e artefatos relacionados) nas tabelas do banco de dados (`documents`, `annotations`, `training_runs`).
- Fornecer utilitários de verificação (relatórios de contagem, resumos de diferenças) para garantir a integridade da migração.
- Remover os comandos/flags da CLI legados que operam exclusivamente em CSV e atualizar as ferramentas para exigir o modo de banco de dados.
- Atualizar a documentação (READMEs, guias) para indicar que o caminho do CSV foi descontinuado/removido.
- Adicionar "guardrails"/testes para evitar a reintrodução do caminho do CSV (por exemplo, levantando erros se as flags de CSV forem passadas).

**Fora do escopo:**
- Mudanças no núcleo do banco de dados ou da API (realizadas nos Planos 38-41).
- Automação de arquivamento/backup de longo prazo.

## Arquivos afetados
- `scripts/migrate_review_csv.py` (novo)
- `tools/feedback_cli.py` (a ser modificado)
- `docs/USER_GUIDE.md`
- `docs/feedback/pdf_annotation.md`
- `docs/refactor/pr32-refactor-spa-blueprint.md`
- `README.md`
- `docs/diagrams/ai_builder_db_flow.mmd`
- `tests/` (novos testes de regressão)

## Critérios de aceitação
1. O script de migração deve importar os dados legados do CSV para o banco de dados com um relatório de validação.
2. Todos os comandos da CLI devem operar exclusivamente com identificadores do banco de dados; as flags de CSV devem ser removidas.
3. A documentação deve indicar claramente que o fluxo de trabalho com CSV foi descontinuado e descrever os passos da migração.
4. Testes automatizados devem confirmar que o caminho do CSV não está mais disponível (e levanta um erro útil se for tentado).
5. Os diretórios de artefatos CSV antigos devem ser marcados como arquivados (ou removidos) após a migração.

## Testes manuais
- Executar `poetry run python scripts/migrate_review_csv.py --glob "reports/feedback/*.csv" --dry-run`.
- Executar o script sem "dry-run" e inspecionar as contagens no banco de dados.
- Exercitar os comandos da CLI para confirmar que o modo "somente banco de dados" funciona e que as flags de CSV causam erros.
- Revisar a documentação para consistência.

## Riscos e mitigação
- **Risco**: A migração de dados pode falhar para alguns arquivos CSV malformados.
- **Mitigação**: O script de migração deve ter um tratamento de erros robusto, registrar os arquivos que falharam e fornecer um modo "dry-run" para validação antes da execução.

## Notas adicionais
Este plano é a continuação direta do Plano 41 e finaliza a transição para um fluxo de trabalho totalmente baseado em banco de dados.
