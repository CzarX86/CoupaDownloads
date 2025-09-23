# Arquitetura 9 — Edge: permitir múltiplos downloads automáticos (automatic_downloads)

- Status: draft
- Data: 2025-09-23
- Responsáveis: TBD
- Observações: Baseado no plano `09-edge-automatic-downloads-PR.md`.

## Resumo executivo
- Reduzir prompts internos e falhas silenciosas quando vários arquivos são disparados rapidamente, habilitando múltiplos downloads automáticos no Edge (Chromium) via preferências do navegador.

## Objetivos e não objetivos
- Objetivos: listar metas específicas do fluxo.
- Não objetivos: registrar explicitamente o que fica fora do escopo.

## Estado atual
- TODO descrever comportamento e limitações atuais.

## Visão proposta
- Componentes & responsabilidades:
  - Projeto principal `src/`:
  - `src/core/browser.py`: adicionar a preferência `"profile.default_content_setting_values.automatic_downloads": 1` ao dicionário de prefs do Edge em:
  - `_create_browser_options(...)`
  - `_create_browser_options_without_profile(...)`

  - Arquivos impactados:
    - `src/core/browser.py`

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
