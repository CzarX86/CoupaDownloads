# AGENTS — Experimental Workspace

1. **Recapitule antes de agir.** Leia `experimental/docs/README.md` para visão macro e, em seguida, `experimental/docs/HANDOFF.md` para status, pendências e testes recentes.
2. **Aderência ao Spec Driven Development.**
   - Consulte `experimental/.specify/memory/constitution.md`; trate-o como fonte das regras constitucionais (ajuste-o antes de iniciar se ainda contiver placeholders).
   - Para novas demandas, gere o ciclo *spec → plan → tasks* usando os scripts em `experimental/.specify/scripts/bash/`:
     1. `./.specify/scripts/bash/create-new-feature.sh "descrição"` cria branch, diretório em `experimental/specs/` e `spec.md` baseado em `templates/spec-template.md`.
     2. `./.specify/scripts/bash/setup-plan.sh` materializa `plan.md` a partir do template de plano.
     3. Revise/complete `spec.md` e `plan.md` seguindo os checklists dos templates, respeitando os gates da constituição.
     4. Antes de avançar para execução ou geração de tarefas, rode `./.specify/scripts/bash/check-prerequisites.sh --json` (e com `--require-tasks` quando aplicável) para garantir que o estado do feature esteja consistente.
     5. Sempre que finalizar ou atualizar um plano, sincronize agentes com `./.specify/scripts/bash/update-agent-context.sh codex` (ou o agente pertinente) mantendo as seções “MANUAL ADDITIONS”.
  - Armazene `spec.md`, `plan.md`, `relatorio` e demais artefatos de PR em `experimental/specs/[###-slug]/` e em `experimental/docs/PR_Plans/`, prefixando o arquivo com timestamp `yyyymmdd-hhmm`. Após aprovação/implementação, mova o conjunto correspondente para `experimental/docs/PR_Plans/Implemented/`.
3. **Combata drift de contexto.** Se notar respostas vagas, contradições ou latência anômala, pause para atualizar README e HANDOFF com as descobertas antes de continuar.
4. **Documente decisões formais.** Use `docs/architecture/experimental-core.md` para narrativas de design e abra/atualize ADRs sob `docs/adr/` para decisões arquiteturais permanentes.
5. **Ambiente controlado.** Trabalhe dentro do ambiente Poetry (`poetry install`, `poetry run …`). Não crie ambientes paralelos nem altere versões sem aprovação prévia.
6. **Registre testes.** Toda execução relevante deve ser listada em `experimental/docs/HANDOFF.md` com comando, resultado e observações; inclua logs essenciais quando necessário.
7. **Encerramento do turno.** Garanta que README e HANDOFF reflitam comandos recentes, próximos passos e qualquer ajuste de configuração para que o próximo agente retome sem perda de contexto.
