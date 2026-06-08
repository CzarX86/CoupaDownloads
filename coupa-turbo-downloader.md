# Plan: Coupa Turbo Downloader

Este plano detalha as fases técnicas de desenvolvimento, arquitetura de componentes, dependências de tarefas e critérios de verificação para a criação da aplicação portátil **Coupa Turbo Downloader** na pasta isolada `/CoupaTurboDownloader`.

---

## Overview
Criação de um novo subprojeto 100% independente do original para baixar anexos do Coupa em altíssima velocidade. O motor de download baseia-se em requisições assíncronas diretas via HTTP/2 (eliminando o footprint de navegadores pesados) integrado a uma interface Web-Native ultra-premium alimentada pelo **pywebview** (HTML5/CSS3/JS estático) com persistência em SQLite de continuidade de processamento.

- **Project Type**: Desktop Web-Native GUI & Async Engine (Python Standalone)
- **Target OS**: macOS & Windows (portable, zero-install, zero-admin)

---

## Success Criteria
- [ ] Executável portátil compilado de arquivo único (`.exe` no Windows e `.app` no macOS) que inicializa sem permissões de administrador.
- [ ] Velocidade sustentada de download validada acima de **30 POs por minuto** (benchmark genético local atingiu **69.44 POs/min**).
- [ ] Interface visual ultra-premium baseada no padrão do **SQLBI Bravo**: Glassmorphism real com backdrop-blur, gradientes fluidos, gráficos de telemetria responsivos e terminal de logs dinâmicos.
- [ ] Login e conexão rápidos automatizados que abrem o Edge uma única vez para capturar cookies corporativos e migram a sessão automaticamente para a Engine de alta velocidade.
- [ ] Análise de rede automática que testa a latência e perda de pacotes da rota com os servidores do Coupa e pré-preenche na UI os parâmetros ótimos sugeridos.
- [ ] Mecanismo de autoupdate integrado para o executável portátil: detecta nova versão nas releases do GitHub, baixa e atualiza o binário portátil de forma 100% transparente para o usuário.
- [ ] Recuperação instantânea de progresso: ao pausar e retomar, ou simular queda de energia/rede, o sistema recomeça exatamente da PO pendente sem duplicar downloads ou requisições de POs já finalizadas.
- [ ] UI minimalista responsiva mostrando telemetria viva (ETA, progresso, velocidade de rede, avisos e logs).
- [ ] Testes unitários com cobertura de 100% do parser DOM híbrido e transações de banco de dados SQLite.

---

## Tech Stack
- **Environment**: Python 3.12 (gerenciado localmente via `uv`)
- **GUI Shell**: **pywebview** (Abre WebView2 nativa no Windows e WebKit no macOS, footprint RAM ~35MB)
- **Frontend Assets**: HTML5 / CSS3 (TailwindCSS/Glassmorphic) / JS (Vanilla)
- **Networking**: `httpx[http2]` + `asyncio` (requests assíncronas com concorrência ótima e suporte a HTTP/2)
- **HTML Scraper**: `beautifulsoup4` + `lxml` (leitura extremamente rápida de DOM)
- **Temp Autentication**: Selenium (Edge WebDriver) para captura única de cookies de sessão ativa.
- **Database**: SQLite3 built-in (persistência ACID de progresso)
- **Bundling**: `pyinstaller` (geração de executável standalone portátil com pasta de assets estáticos embutida)

---

## Directory Structure
```
CoupaTurboDownloader/
├── .planning/
│   ├── config.json
│   ├── PROJECT.md
│   ├── REQUIREMENTS.md
│   ├── ROADMAP.md
│   └── STATE.md
├── src/
│   ├── __init__.py
│   ├── main.py              # Entrypoint principal do App
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── api.py           # API Python exposta ao JS (Ponte IPC)
│   │   └── assets/          # Arquivos de interface HTML/CSS/JS estáticos
│   │       ├── index.html
│   │       ├── style.css
│   │       └── script.js
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── crawler.py       # httpx Async Crawler com limite de concorrência
│   │   ├── parser.py        # bs4 unificado para extrair links data-url + href
│   │   ├── authenticator.py # Edge WebDriver temporário para extração automática de cookies
│   │   ├── benchmarker.py   # Latency ping test para pré-preenchimento de sliders da UI
│   │   ├── updater.py       # GitHub release checker e autoupdate script
│   │   └── rate_limiter.py  # Atrasos de 0.03s e cooldowns inteligentes
│   └── db/
│       ├── __init__.py
│       └── session_db.py    # Persistência de transações do SQLite
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   └── test_db.py
├── pyproject.toml           # Dependências isoladas gerenciadas por uv
├── uv.lock
└── build_standalone.py      # Automação do PyInstaller
```

