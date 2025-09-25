# Treinamento Assistido por LLM (Fluxo PDF-First)

> 💡 **Contexto**: o assistente LLM agora está embutido no PDF Training Wizard. Este documento descreve como habilitar o painel na UI, quais variáveis de ambiente controlar e como automatizar o processo via API. Ao final há um apêndice sobre o fluxo legado baseado em CSV para referência histórica.

## Visão geral do painel

1. **Upload e pré-processamento** – após enviar o PDF pelo wizard, o backend cria a anotação inicial e registra as entidades detectadas.
2. **Geração de sugestões** – no painel lateral “LLM Helper”, clique em **Generate suggestions**. Um job assíncrono (`JobType.support_llm`) é criado para coletar contexto, montar o prompt e chamar o modelo configurado.
3. **Revisão humana** – as sugestões são exibidas em uma tabela com campo, valor proposto, confiança e observações. Use os botões de aceitar/rejeitar por linha; apenas as decisões aprovadas são persistidas.
4. **Datasets atualizados** – ao concluir a revisão, gere um treinamento ou exporte datasets diretamente pela UI. Os artefatos (`supervised.jsonl`, `st_pairs.jsonl`, modelos) refletem as correções aplicadas.

> ✅ **Boas práticas**
> - Execute o helper apenas depois do pré-processamento terminar (status `SUCCEEDED`).
> - Trabalhe com lotes menores de documentos para facilitar auditoria.
> - Revise os custos estimados exibidos no painel antes de habilitar chamadas reais.

## Variáveis de ambiente

| Variável | Default | Descrição |
| --- | --- | --- |
| `PDF_TRAINING_LLM_PROVIDER` | `deepseek` | Provedor suportado (`deepseek`, `openai`, etc.). |
| `PDF_TRAINING_LLM_MODEL` | `deepseek-chat` | Modelo solicitado ao provedor. |
| `PDF_TRAINING_LLM_DRY_RUN` | `true` | Quando `true`, gera respostas simuladas (sem chamadas externas). |
| `PDF_TRAINING_LLM_FIELDS` | – | Lista separada por vírgulas com os campos que devem receber sugestões. |
| `PDF_TRAINING_LLM_TEMPERATURE` | `0.0` | Temperatura usada na chamada oficial ao provedor. |
| `PDF_TRAINING_LLM_TOP_P` | `0.9` | Parâmetro de amostragem complementar à temperatura. |
| `PDF_TRAINING_LLM_TIMEOUT` | `30.0` | Timeout (segundos) para chamadas reais. |
| `PDF_TRAINING_LLM_API_KEY` | – | Chave explícita do provedor; se ausente, o helper tenta `DEEPSEEK_API_KEY` ou `OPENAI_API_KEY`. |

Para ambientes de QA, mantenha `PDF_TRAINING_LLM_DRY_RUN=true` e ajuste `PDF_TRAINING_LLM_FIELDS` para focar em poucos campos. Em produção, configure a chave correspondente e monitore o painel de custos.

## Automação via API

O frontend utiliza endpoints dedicados. Eles podem ser consumidos por integrações externas:

- **Disparar sugestões**
  ```bash
  curl -X POST \
    "http://localhost:8008/api/pdf-training/documents/<document_id>/support/llm" \
    -H "Content-Type: application/json" \
    -d '{"fields": ["supplier_name", "contract_type"], "provider": "deepseek"}'
  ```
- **Consultar resultado**
  ```bash
  curl "http://localhost:8008/api/pdf-training/documents/<document_id>/support/llm"
  ```
- **Acompanhar o job**
  ```bash
  curl "http://localhost:8008/api/pdf-training/jobs?resource_type=document&resource_id=<document_id>"
  ```

Os payloads retornam a decisão do modelo (`decision`), justificativas (`rationale`), custos estimados (`estimated_cost`) e os valores propostos. Combine com o endpoint `/documents/{id}/entities` para exibir os dados atuais lado a lado.

## Perguntas frequentes

**Posso salvar automaticamente as sugestões?**
: Não. Mesmo no fluxo API o helper apenas escreve recomendações. A aprovação final continua manual na UI para preservar o controle HITL.

**Como forçar uma execução síncrona em testes?**
: Defina `PDF_TRAINING_FORCE_SYNC_JOBS=true`. Os jobs de suporte passam a rodar no mesmo processo, facilitando asserts em pytest.

**É possível usar outro provedor?**
: Sim. Desde que exista suporte no módulo `tools.llm_critique`, basta setar `PDF_TRAINING_LLM_PROVIDER`/`MODEL` e fornecer a chave via variável de ambiente correspondente.

## Apêndice A — Fluxo legado baseado em CSV

> ⚠️ **Descontinuado**: as instruções abaixo descrevem o antigo pipeline `review.csv` + `feedback_cli`. Use apenas para consultar históricos ou reproduzir experimentos antigos.

1. Gerar críticas com `tools/llm_critique.py`, produzindo colunas `_llm_suggested` em uma cópia do CSV.
2. Opcionalmente criar pares sintéticos com `tools/self_augment.py`.
3. Executar o modo gamificado de `feedback_cli.py train-st` para aceitar/rejeitar sugestões e regenerar datasets.

O arquivo `tools/feedback_cli.py` atual apenas imprime uma mensagem informando que o fluxo foi removido. Para qualquer implementação nova, baseie-se na UI ou nos endpoints documentados neste guia.
