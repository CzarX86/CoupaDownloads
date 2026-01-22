# Arquitetura 53 — Endurecer detecção de página de erro de PO

- Status: implementing
- Data: 2025-09-24
- Responsáveis: Equipe CoupaDownloads (dev a designar)
- Observações: pré-requisito da PR 28, estende a solução da PR 24 (fast PO not-found detection). Documento atualizado para refletir implementação inicial.

## Resumo executivo

A detecção anterior de páginas Coupa "Oops! We couldn’t find what you wanted" lia o `page_source` logo após `driver.get`. Quando o HTML demorava a ser renderizado, o teste falhava em detectar a página de erro, prosseguia para `_find_attachments` e permitia que o fallback de PR tentasse operar em uma página inválida. A implementação atual encapsula a detecção em um helper com `WebDriverWait`, suporta múltiplos seletores e reduz o timeout para no máximo 2 segundos, garantindo retorno precoce, bloqueio do fallback e padronização dos status/mensagens persistidos (incluindo novos códigos `PO_NOT_FOUND`, `PARTIAL`).

## Objetivos e não objetivos

**Objetivos**
- Detectar todas as variantes conhecidas do template de erro Coupa em ≤ 2 segundos.
- Expor um método reutilizável (`_detect_error_page`) que devolva um objeto rico (`ErrorPageInfo`) com marcador, fonte, fase e tempo decorrido.
- Interromper o fluxo normal imediatamente ao detectar erro, sem chamar `_find_attachments` nem `_navigate_to_pr_from_po`, e devolver dados suficientes para persistência (`status_code`, `status_reason`, `errors`).
- Garantir que todos os anexos listados sejam clicados, independentemente da extensão informada pelo Coupa, com mensagens de erro curtas por anexo.

**Não objetivos**
- Não alterar a mecânica de navegação ou criação de abas além da detecção.
- Não cobrir mensagens genéricas de HTTP (502/504) — permanecem sob responsabilidade do timeout padrão.
- Não implementar mecanismos de retry automático.
- Não revisar, nesta fase, componentes Playwright ou scripts legados em `MyScript/` (ficam como follow-up opcional).

## Estado atual

- `Downloader.download_attachments_for_po` agora executa `_detect_error_page` em duas fases (imediata + pós-readyState) e retorna payload estruturado com `status_code`, `status_reason`, `errors`, `error_info`.
- `Config` oferece marcadores multilíngues, seletores CSS/XPath e timeouts configuráveis (`ERROR_PAGE_CHECK_TIMEOUT`, `ERROR_PAGE_READY_CHECK_TIMEOUT`, `ERROR_PAGE_WAIT_POLL`).
- `_download_attachment` removeu filtro de extensões, registra erros amigáveis por anexo e devolve sumários concisos.
- `Core_main` e `ExcelProcessor` passaram a interpretar os novos campos e atualizar o `input.csv` com mensagens human-friendly e ícones adicionais.
- Scripts legados (`MyScript/browser_tab_manager.py`) ainda usam detecção antiga e foram anotados como follow-up opcional.

## Visão proposta

### Componentes e responsabilidades

- `src/core/downloader.py`: implementa `_detect_error_page`, `_wait_for_dom_ready`, `_summarize_download_errors` e retorno estruturado.
- `src/core/config.py`: expõe novos marcadores/seletores e timeouts de detecção.
- `src/Core_main.py`: consome `status_code`/`status_reason`, humaniza exceções (`_humanize_exception`), registra mensagens curtas no CSV e renomeia pastas com novos sufixos.
- `src/core/excel_processor.py`: adiciona ícones para `PO_NOT_FOUND`, mantém mensagens concisas no `ERROR_MESSAGE` e na saída do console.
- Follow-up sugerido: alinhar `MyScript/browser_tab_manager.py` e documentação de agentes quando o fallback da PR 28 for retomado.

### Fluxos (texto)

1. `driver.get(url)`
2. `_detect_error_page(driver)` executa `WebDriverWait` ≤ 2s, verificando:
   - `driver.title` (strings "Oops"/"Not Found").
   - Presença de seletores configurados via `find_elements`.
   - Fallback para `page_source` contains markers.
3. Se erro detectado → log estruturado + retorno `success=False`.
4. Caso contrário → seguir fluxo tradicional (`_find_attachments`, fallback PR, etc.).

### Dados e contratos

- Estruturar retorno como `ErrorPageInfo = TypedDict('ErrorPageInfo', {'marker': str, 'selector': str | None, 'elapsed': float})`.
- Armazenar `ErrorPageInfo` em `result['error_info']` quando disponível (sem quebrar compatibilidade: chave opcional).
- Permitir que callers externos ignorem a info mantendo dicionário atual.

## Plano de implementação

1. **Configuração** (concluído): novos marcadores, seletores e timeouts (`*_CHECK_TIMEOUT`, `*_READY_CHECK_TIMEOUT`, `*_WAIT_POLL`).
2. **Downloader** (concluído): `_detect_error_page` em duas fases, retorno estruturado, remoção do filtro de extensões e mensagens resumidas.
3. **Orquestração** (concluído): adequações em `Core_main` e `excel_processor` para refletir status/mensagens, incluindo humanização de exceções.
4. **Documentação** (em andamento): alinhamento deste plano e atualização da PR 28 como dependente; avaliar atualização de `AGENTS.md` em nova rodada.
5. **Follow-up opcional**: estender helper a `MyScript/browser_tab_manager.py` e suites Playwright.

Rollback: desabilitar via env vars (`ERROR_PAGE_CHECK_TIMEOUT=0` + `ERROR_PAGE_READY_CHECK_TIMEOUT=0`) ou, se necessário, guarda adicional para retornar à verificação antiga.

## Impactos

- **Performance**: leve overhead (polling até 2s) apenas em páginas inválidas; páginas válidas mantêm detecção quase instantânea (readyState + busca de anexos).
- **Segurança**: nenhuma alteração — operamos nas mesmas páginas Coupa autenticadas.
- **Operações / suporte**: logs agora registram marcador, fase, fonte e resumo de erros por anexo, facilitando suporte e auditoria do CSV.

## Testes e evidências

- Unit tests fakes (`selenium.webdriver` mockado) cobrindo cenários: erro imediato, erro após 1s, página válida (pendente de criação para solidificar regressão futura).
- Testes manuais com POs reais (inexistente vs válido) registrando tempo pelo log e verificando status/mensagens no `input.csv`.
- Comparação de métricas antes/depois (tempo médio até retorno em POs inválidas) e registro de cenários `PARTIAL`.

## Decisões, trade-offs e alternativas consideradas

- Optou-se por `WebDriverWait` em vez de pooling manual com `time.sleep` para integrar com a API padrão do Selenium e permitir custom ExpectedConditions.
- Alternativa descartada: interceptar requisições de rede via DevTools. Considerada overkill e adicionaria dependência em `selenium-wire`.
- Permanece fallback para string matching e checagem de título caso os seletores mudem.
- Manteve-se o logging via `print` nesta fase para visibilidade no CLI; migração para logger estruturado fica como melhoria futura.

## Pendências e próximos passos

- Confirmar com usuários se há variações localizadas adicionais (francês/espanhol) e adicioná-las aos markers.
- Atualizar documentação (`AGENTS.md`) quando expusermos os novos env vars a todo o time.
- Após entrega, coordenar com PR 28 para revalidar o fluxo end-to-end e decidir se `_navigate_to_pr_from_po` absorve o helper.
- Criar relato de implementação quando a fase de testes for concluída e mover a PR para `Implemented/`.
