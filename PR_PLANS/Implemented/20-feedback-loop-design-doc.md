# Arquitetura 20 — Feedback loop (HITL): ingestão de CSV anotado, geração de datasets e avaliação

- Status: draft
- Data: 2025-09-23
- Responsáveis: TBD
- Observações: Baseado no plano `20-feedback-loop-PR.md`.

## Resumo executivo
Estabelecer um ciclo leve e prático de Human‑in‑the‑Loop (HITL) para:
- Preparar um CSV de revisão com colunas “_pred/_gold/_status” por campo.
- Ingerir o CSV anotado e gerar artefatos de treino (JSONL) e relatórios de métricas.
- Disparar fine‑tuning opcional de Sentence Transformers usando os dados anotados.
- Não alterar defaults do pipeline atual; apenas adicionar ferramentas auxiliares e flags.

## Objetivos e não objetivos
- Objetivos: listar metas específicas do fluxo.
- Não objetivos: registrar explicitamente o que fica fora do escopo.

## Estado atual
- TODO descrever comportamento e limitações atuais.

## Visão proposta
- Componentes & responsabilidades:
  Em `embeddinggemma_feasibility` e `tools/` (novo):
  - CLI de feedback com subcomandos: `prepare`, `ingest`, `eval`, `train-st`, `export-labelstudio` (opcional).
  - Conversores: CSV (pred) → CSV (review) → JSONL supervisionado e pares para ST.
  - Métricas por campo: precisão/cobertura por documento e agregado, com reporte em JSON/Markdown.
  - Integração leve com os utilitários existentes:
  - Reusar `ContractDataTrainer` para gerar `training_analysis.json` (padrões/estatísticas) com base no CSV anotado.
  - Invocar o customizer de ST para fine‑tuning com os pares gerados (sem mudar defaults).

  Fora de escopo:
  - Alterar prompts LLM ou a ordem/estratégia do extrator principal.
  - Adicionar novos campos sem plano próprio.
  - Integrar UIs externas pesadas (Label Studio/Doccano) além de um export simples opcional.

- Fluxo (sequência/mermaid):
  - TODO documentar passo a passo ou adicionar diagrama.

- Dados & contratos:
  - TODO listar estruturas de dados, esquemas ou interfaces afetadas.

## Plano de implementação
- TODO detalhar fases, checkpoints e possíveis feature flags.
- TODO definir estratégia de rollback.

## Impactos
- Performance: TODO
- Segurança: TODO
- Operações / suporte: TODO

## Testes e evidências
- TODO planejar testes automatizados e manuais, com métricas de aceitação.

## Decisões, trade-offs e alternativas consideradas
- TODO registrar principais escolhas arquiteturais.

## Pendências e próximos passos
- TODO listar itens adicionais antes da implementação.
