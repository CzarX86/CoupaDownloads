# Roadmap: Coupa Turbo Downloader

**17 requirements** | **6 phases** | All v1 requirements covered

---

### Phase 1: Setup & Estrutura
**Goal:** Ambiente Python isolado com `uv` e esqueleto estrutural do projeto
**Mode:** mvp
**Success Criteria:**
1. `pyproject.toml` criado com dependencias: pywebview, httpx, beautifulsoup4, lxml, pyinstaller, selenium
2. Estrutura de diretorios: `src/engine/`, `src/gui/`, `src/gui/assets/`, `src/db/`, `tests/`
3. `uv run` executa entrypoint `src/main.py` (placeholder)

**Requirements:** ISOL-01

**Files:**
- `pyproject.toml` — definicao do pacote Python 3.12 independente
- `src/main.py` — entrypoint placeholder
- `src/__init__.py`

---

### Phase 2: Database & Persistencia
**Goal:** Banco SQLite unificado com schema de sessoes e tracking de downloads
**Mode:** mvp
**Success Criteria:**
1. Tabelas `sessions` e `po_downloads` criadas com schema completo
2. PO statuses implementados: PENDING, DOWNLOADING, COMPLETED, FAILED, SKIPPED_VERIFICATION_REQUIRED
3. Funcoes de resume: restaurar batch interrompido sem re-baixar completos
4. Testes unitarios validam escrita e atualizacao transacional

**Requirements:** PERS-01

**Files:**
- `src/db/session_db.py` — schema, funcoes CRUD, resume, reset-status

---

### Phase 3: Engine Core
**Goal:** Motor HTTP assincrono completo — crawler, parser, benchmarker, rate limiter
**Mode:** mvp
**Success Criteria:**
1. `crawler.py`: httpx.AsyncClient com semaforo 11 workers, exportacao Excel
2. `parser.py`: BeautifulSoup two-pass (data-url + href)
3. `benchmarker.py`: testes de latencia, sugestoes de concorrencia/delay
4. Circuit Breaker funcional: le `legal entity`, aplica threshold 15%/min-3/100%
5. Lazy Creation: so cria pasta ao baixar 1o anexo; cleanup remove orfas
6. Rate limiter: delay 0.03s, cooldown para >500 POs

**Requirements:** ENG-01, ENG-02, ERR-01, ERR-02, NET-01, NET-02, PARS-01

**Files:**
- `src/engine/crawler.py` — motor async principal
- `src/engine/parser.py` — parser HTML unificado
- `src/engine/benchmarker.py` — `async def benchmark(urls: list[str]) -> dict`
- `src/engine/rate_limiter.py` — controle de delays e cooldown

---

### Phase 4: Web UI & IPC Bridge
**Goal:** Interface web-nativa completa com Glassmorphism, sliders, drag-and-drop e ponte IPC
**Mode:** mvp
**Success Criteria:**
1. `index.html` renderiza dashboard Glassmorphism com sliders, console de logs e area drag-and-drop
2. `style.css` com tokens de design: cores HSL/RGB escuras, backdrop-filter, transicoes
3. `script.js` gerencia cliques, benchmark, drag-and-drop, telemetria dinamica via `window.pywebview.api`
4. `api.py` expoe funcoes Python ao JavaScript (ponte IPC)
5. Aba de Historico de Execucoes funcional: revisar, exportar, retomar

**Requirements:** GUI-01, INPT-01, UI-01

**Files:**
- `src/gui/assets/index.html` — estrutura HTML5 premium
- `src/gui/assets/style.css` — tokens de design e glassmorphism
- `src/gui/assets/script.js` — logica de interacao e IPC
- `src/gui/api.py` — mapeamento de funcoes Python → JS

---

### Phase 5: Integracao & Packaging
**Goal:** Integrar todos os modulos, Edge Authenticator, empacotar com PyInstaller
**Mode:** mvp
**Success Criteria:**
1. `authenticator.py`: Selenium Edge temporario → cookies → httpx engine
2. `updater.py`: GitHub Releases API check, download background, script atomico de replace
3. `main.py`: entrypoint final orquestrando GUI + engine
4. Rate limiting integrado com engine HTTP
5. `build_standalone.py`: PyInstaller single-file, `sys._MEIPASS` assets

**Requirements:** AUTH-01, TRAF-01, UPDT-01, OUT-01

**Files:**
- `src/engine/authenticator.py` — `async def get_coupa_cookies() -> dict`
- `src/engine/updater.py` — version check + autoupdate atomico
- `build_standalone.py` — orquestrador PyInstaller

---

### Phase 6: Testes & Validacao
**Goal:** Bateria de testes unitarios/integracao e validacao manual cross-platform
**Mode:** mvp
**Success Criteria:**
1. Testes unitarios `pytest` + `pytest-asyncio`: parser HTML, SQLite transacional, IPC bridge, Circuit Breaker, criacao/limpeza de pastas
2. Testes de integracao: authenticator com Edge, benchmarker com endpoints reais
3. Validacao manual: execucao direta `uv run`, teste de Circuit Breaker com planilha real, teste de retentativa, validacao de limpeza de disco
4. Build PyInstaller testado em maquina limpa Windows e macOS
5. Teste de resiliencia: desconexao de rede no meio do batch → resume SQLite sem duplicados

**Requirements:** PLAT-01 (validacao cross-platform)

**Files:**
- `tests/unit/test_parser.py`
- `tests/unit/test_session_db.py`
- `tests/unit/test_circuit_breaker.py`
- `tests/unit/test_ipc_api.py`
- `tests/integration/test_authenticator.py`
- `tests/integration/test_benchmarker.py`

---
*Roadmap created: 2026-05-20*
## Pós-v1 planejado

- **Alinhamento de input e relatórios:** `docs/plan-alinhamento-input-relatorios.md` — template configurável, normalização de schema, preservação do input e retries completos.
- **Integração Power BI:** `docs/roadmap-integracao-powerbi.md` — adiada; não faz parte da implementação atual.

*Last updated: 2026-07-29 with input/report alignment and deferred Power BI roadmap*