---

## Task Breakdown

### Phase 1: Setup & Foundations (P0)
- **Task 1.1**: Setup do diretório e ambiente `uv`
  - **Agent**: `devops-engineer` | **Skill**: `bash-linux`
  - **Dependencies**: Nenhuma
  - **INPUT**: Pasta vazia `/CoupaTurboDownloader`
  - **OUTPUT**: Ambiente `uv` inicializado com `pyproject.toml` contendo dependências isoladas.
  - **VERIFY**: Executar `uv run python --version` retornando Python 3.12.x com sucesso.
  
- **Task 1.2**: Estruturar banco de dados SQLite de Continuidade
  - **Agent**: `database-architect` | **Skill**: `database-design`
  - **Dependencies**: Task 1.1
  - **INPUT**: `src/db/session_db.py`
  - **OUTPUT**: Classe `SessionDB` implementando criação de tabelas (`po_downloads`), inicialização de registros e atualizações transacionais atômicas de status de download (`PENDING`, `DOWNLOADING`, `COMPLETED`, `FAILED`).
  - **VERIFY**: Teste unitário simples validando inserção, atualização e leitura atômica de POs no banco.

---

### Phase 2: Connection, Scraper & Automation Core (P1)
- **Task 2.1**: Desenvolver Edge Authenticator Temporário
  - **Agent**: `backend-specialist` | **Skill**: `clean-code`
  - **Dependencies**: Task 1.1
  - **INPUT**: `src/engine/authenticator.py`
  - **OUTPUT**: Módulo de automação minimalista que abre o navegador padrão do sistema (Microsoft Edge WebDriver), detecta a página de autenticação, captura os cookies ativos após login bem-sucedido do usuário, fecha o navegador e encerra o processo de automação de forma limpa.
  - **VERIFY**: Execução de login simulado em sandbox capturando os cookies de cabeçalho com sucesso.

- **Task 2.2**: Desenvolver Parser DOM Híbrido
  - **Agent**: `backend-specialist` | **Skill**: `clean-code`
  - **Dependencies**: Task 1.2
  - **INPUT**: `src/engine/parser.py`
  - **OUTPUT**: Função robusta de extração de links que varre o DOM com BeautifulSoup buscando passagens duplas: elementos modernos com atributo `data-url` contendo palavras-chave e tags de âncora `<a>` tradicionais com `href`.
  - **VERIFY**: Executar testes unitários com mocks HTML contendo ambos os formatos e certificar que todos os links válidos de anexos são identificados e deduplicados.

- **Task 2.3**: Desenvolver Core de Conexão Assíncrona e Crawler
  - **Agent**: `backend-specialist` | **Skill**: `api-patterns`
  - **Dependencies**: Task 2.2
  - **INPUT**: `src/engine/crawler.py`
  - **OUTPUT**: Classe `TurboCrawler` baseada em `httpx.AsyncClient` implementando semáforo de concorrência com limite configurável (default `11` conexões), downloads concorrentes em lote e retries automáticos com backoff.
  - **VERIFY**: Simulação de download de 15 páginas mockadas retornando sucesso sustentado acima de 60 downloads por minuto.

- **Task 2.4**: Implementar Benchmarker de Rede
  - **Agent**: `backend-specialist` | **Skill**: `performance-profiling`
  - **Dependencies**: Task 2.3
  - **INPUT**: `src/engine/benchmarker.py`
  - **OUTPUT**: Módulo que realiza testes de ping e latência concorrentes e rápidos contra a API do Coupa, analisando estabilidade e sugerindo a concorrência ideal (ex: 11 conexões) e delays mínimos de rate-limit.
  - **VERIFY**: Execução de teste retornando uma payload estruturada JSON com os hiperparâmetros de rede ideais.

- **Task 2.5**: Implementar Rate Limiting, Cooldowns e Self-Updater
  - **Agent**: `backend-specialist` | **Skill**: `performance-optimizer`
  - **Dependencies**: Task 2.4
  - **INPUT**: `src/engine/rate_limiter.py` e `src/engine/updater.py`
  - **OUTPUT**:
    - Gerenciador que impõe delays mínimos controlados (0.03s por worker) e janelas de cooldown para tarefas que superem 500 POs consecutivas.
    - Módulo `updater.py` que checa o GitHub Releases de forma assíncrona, sinaliza novas versões disponíveis na UI e baixa o binário portátil mais recente em segundo plano executando o script de substituição atômica.
  - **VERIFY**: Logs de requisições mostrando com precisão a aplicação de micro-delays e simulação de atualização portátil baixando um executável mockado.

