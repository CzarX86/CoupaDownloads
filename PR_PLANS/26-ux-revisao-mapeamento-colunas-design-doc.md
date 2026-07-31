# Design Doc: Revisão UX e Mapeamento de Colunas — Contract Downloader

**Data:** 2026-07-31
**Escopo:** Correções priorizadas na reunião de revisão (31/07) + mapeamento de colunas.

## 1. Contexto

A reunião de revisão identificou problemas de UX e confiabilidade no fluxo de "New Run":

1. Janela com título comprimido e controles cortados.
2. Idioma salvo (pt-BR) não aplicado na inicialização — só após abrir Settings.
3. Botão de autenticação redundante quando já autenticado.
4. "Start Over" posicionado no início do fluxo (não deve existir sem estado; deve ficar na etapa final).
5. Validação com mensagens soltas, sem agrupar por tipo e sem ações de correção por grupo.
6. Hierarquia de pastas ignora Supplier (deve ser Nível 1 fixo; PO nível final fixo); colunas 100% vazias devem gerar aviso e não criar pastas.
7. Confirmação de estrutura de pastas aparece no início do download; deve aparecer entre as etapas 3 e 4 (preview) e não repetir.
8. Input arquivado de run anterior pode ser alterado acidentalmente; deve ser snapshot protegido (exceção: retry explícito).
9. Aba New Run acessível durante execução ativa (deve ficar travada).
10. Sem descrição/título livre para a run (auditoria).

**Incluído neste desenvolvimento:** mapeamento de colunas para inputs não padronizados (antes "fase futura").
**Fora do escopo:** enriquecimento via Coupa, SharePoint, IA, Power BI, terminal headless, ETA/velocidade total, links clicáveis no log, notificação de conclusão.

## 2. Decisões de design

### 2.1 Mapeamento de colunas (novo)
- Novo módulo `src/engine/input_schema.py` com funções puras:
  - `normalize_column_name(col)` — normaliza para comparação (lowercase, sem não-alfanuméricos).
  - `detect_required_columns(columns)` — detecta PO e Supplier pelos sinônimos atuais.
  - `resolve_mapping(columns, mapping)` — valida mapeamento explícito {po, supplier}.
- Persistência do mapeamento: `~/.contract_downloader/column_mappings.json`, chave = caminho absoluto do input. O mapeamento é reutilizado em validação/importação.
- O pipeline CLI recebe o mapeamento via `COUPA_COLUMN_MAPPING` (JSON) e usa nas funções de criação de sessão e mapa de subdiretórios.
- UI: se a validação falhar por colunas obrigatórias ausentes, exibe card de mapeamento (selects de colunas do arquivo → PO / Supplier) + "Aplicar mapeamento".

### 2.2 Validação agrupada com correções por grupo
- `validate_input_file` retorna `groups: [{id, title, count, rows, fix_action, fixable, severity}]`:
  - `blank_rows` → fix `remove_blank_rows` (seguro)
  - `duplicate_pos` → fix `remove_duplicate_pos` (seguro)
  - `invalid_chars` → fix `clean_invalid_chars` (seguro, novo)
  - `unusual_format` → sem correção automática (abrir arquivo para edição assistida)
  - `missing_columns` → tratado pelo mapeamento
- `repair_input_file` ganha `clean_invalid_chars` (CSV e XLSX).

### 2.3 Hierarquia Supplier-first (fim a fim)
- `_build_output_subdir`: sempre prefixa Supplier como primeiro nível.
- `_extract_hierarchy_columns`: remove colunas 100% vazias da lista ativa (GUI continua exibindo o aviso).
- UI etapa 3: Supplier fixo no topo (não arrastável), colunas intermediárias com toggle ativar/desativar, PO fixo no final, lista "Disabled columns", aviso de colunas vazias, preview em árvore.

### 2.4 Preview entre etapas 3 e 4
- Etapa 4 (Destino) passa a exibir, no topo, o preview da estrutura de pastas (árvore + pasta raiz).
- O modal "Confirm destination / Review folder structure" deixa de ser exibido ao iniciar o download (sem segunda confirmação).

### 2.5 Proteção do input arquivado
- Após a conclusão da run, o input arquivado (`input_source_{id}.{ext}`) recebe atributo somente leitura (chmod 444 / attrib +R).
- No retry in-place: remover proteção → editar → reaplicar (em `persist_retry_files` / `_replace_po_in_file`).
- Ao selecionar como input um arquivo que é snapshot de outra run, criar cópia de trabalho em `~/.contract_downloader/working/` (a run nova nunca edita o snapshot da anterior).

### 2.6 Descrição da run
- Coluna `description` em `sessions` (migração nos dois DBs).
- `COUPA_RUN_DESCRIPTION` para o pipeline; `set_run_description()` para edição posterior.
- UI: campo livre no header do modal de detalhes (ao lado do título da run) + coluna "Description" no histórico; input do histórico clicável (abre o snapshot arquivado).

### 2.7 Travamento da New Run durante execução
- `runInProgress`: botão de navegação New Run desabilitado, banner ativo, Start Over e limpar arquivo desabilitados; ao concluir, reabilita.

### 2.8 Correções de inicialização/UX
- Startup: carregar settings (com retry até `pywebview.api` disponível) antes de marcar como feito; aplicar idioma e font scale.
- `updateAuthUI`: esconder `.auth-action` quando autenticado.
- Janela: largura mínima maior (1080) e `min_size` maior; teste de geometria atualizado.

## 3. Arquivos alterados

| Arquivo | Mudança |
|---|---|
| `src/engine/input_schema.py` | novo: detecção/resolução de mapeamento |
| `src/db/session_db.py` | coluna `description`, `update_session_description` |
| `process_all_pos.py` | Supplier L1, mapeamento por env, descrição por env, filtro de colunas vazias |
| `src/gui/api.py` | `get_input_columns`, `map_input_columns`, validação agrupada, `clean_invalid_chars`, import com mapeamento |
| `src/gui/cli_supervisor.py` | `description`, `set_run_description`, proteção read-only, migração |
| `src/main.py` | working copy de snapshots, descrição no start, geometria da janela |
| `src/gui/web/index.html` | painéis 2/3/4, detalhes, histórico, banner |
| `src/gui/web/app.js` | toda a lógica de UI acima |
| `src/gui/web/style.css` | estilos novos |
| `tests/*` | ajustes + novos testes |

## 4. Critérios de aceite

- 131+ testes existentes passam (com ajustes de expectativa de Supplier-first e geometria).
- Fluxo completo: input padrão e input não padrão (com mapeamento) → validação agrupada → hierarquia com Supplier fixo → preview → destino → run.
- Input arquivado fica read-only após a run; retry edita e reaplica proteção.
- Descrição salva e exibida em detalhes e histórico.
- Idioma salvo aplicado na abertura do app sem abrir Settings.
