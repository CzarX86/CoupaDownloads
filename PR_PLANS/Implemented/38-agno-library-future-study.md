# PR Plan 38 — Agno Library Future Study
- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: TBD
- Observações: 


## Objective
Evaluate how the Python Agno agent framework could enhance CoupaDownloads’ automation, research surfaces where Agno’s capabilities align with current architecture, and outline a recommendation captured in `docs/future-studies/` for stakeholders.

**Resumo em pt-BR:** Vamos estudar profundamente a biblioteca Agno (framework de agentes para Python), mapear como ela poderia acelerar os fluxos do CoupaDownloads e produzir uma análise escrita na pasta `docs/future-studies/`, sem implementar integração agora.

## Scope
- Research Agno’s feature set (agent orchestration, tool calling, memory, async execution) and its maturity/status.
- Map Agno’s capabilities to current project needs (ETL/download workers, RAG flows, orchestration scripts, CLI automation).
- Assess technical fit: environment requirements, dependency impact, concurrency model, extensibility.
- Identify potential adoption scenarios (short-term experiments, long-term architecture evolution) and risks.
- Deliver a future study document summarizing findings, comparison tables, diagrams, and actionable next steps.

Out of scope:
- Writing production code that integrates Agno into the repository.
- Changing existing pipelines, dependencies, or runtime defaults.
- Deciding on adoption; this is an exploratory analysis only.

## Affected Files
- `docs/future-studies/` (new directory) — holds future study documents.
- `docs/future-studies/agno-library-evaluation.md` (new) — comprehensive analysis document with sections in pt-BR and diagrams.
- `docs/diagrams/agno-integration.mmd` (new) — Mermaid source for the document’s diagram (if stored separately, otherwise embed in Markdown).
- Optional: `PR_PLANS/Implemented/38-agno-library-future-study.md` (after implementation, move the plan per workflow).

## Approach
1. **Context survey**
   - List current CoupaDownloads workflows that rely on custom orchestration (CLI automation, download workers, RAG, QA loops) by scanning `src/` and docs to anchor the analysis.
   - Capture constraints from `pyproject.toml` (Python version, key dependencies) and runtime expectations (Poetry-managed environment, local-first execution).

2. **Agno research**
   - Review Agno’s official documentation and repository to understand core abstractions (Agents, Tasks, Tools, Memory, Connectors) and runtime model.
   - Note supported models/providers, plugin ecosystem, deployment story, and licensing/maintenance activity.

3. **Fit assessment**
   - Compare Agno’s capabilities with CoupaDownloads needs: agent-based download automation, multi-step workflows, data extraction, feedback loop automation.
   - Analyze integration touchpoints: replacing ad-hoc orchestrators, augmenting CLI flows, bridging to RAG pipeline, coordinating QA tasks.
   - Evaluate operational concerns (dependency weight, async support, tracing/logging, testability, compatibility with BMAD practices).

4. **Deliverable synthesis**
   - Draft the future study document in pt-BR with sections: Introdução, Visão Geral do Agno, Casos de Uso Potenciais, Análise de Ajuste Técnico, Riscos & Mitigações, Roadmap Proposto, FAQ/Glossário.
   - Include a Mermaid diagram summarizing how Agno agents could mediate between existing components, plus a plain-language explainer for newcomers.
   - Provide actionable recommendations (experimentos sugeridos, critérios de go/no-go) aligned with BMAD process (e.g., quais planos futuros abrir se avançar).

5. **Review checklist**
   - Self-proofread for clarity and consistency (pt-BR text, English UI references when needed).
   - Ensure file encoding stays ASCII/UTF-8 without BOM; keep Markdown lint-friendly formatting.
   - Link to relevant existing docs (feedback workflow, RAG architecture) for context.

## Acceptance Criteria
- Future study document lives at `docs/future-studies/agno-library-evaluation.md`, written em pt-BR, referencing English UI terms only when needed.
- Document includes: overview of Agno, comparison to current stack, detailed fit analysis, risks, recommended experimental roadmap, and plain-language explainer.
- At least one Mermaid diagram (inline or referenced) illustrating proposed interactions between Agno and CoupaDownloads components.
- Document highlights dependency considerations (Poetry, version pinning) and potential impact on testing/QA flows.
- Plan file updated/moved to `Implemented` directory after delivering the document (per BMAD workflow).

## Manual Tests
- Visual inspection in Markdown preview to verify headings, tables, and Mermaid diagram render correctly.
- `poetry run python -m compileall docs/future-studies` (optional) to ensure no syntax errors in example code blocks if any are executable.
- Spell-check (manual) focusing on technical terms and Portuguese accents.

## Suggested Branch & Commit
- Branch: `38-agnolib-future-study`
- Commit (initial): `Add Agno future study plan`

```mermaid
flowchart TD
    A[Context survey
    (repositorio atual)] --> B[Estudar biblioteca Agno]
    B --> C[Comparar necessidades x recursos]
    C --> D[Documentar insights
    em future-studies]
    D --> E[Recomendações para próximos planos]
```

### Plain-language explainer
Agno funciona como um "chefe de orquestra" para agentes de IA: você descreve tarefas em etapas, e ele conversa com modelos de linguagem, ferramentas externas e memórias para cumprir essas etapas automaticamente. Em vez de escrever scripts longos que coordenam tudo na unha, o Agno dá blocos prontos para combinar modelos, funções Python e integrações — economizando tempo quando precisamos de fluxos inteligentes que tomam decisões a cada passo.
