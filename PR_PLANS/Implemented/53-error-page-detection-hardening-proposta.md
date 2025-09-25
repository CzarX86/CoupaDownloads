# PR 53 — Endurecer detecção de página de erro de PO

- Status: implementing
- Implementação: em progresso
- Data: 2025-09-24
- Responsáveis: Equipe CoupaDownloads (dev a designar)
- Observações: requisito prévio para liberar a entrega da PR 28 (fallback de anexos via PR). Plano atualizado após implementação inicial no `Downloader`.

## Objetivo

Reduzir ao mínimo o tempo para identificar páginas de erro do Coupa ("Oops! We couldn’t find what you wanted" e variações), evitando tentativas de fallback ou descoberta de anexos sobre uma página inválida. A meta é encurtar a detecção para ~1 segundo, retornar erro estruturado antes de qualquer lógica adicional e padronizar os status/mensagens persistidos no `input.csv`.

## Escopo

- Centralizar a detecção em um helper dedicado no `Downloader`, reutilizado por outros módulos que navegam para páginas de PO/PR.
- Substituir a leitura direta de `driver.page_source` por uma verificação iterativa com `WebDriverWait`, usando seletores CSS/XPath do template Coupa e permitindo interrupção assim que o DOM evidencia a mensagem.
- Ajustar variáveis em `Config` para definir `ERROR_PAGE_CHECK_TIMEOUT`, `ERROR_PAGE_READY_CHECK_TIMEOUT`, `ERROR_PAGE_WAIT_POLL` e listas de seletores multilíngues (`ERROR_PAGE_*_SELECTORS`).
- Registrar logs estruturados e enriquecer o retorno com `status_code`, `status_reason`, `errors` e mensagens amigáveis para impedir fallback na PR 28 e aprimorar os dados registrados no `input.csv`.
- Remover a restrição de extensões permitidas, garantindo que todos os anexos listados sejam baixados (com nomes sanitizados) e reportando problemas por anexo.

Fora de escopo:
- Alterações em fluxos Playwright ou pipelines paralelos.
- Mudança do comportamento padrão de timeout das páginas válidas (somente o fast-fail de erro).
- Revisões no processo de login ou em credenciais.

## Arquivos afetados

- `src/core/downloader.py`: helper `_detect_error_page`, espera em duas fases, retorno estruturado (`status_code`, `status_reason`, `errors`) e download sem filtro de extensão.
- `src/core/config.py`: novos seletores, timeouts e parâmetros de polling para páginas de erro.
- `src/Core_main.py`: consumo do novo payload, mensagens human-friendly e atualização do CSV com status diferenciados.
- `src/core/excel_processor.py`: ícones e mensagens resumidas para novos status (`PO_NOT_FOUND`, `PARTIAL`).
- Documentação: atualizar `PR_PLANS/28-pr-attachments-fallback-*` para registrar dependência (concluído nesta revisão).

## Critérios de aceitação

- Páginas de erro conhecidas são detectadas em até 2 segundos em ambientes de teste (log evidencia o marcador encontrado, tempo decorrido e `status_code=PO_NOT_FOUND`).
- O fallback de PR (PR 28) permanece bloqueado quando a detecção retorna erro; o fluxo encerra com mensagem clara e não tenta `_find_attachments`.
- A solução suporta versões localizadas da mensagem (ex.: inglês, português) via markers configuráveis e seletores CSS/XPath.
- O tempo de detecção para POs válidas não piora de forma perceptível (< 100 ms adicional) e o CSV registra status finais diferenciados (`PO_NOT_FOUND`, `NO_ATTACHMENTS`, `PARTIAL`, `FAILED`).
- Todos os anexos listados na PO/PR são clicados, independentemente da extensão, preservando nomes sanitizados e mensagens de erro resumidas por item.

## Testes manuais

- Navegar para uma PO inexistente e validar logs: detecção em até 2s, `status_code=PO_NOT_FOUND`, `status_reason=COUPA_ERROR_PAGE`, CSV com mensagem amigável.
- Navegar para uma PO válida (com e sem anexos) e conferir que não há falso positivo e que os status `COMPLETED`/`NO_ATTACHMENTS` são registrados corretamente.
- Forçar cenário de downloads parciais (erro em um anexo específico) e verificar mensagem resumida (`errors`) e `status_code=PARTIAL`.
- Ajustar `ERROR_PAGE_CHECK_TIMEOUT=0` para validar comportamento de bypass via env var, confirmando que o fallback não executa devido ao `status_reason` retornado.

## Riscos e mitigação

- **Falsos positivos com mensagens parciais**: incluir testes unitários cobrindo diferentes idiomas e variações do template Coupa.
- **Aumento de custo de navegação**: limitar o wait a 2s e interromper imediatamente ao encontrar matches.
- **Manutenção de seletores Coupa**: documentar origem dos seletores e adicionar fallback para string matching caso o HTML mude.

## Dependências

- Libera PR 28 — fallback de anexos via PR (não deve ser implementada antes desta melhoria).
- Leva em conta entregas já concluídas na PR 24 (fast PO not-found detection); esta PR substitui o polling com string match simples por uma verificação orientada a DOM.

## Notas adicionais

- Não foram encontradas PRs abertas sobre o mesmo tema; a PR 24 correspondente encontra-se em `Implemented/` e serve como contexto histórico.
- Após a implementação, avaliar se faz sentido publicar um ADR sobre o padrão de "Fast error detection" para Coupa.