---

### Phase 3: Web-Native GUI Integration (P2)
- **Task 3.1**: Desenvolver Assets HTML5/CSS3 Estáticos (Visual Bravo Standard)
  - **Agent**: `frontend-specialist` | **Skill**: `frontend-design`
  - **Dependencies**: Task 1.1
  - **INPUT**: `src/gui/assets/index.html` e `src/gui/assets/style.css`
  - **OUTPUT**: UI moderna com efeito Glassmorphism real (`backdrop-filter`), gradientes escuros elegantes, barra de progresso horizontal e circular animada, controles de sliders de concorrência, e console interativo de logs pretos coloridos.
  - **VERIFY**: Renderização estática em navegador local exibindo design impecável e fluidez de animação a 60 FPS.

- **Task 3.2**: Implementar Ponte IPC API do pywebview
  - **Agent**: `backend-specialist` | **Skill**: `clean-code`
  - **Dependencies**: Task 3.1, Task 2.5
  - **INPUT**: `src/gui/api.py` e `src/gui/assets/script.js`
  - **OUTPUT**:
    - Ponte C#-like em Python (`AppAPI`) mapeando as funcionalidades nativas (`connect_coupa`, `run_benchmark`, `start_download`) expostas no JS sob o objeto `window.pywebview.api`.
    - Script JavaScript gerenciando os eventos de clique, atualizações de sliders e capturas de inputs na interface gráfica.
  - **VERIFY**: Conexão IPC estabelecida e resposta correta do JS ao chamar qualquer método Python.

- **Task 3.3**: Orquestrar Janela Principal e Threads de Telemetria
  - **Agent**: `frontend-specialist` | **Skill**: `frontend-design`
  - **Dependencies**: Task 3.2
  - **INPUT**: `src/main.py`
  - **OUTPUT**: Inicialização do `webview.create_window` com o arquivo local `index.html` carregado dinamicamente usando caminhos relativos ao `sys._MEIPASS`. Dispara Worker Thread para rodar o crawler assíncrono e comunica telemetria executando JS diretamente via `window.evaluate_js()`.
  - **VERIFY**: Iniciar download simulado, arrastar a janela livremente e confirmar que a UI se mantém totalmente responsiva e fluida com telemetria exata sem congelamento de tela.

---

### Phase 4: Integration, Build Standalone & QA (P3)
- **Task 4.1**: Integração Final e Script de Entrada
  - **Agent**: `backend-specialist` | **Skill**: `clean-code`
  - **Dependencies**: Task 3.3
  - **INPUT**: `src/main.py`
  - **OUTPUT**: Entrypoint geral que lê o CSV/Excel, valida o banco SQLite local, valida caminhos de assets e dispara a janela gráfica Web-Native.
  - **VERIFY**: Executar `uv run python -m src.main` inicializando o aplicativo gráfico com sucesso.

- **Task 4.2**: Automação de Builds Standalone Portáteis (PyInstaller)
  - **Agent**: `devops-engineer` | **Skill**: `bash-linux`
  - **Dependencies**: Task 4.1
  - **INPUT**: `build_standalone.py`
  - **OUTPUT**: Script de build automatizado que executa o PyInstaller com parâmetros `--onefile --noconsole --clean --add-data "src/gui/assets;src/gui/assets"` (ajustando a sintaxe de barras por OS), gerando o executável final standalone de arquivo único sob `/CoupaTurboDownloader/dist`.
  - **VERIFY**: Compilação sem avisos críticos e execução bem-sucedida do executável portátil gerado em máquina limpa.

---

## Phase X: Final Verification Checklist (MANDATORY)

- [ ] **Lint & Type Check**:
  ```bash
  uv run ruff check src/
  ```
- [ ] **Security Scan**:
  ```bash
  python .agent/skills/vulnerability-scanner/scripts/security_scan.py CoupaTurboDownloader
  ```
- [ ] **Automated Unit Tests**:
  ```bash
  uv run pytest CoupaTurboDownloader/tests/
  ```
- [ ] **Manual Portability & Build Verification**:
  ```bash
  python CoupaTurboDownloader/build_standalone.py
  ```
  - Verificar que o binário gerado inicializa em menos de 2 segundos.
  - Testar o fluxo completo de downloads em lote e testar a pausa e retomada de processo no SQLite.
  - Confirmar a integridade estética da UI (sem cores roxas ou violetas, layout alinhado).

## ✅ PHASE X COMPLETE
- Lint: [ ] Pending
- Security: [ ] Pending
- Build: [ ] Pending
- Date: [Pending Approval]
