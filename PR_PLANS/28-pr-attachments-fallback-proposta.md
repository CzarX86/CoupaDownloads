# PR 28 — Fallback de anexos via PR (requisition)

- Status: bloqueada (aguardando PR 53)
- Implementação: pendente
- Data: 2025-09-24
- Responsáveis: Equipe CoupaDownloads (dev a designar)
- Observações: atualização alinhada ao estado atual do `Downloader` baseado em Selenium. Número atualizado para versão 2 do plano.
- Revisão: 2

## Objetivo

Permitir que o fluxo de download continue obtendo anexos quando uma página de Purchase Order (PO) não possui arquivos, reutilizando a página de Purchase Requisition (PR) de origem como fonte secundária. O comportamento atual simplesmente encerra o processamento com mensagem de "No attachments found", mesmo quando a requisição possui anexos úteis para o time de compras.

## Escopo

- Introduzir uma verificação condicional no `Downloader.download_attachments_for_po` para detectar ausência de anexos na PO e navegar até a PR correspondente.
- Reaproveitar o mecanismo existente de descoberta e clique em anexos também na tela de PR, mantendo contadores e mensagens consistentes.
- Garantir que os arquivos baixados pela PR sejam gravados na mesma pasta gerenciada pelo `FolderHierarchyManager`, sem alterar convenções de nomenclatura ou sufixos de status já adotados no `Core_main`.
- Expor no `Config` os seletores e a flag de ativação (`PR_FALLBACK_ENABLED`) para permitir ajustes rápidos sem alterar código.

Fora de escopo:
- Refatorações amplas do `BrowserManager` ou do gerenciamento paralelo de abas/processos.
- Mudanças em fluxos de CSV, feedback loop ou pipeline Playwright.
- Revisão de nomenclatura de pastas ou reorganização do diretório `Downloads`.

## Arquivos afetados

- `src/core/downloader.py`: adicionar lógica de fallback, logs e coleta da URL final.
- `src/core/config.py`: incluir flag `PR_FALLBACK_ENABLED` e listas de seletores CSS/XPath para localizar o link de requisição.
- `src/core/browser.py` (se necessário): apenas caso surjam ajustes de utilitários de navegação ou waits reaproveitados pela nova rotina.
- `docs/ADR` (avaliar): somente se a estratégia de fallback alterar decisões arquiteturais prévias.

## Critérios de aceitação

- Quando a PO possuir anexos, o fluxo permanece idêntico ao atual: não deve haver navegação extra nem regressão em contadores ou mensagens.
- Para uma PO sem anexos, com fallback habilitado e link de PR disponível:
  - O sistema deve abrir a página de PR, reutilizar o método `_find_attachments` e acionar o download com a mesma robustez (cliques, JavaScript fallback, etc.).
  - `attachments_found` e `attachments_downloaded` refletem a quantidade obtida na PR, e `coupa_url` retorna a URL da página onde os anexos foram encontrados.
  - A pasta final permanece a mesma criada antes do fallback, incluindo eventuais sufixos aplicados no encerramento (`_COMPLETED`, `_NO_ATTACHMENTS`, etc.).
- Caso a PR também não tenha anexos ou o link não seja localizado, o fluxo retorna "No attachments found" com `success=True`, sem lançar exceções e com mensageria clara no log.
- O fallback pode ser desativado via variável de ambiente `PR_FALLBACK_ENABLED=false`, restabelecendo o comportamento anterior.

## Testes manuais

- Executar `poetry run python -m src.Core_main` com uma planilha que contenha:
  - PO com anexos próprios (verificar ausência de fallback e contadores).
  - PO sem anexos, mas com PR contendo arquivos (validar downloads, renomeação da pasta e contadores > 0).
  - PO sem anexos e PR inexistente ou também vazia (confirmar retorno "No attachments found").
- Repetir o cenário principal com `PR_FALLBACK_ENABLED=false` para garantir que o recurso é opcional e que não há navegação extra.
- Monitorar o CSV de controle em `data/control` e os logs gerados para certificar que não houve duplicidade de registros ou travamentos entre processos.

## Riscos e mitigação

- **Seletores frágeis para localizar a PR**: mitigar utilizando múltiplos seletores configuráveis e validando em ambientes diferentes antes do rollout.
- **Latência extra na troca de página**: incorporar logs claros e considerar um timeout curto para evitar travar workers quando o link não existe.
- **Downloads duplicados**: garantir que, ao retornar para a PO ou reutilizar `_find_attachments`, não haja reprocessamento quando a PO já tinha anexos.
- **Impacto em execuções paralelas**: validar que a navegação adicional não interfere na limpeza do `BrowserManager` nem em bloqueios do EdgeProfile (workers já desabilitam perfil compartilhado por padrão).

## Notas adicionais

- A implementação deve respeitar o padrão de logs em inglês presente no `Downloader` (ex.: `print("No attachments found")`), apenas acrescentando mensagens focadas no fallback com ícones já utilizados.
- Caso a busca de PR exija novas dependências (p.ex. BeautifulSoup), será necessária reavaliação, mas a intenção é permanecer apenas com Selenium.
- O design detalhado desta proposta está documentado em `PR_PLANS/28-pr-attachments-fallback-design-doc.md` e deve ser lido antes da execução.

## Dependências

- Bloqueada pela PR 53 — endurecimento da detecção de página de erro de PO.
