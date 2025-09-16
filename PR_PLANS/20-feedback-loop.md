# PR 20 — Feedback loop (HITL): ingestão de CSV anotado, geração de datasets e avaliação

## Objetivo
Estabelecer um ciclo leve e prático de Human‑in‑the‑Loop (HITL) para:
- Preparar um CSV de revisão com colunas “_pred/_gold/_status” por campo.
- Ingerir o CSV anotado e gerar artefatos de treino (JSONL) e relatórios de métricas.
- Disparar fine‑tuning opcional de Sentence Transformers usando os dados anotados.
- Não alterar defaults do pipeline atual; apenas adicionar ferramentas auxiliares e flags.

## Escopo
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

## Análise de bibliotecas (usar se adequado)
- Typer/Click: facilitaria o CLI, porém evita‑se dependência extra; usaremos `argparse` (stdlib) para manter leve.
- Hugging Face Datasets: útil para splits/serialização; manteremos suporte opcional (try/except) sem tornar obrigatório.
- Pandera/Great Expectations: validação de schema; manteremos validação com pandas (sem deps novas).
- Label Studio: ótimo para anotação HITL, mas pesado. Incluiremos apenas um exportador simples de tarefas (JSON) compatível, sem adicionar SDK.

Decisão: baseline 100% stdlib + pandas; integrações opcionais não bloqueiam o fluxo.

## Arquivos afetados (esperados)
- Add: `tools/feedback_cli.py` (CLI: prepare/ingest/eval/train-st/export-labelstudio)
- Add: `tools/feedback_utils.py` (helpers: schema, amostragem, conversões, métricas)
- Add: `reports/feedback/` (saídas geradas em runtime)
- Update (leve, não‑breaking): `embeddinggemma_feasibility/sentence_transformer_customizer.py` (aceitar dataset externo opcional nos métodos públicos; via parâmetro)
- Update (leve, não‑breaking): `embeddinggemma_feasibility/contract_data_trainer.py` (expor função utilitária para rodar análise a partir de um DataFrame)
- Docs: `embeddinggemma_feasibility/README.md` (seção "Feedback/HITL"), `docs/HITL_FEEDBACK_WORKFLOW.md`

## Pseudodiff (representativo)
```diff
+ tools/feedback_cli.py
+ -------------------------------------------------
+ if __name__ == "__main__":
+   # Subcomandos: prepare | ingest | eval | train-st | export-labelstudio
+   # argparse com rotas:
+   #  - prepare:  --pred-csv reports/advanced_*.csv --out review.csv --fields "contract_name,contract_type,..." --sample 50
+   #  - ingest:   --review-csv review.csv --out-dir datasets/
+   #  - eval:     --review-csv review.csv --report-dir reports/feedback/
+   #  - train-st: --dataset datasets/st_pairs.jsonl --output models/st_custom_v1
+   #  - export-labelstudio: --review-csv review.csv --out tasks.json
+
+ tools/feedback_utils.py
+ -------------------------------------------------
+ def make_review_csv(pred_csv, out_csv, fields, sample=None):
+   # Lê CSV predito -> cria colunas *_pred, *_gold, *_status; preserva metadados (arquivo, confiança)
+   # Amostragem opcional por documento/PO
+
+ def ingest_review_csv(review_csv, out_dir):
+   # Valida schema; gera:
+   #  - supervised.jsonl (por doc, labels gold)
+   #  - st_pairs.jsonl (pares positivos/negativos por categoria)
+   #  - training_analysis.json (via ContractDataTrainer)
+
+ def evaluate_review_csv(review_csv, report_dir):
+   # Compara *_pred vs *_gold quando *_status ∈ {OK, CORRECTED, NEW}
+   # Gera metrics.json e metrics.md com precisão/cobertura por campo
+
+ def export_labelstudio_tasks(review_csv, out_json):
+   # Gera JSON de tarefas simples (texto + campos alvo) compatível para import
+
*** a/embeddinggemma_feasibility/sentence_transformer_customizer.py
--- b/embeddinggemma_feasibility/sentence_transformer_customizer.py
@@ class ContractSentenceTransformerCustomizer:
- def create_training_data(self):
+ def create_training_data(self, pairs_jsonl: str | None = None):
+   # Se pairs_jsonl for informado, carregar pares; senão, derivar dos dados existentes

*** a/embeddinggemma_feasibility/contract_data_trainer.py
--- b/embeddinggemma_feasibility/contract_data_trainer.py
@@ class ContractDataTrainer:
- def save_training_data(self, output_file: str):
+ def save_training_data(self, output_file: str, df: pd.DataFrame | None = None):
+   # Se df fornecido, usar diretamente (permite integração com ingestão sem re‑ler CSV)
```

## Critérios de Aceitação
- `tools/feedback_cli.py` disponível e funcional com `argparse`, sem dependências novas obrigatórias.
- `prepare` cria um CSV de revisão com colunas `*_pred`, `*_gold`, `*_status` para os campos selecionados e preserva colunas de contexto (`source_file`, `extraction_confidence`, `extraction_method`).
- `ingest` valida o CSV anotado e produz:
  - `datasets/supervised.jsonl` (um objeto por documento com `{source_file, labels:{...}}`).
  - `datasets/st_pairs.jsonl` (pares positivos/negativos para ST por categorias‑chave).
  - `data/training_analysis.json` (padrões/distribuições) reaproveitando `ContractDataTrainer`.
- `eval` gera `reports/feedback/metrics.json` e `metrics.md` com precisão/cobertura por campo e sumário geral.
- `train-st` aceita `--dataset` (ou usa padrão gerado pelo `ingest`) e salva modelo em `embeddinggemma_feasibility/models/st_custom_vX/` sem alterar defaults.
- Documentação inclui passos claros do fluxo HITL e exemplos de uso.

## Testes Manuais Mínimos
1) Preparação de revisão
   - Rodar `feedback_cli.py prepare --pred-csv <csv_do_pipeline> --out review.csv --fields "contract_name,contract_type,sow_value_eur,pwo_number,managed_by" --sample 30`.
   - Abrir `review.csv` e confirmar colunas `*_pred/_gold/_status` + metadados.
2) Ingestão e datasets
   - Preencher algumas linhas `*_gold` e `*_status` (`OK`, `CORRECTED`, `NEW`).
   - Rodar `feedback_cli.py ingest --review-csv review.csv --out-dir datasets/` e verificar `supervised.jsonl`, `st_pairs.jsonl`, `training_analysis.json`.
3) Avaliação
   - Rodar `feedback_cli.py eval --review-csv review.csv --report-dir reports/feedback/` e conferir `metrics.md` com per‑campo.
4) Treino opcional ST
   - Rodar `feedback_cli.py train-st --dataset datasets/st_pairs.jsonl --output embeddinggemma_feasibility/models/st_custom_v1`.
   - Confirmar criação do diretório do modelo.
5) Export opcional para Label Studio
   - Rodar `feedback_cli.py export-labelstudio --review-csv review.csv --out tasks.json` e validar JSON básico.

## Mensagem de Commit e Branch Sugeridos
- Branch (plan): `plan/20-feedback-loop`
- Commit (plan): `docs(pr-plan): PR 20 — feedback loop (HITL ingest, datasets, eval, optional ST training)`
- Branch (impl): `feat/20-feedback-loop`

## Checklist
- [x] Objective and Scope are clear and limited.
- [x] Affected files listed.
- [x] Pseudodiff (pequeno e representativo) incluído.
- [x] Acceptance criteria e minimal manual tests.
- [x] Suggested commit message and branch name.
