# Relatório de Implementação — Revisão UX + Mapeamento de Colunas

**Data:** 2026-07-31
**Design doc:** `PR_PLANS/26-ux-revisao-mapeamento-colunas-design-doc.md`

## Entregue

### 1. Correções de inicialização e janela
- Janela maior: largura mínima 1080 (88% da tela), `min_size` (1000×680) — título e controles não ficam mais comprimidos.
- Idioma salvo (pt-BR) é carregado **antes** da primeira renderização: `runStartupChecks` agora aguarda a ponte pywebview estar disponível antes de aplicar settings.
- Botão de autenticação: quando autenticado, a ação redundante "Sign in/Entrar" é ocultada (um estado por vez).

### 2. Fluxo New Run
- **Start Over** movido para a etapa 5 (Review): só existe quando há estado para limpar, com confirmação explicando que o histórico é preservado e uma nova run será criada.
- **New Run bloqueada durante execução ativa**: navegação desabilitada, banner traduzido, retorno automático para Active Run.

### 3. Validação agrupada com correções por grupo
- Erros agora são retornados em `groups` por categoria: `blank_rows`, `partial_rows`, `duplicate_pos`, `invalid_chars`, `unusual_format`, `missing_po_column`, `missing_supplier_column`.
- Correções seguras por grupo: `remove_blank_rows`, `remove_duplicate_pos`, **`clean_invalid_chars`** (novo, CSV e XLSX, com backup).
- Problemas sem correção automática (formato inválido): botão "Open file to fix" abre o arquivo no editor.

### 4. Mapeamento de colunas (arquivos não padronizados)
- Novo módulo `src/engine/input_schema.py` (detecção + resolução de mapeamento), compartilhado entre GUI e pipeline CLI (`COUPA_COLUMN_MAPPING`).
- `get_input_columns` / `map_input_columns`: card "Map the file columns" na etapa de validação; mapeamento persistido em `~/.contract_downloader/column_mappings.json` por arquivo.
- Arquivos sem `<|>` agora têm todas as colunas (exceto PO/Supplier) como candidatas a hierarquia; o usuário escolhe ativar/desativar.

### 5. Hierarquia Supplier-first (fim a fim)
- `_build_output_subdir` e `AppAPI.import_file` sempre usam **Supplier como Nível 1**; PO permanece no nível final.
- UI etapa 3: Supplier fixo (não arrastável), PO fixo no final, níveis intermediários arrastáveis com toggle ×/+ (lista "Disabled columns"), colunas 100% vazias geram aviso e não criam pastas.
- O pipeline respeita ordem explícita, inclusive vazia (`COUPA_HIERARCHY_ORDER` agora é enviado mesmo quando vazio).

### 6. Preview entre etapas 3 e 4
- A etapa 4 exibe a árvore de pastas (preview) antes do campo de destino.
- O modal "Confirm destination" foi **removido** do início do download (sem segunda confirmação).

### 7. Proteção dos inputs arquivados
- Após a run, `input_source_{id}` recebe atributo somente leitura (chmod 444).
- Retry explícito remove a proteção, edita e reaplica.
- Selecionar um snapshot de outra run cria cópia de trabalho em `~/.contract_downloader/working/` — o snapshot original nunca é alterado incidentalmente.

### 8. Descrição da run (auditoria)
- Coluna `description` em `sessions` (migração nos dois bancos); `COUPA_RUN_DESCRIPTION` para o pipeline; `set_run_description` para edição posterior.
- UI: campo livre no modal de detalhes (ao lado do título) + coluna "Description" no histórico; input do histórico clicável (abre o snapshot).

## Validação

- **156 testes passando** (eram 131; +25 novos cobrindo mapeamento, grupos de validação, `clean_invalid_chars`, supplier-first, descrição, proteção e working copy).
- E2E Playwright (mock e real): jornada completa sem erros de página.
- `git diff --check`, `node --check`, `py_compile` limpos.

## Fora de escopo (mantidos para sprints futuras)

- Terminal headless; velocidade total/ETA; links clicáveis no log; notificação de conclusão; enriquecimento via Coupa; SharePoint; IA; Power BI.
