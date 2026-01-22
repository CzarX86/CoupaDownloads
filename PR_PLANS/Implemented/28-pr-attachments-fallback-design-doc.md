# Arquitetura 28 — Fallback de anexos via PR (requisition)

- Status: bloqueada (aguardando PR 53)
- Data: 2025-09-24
- Responsáveis: Equipe CoupaDownloads (dev a designar)
- Observações: deriva da proposta `PR_PLANS/28-pr-attachments-fallback-proposta.md`. Revisão 2 do plano.

## Resumo executivo

Quando uma Purchase Order (PO) não possui anexos disponíveis, o fluxo atual encerra com sucesso "No attachments found", mesmo que a Purchase Requisition (PR) de origem possua documentos relevantes. Este design introduz um fallback opcional: após confirmar ausência de anexos na PO, o `Downloader` passa a navegar para a PR ligada à ordem, reaproveitando os mesmos seletores e rotinas de download. A mudança é isolada ao módulo de download baseado em Selenium e protegida por uma flag em `Config`, evitando regressões para cenários onde o fallback não é desejado.

## Objetivos e não objetivos

**Objetivos**
- Reaproveitar o `Downloader` existente para obter anexos na PR quando a PO não apresentar arquivos.
- Manter a assinatura de retorno do método `download_attachments_for_po`, ajustando apenas valores (contadores, URL) conforme a origem dos anexos.
- Permitir ativação/desativação do fallback via variável de ambiente, facilitando troubleshooting.

**Não objetivos**
- Não alterar o paralelismo atual (`ProcessPoolExecutor` em `Core_main`).
- Não modificar a lógica de criação/renomeação de pastas do `FolderHierarchyManager`.
- Não introduzir novos componentes de persistência ou APIs externas.

## Estado atual

- `Downloader.download_attachments_for_po` (`src/core/downloader.py:120` em diante) monta a URL da PO (`/order_headers/{order_number}`), invoca `_find_attachments` e retorna imediatamente com sucesso quando a lista vem vazia, registrando `attachments_found=0` e `coupa_url` da própria PO.
- Não existem helpers para navegar da PO para a PR; as únicas interações são click nos anexos e waits configurados no próprio `Downloader`.
- `Config` (`src/core/config.py`) define seletores e flags diversas, mas não possui chaves relacionadas à PR.
- `Core_main.process_po_worker` consome o dict retornado pelo downloader para inferir o status final (com base em `message` e contadores) e renomeia a pasta de download em seguida. Tudo é feito assumindo que o navegador permaneceu na página original da PO.
- Nenhum teste ou rotina atual contempla fallback; logging baseia-se em prints síncronos.

## Visão proposta

### Componentes e responsabilidades

- `Config` passa a expor:
  - `PR_FALLBACK_ENABLED` (bool) com default `True`.
  - Listas `PR_LINK_CSS_SELECTORS` e `PR_LINK_XPATH_CANDIDATES` contendo seletores típicos de Coupa para o link "Requisition".
- `Downloader` recebe dois incrementos:
  1. Após `_find_attachments`, se a lista estiver vazia e o fallback estiver habilitado, executa `_navigate_to_pr_from_po`.
  2. Novo método privado `_navigate_to_pr_from_po` realiza a busca dos elementos configurados, obtém o `href` da PR e faz `driver.get` para a nova página.
- Reuso de `_find_attachments`, `_extract_supplier_name` e `_download_attachment` sem modificações estruturais, garantindo consistência entre PO e PR.

### Fluxos (diagramas, mermaid, sequência)

```
PO page
  ↓ (sem anexos)
_navigate_to_pr_from_po
  ↓ (encontrou link)
PR page
  ↓
_find_attachments → _download_attachment*
```

Casos de exceção (link ausente, PR vazia) retornam ao fluxo atual, emitindo "No attachments found".

### Dados e contratos

- O dict retornado por `download_attachments_for_po` mantém as chaves atuais (`success`, `message`, `attachments_found`, etc.).
- `coupa_url` passa a refletir a página efetiva onde os anexos foram localizados (PO ou PR).
- Avaliar inclusão de um campo opcional `fallback_used: bool` apenas para logs internos; se necessário, documentar explicitamente no relatório de implementação.

## Plano de implementação

1. **Configuração**: adicionar novas chaves em `Config`, com validação básica (listas não vazias) e documentação breve em comentários.
2. **Navegação PR**: implementar `_navigate_to_pr_from_po` no `Downloader`, com tratamento de exceções e logs alinhados ao padrão existente.
3. **Integração fallback**: ajustar `download_attachments_for_po` para chamar o helper, atualizar `coupa_url` e garantir que contadores reflitam a PR.
4. **Instrumentação opcional**: se necessário, propagar `fallback_used` para logs/telemetria e ajustar o avaliador de status em `Core_main` (não obrigatório para MVP).
5. **Documentação e lint**: revisar `AGENTS.md` apenas se surgirem novas orientações operacionais e executar lint/testes existentes.

Rollback: desabilitar `PR_FALLBACK_ENABLED` via ambiente para restaurar o comportamento atual sem redeploy de código.

## Impactos

- **Performance**: impacto marginal; somente POs sem anexos fazem a navegação extra. O custo é uma requisição adicional da página de PR.
- **Segurança**: nenhum novo escopo; seguimos autenticados na mesma sessão Selenium. Ficam armazenados apenas downloads autorizados pelo usuário.
- **Operações / suporte**: logs adicionais informam quando o fallback foi acionado, auxiliando suporte a campo. Não há novos artefatos persistentes.

## Testes e evidências

- **Manual**: três cenários mínimos (PO com anexos, PO sem anexos + PR com anexos, PO/PR sem anexos) executados via `poetry run python -m src.Core_main` com planilha representativa.
- **Automatizado**: validar possibilidade de adicionar teste integrado usando mocks/fakes de Selenium (caso complexo, pode ficar como futuro trabalho). No mínimo, cobrir `_navigate_to_pr_from_po` com unit tests simulando respostas de driver.
- **Observabilidade**: revisar registros em `data/control/download_control.csv` para assegurar que contadores permanecem corretos.

## Decisões, trade-offs e alternativas consideradas

- Optamos por navegar com Selenium em vez de chamar APIs internas do Coupa porque o contexto autenticado e os seletores já estão estabilizados no projeto.
- A flag de configuração garante rollback instantâneo sem distribuir builds adicionais.
- Decidido não alterar `FolderHierarchyManager`: manter a mesma pasta evita duplicidade e reduz risco de divergência nos relatórios.

## Pendências e próximos passos

- Validar seletores propostos em ambiente real (produção/homologação) antes do merge.
- Confirmar se o time de QA deseja expor em relatório CSV quando o fallback for utilizado.
- Após implementação, mover proposta + design para `PR_PLANS/Implemented/` junto ao relatório de implementação.
- Guardar execução até que a PR 53 (detecção avançada de página de erro) seja concluída e validada.
