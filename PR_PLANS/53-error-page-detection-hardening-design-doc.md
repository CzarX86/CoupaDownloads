# Arquitetura 53 — Endurecer detecção de página de erro de PO

- Status: draft
- Data: 2025-09-24
- Responsáveis: Equipe CoupaDownloads (dev a designar)
- Observações: pré-requisito da PR 28, estende a solução da PR 24 (fast PO not-found detection).

## Resumo executivo

A detecção atual de páginas Coupa "Oops! We couldn’t find what you wanted" lê o `page_source` logo após `driver.get`. Quando o HTML demora a ser renderizado, o teste falha em detectar a página de erro, prossegue para `_find_attachments` e permite que o fallback de PR tente operar em uma página inválida. Propomos encapsular a detecção em um helper com `WebDriverWait`, suportando múltiplos seletores e reduzindo o timeout para no máximo 2 segundos, garantindo um retorno precoce e bloqueando o fallback.

## Objetivos e não objetivos

**Objetivos**
- Detectar todas as variantes conhecidas do template de erro Coupa em ≤ 2 segundos.
- Expor um método reutilizável (`detect_error_page`) que devolva um objeto rico (`ErrorPageInfo`) com motivo/marcador encontrado.
- Interromper o fluxo normal imediatamente ao detectar erro, sem chamar `_find_attachments` nem `_navigate_to_pr_from_po`.

**Não objetivos**
- Não alterar a mecânica de navegação ou criação de abas além da detecção.
- Não cobrir mensagens genéricas de HTTP (502/504) — permanecem sob responsabilidade do timeout padrão.
- Não implementar mecanismos de retry automático.

## Estado atual

- `Downloader.download_attachments_for_po` (`src/core/downloader.py:267-284`) captura `page_source`, converte para lowercase e procura marcadores via `Config.ERROR_PAGE_MARKERS`. Não há espera ativa; se o DOM ainda não contém a mensagem, o check falha.
- `Config.ERROR_PAGE_CHECK_TIMEOUT` existe, mas não é usado pelo `Downloader`; somente alguns utilitários (`MyScript/browser_tab_manager.py`) fazem polling manual baseado nele.
- Logs retornam apenas "PO not found or page error detected" sem diferenciar motivo ou marcador.
- O fallback da PR 28 (em elaboração) ocorre logo após `_find_attachments` retornar vazio. Em páginas de erro, `_find_attachments` também retorna vazio, induzindo fallback desnecessário.

## Visão proposta

### Componentes e responsabilidades

- Novo helper em `src/core/downloader.py` (ou módulo utilitário compartilhado) chamado `_detect_error_page`, que:
  - Usa `WebDriverWait` com timeout configurável (default 2s) avaliando tanto texto bruto quanto seletores (`ERROR_PAGE_SELECTORS`).
  - Retorna uma tupla `(is_error: bool, info: dict)` descrevendo o primeiro marcador encontrado.
- `Config` passa a fornecer:
  - `ERROR_PAGE_SELECTORS`: lista de CSS/XPath que apontam para containers comuns dos erros Coupa (`div.notice`, `div#error_explanation`, etc.).
  - `ERROR_PAGE_WAIT_POLL`: intervalo de polling (ex.: 0.2s) ajustável.
- Consumidores (`Downloader`, `browser_tab_manager`, futuros workers Playwright) usam o helper antes de qualquer lógica de anexos.

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

1. **Config**: adicionar `ERROR_PAGE_SELECTORS`, `ERROR_PAGE_WAIT_POLL`, revisar `ERROR_PAGE_MARKERS` (incluir PT-BR se disponível), definir defaults (timeout=2s, poll=0.2s).
2. **Helper**: implementar `_detect_error_page` com `WebDriverWait` e fallback manual; retornar `ErrorPageInfo` e medir `elapsed` via `time.perf_counter()`.
3. **Downloader**: substituir bloco atual por chamada ao helper; se erro, retornar `success=False` com `error_info` em `result` e log detalhado.
4. **Reuso**: atualizar `MyScript/browser_tab_manager.py` (ou equivalente atual) para usar helper e remover polling duplicado.
5. **Testes**: criar testes unitários em `src/utils/GeminiTests` (ou pasta apropriada) simulando HTML de erro/normal.

Rollback: expor flag `ERROR_PAGE_DETECTION_ENABLED` (default true). Em caso de regressão, desativar via env var e retornar ao comportamento atual enquanto se avalia fix.

## Impactos

- **Performance**: leve overhead (polling até 2s) apenas em páginas inválidas; páginas válidas passam sem atraso significativo.
- **Segurança**: nenhuma alteração — operamos nas mesmas páginas Coupa autenticadas.
- **Operações / suporte**: logs conterão marcador e tempo de detecção, auxiliando troubleshooting e métricas.

## Testes e evidências

- Unit tests fakes (`selenium.webdriver` mockado) cobrindo cenários: erro imediato, erro após 1s, página válida.
- Testes manuais com POs reais (inexistente vs válido) registrando tempo pelo log.
- Comparação de métricas antes/depois (tempo médio até retorno em POs inválidas).

## Decisões, trade-offs e alternativas consideradas

- Optou-se por `WebDriverWait` em vez de pooling manual com `time.sleep` para integrar com a API padrão do Selenium e permitir custom ExpectedConditions.
- Alternativa descartada: interceptar requisições de rede via DevTools. Considerada overkill e adicionaria dependência em `selenium-wire`.
- Permanece fallback para string matching a fim de garantir compatibilidade em casos onde HTML mude levemente.

## Pendências e próximos passos

- Confirmar com usuários key se há variações localizadas da mensagem (francês/espanhol) e adicioná-las aos markers.
- Atualizar documentação (`AGENTS.md`) após implementação caso novos env vars sejam introduzidos.
- Após entrega, coordenar com PR 28 para revalidar o fluxo end-to-end.
