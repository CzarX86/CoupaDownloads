# 🚀 Diagrama do Sistema MyScript - CoupaDownloads

## 📋 Visão Geral da Arquitetura

```mermaid
graph TB
    subgraph "🎯 Interface do Usuário"
        GUI[CustomTkinter GUI]
        CLI[Terminal Interface]
    end

    subgraph "⚙️ Sistemas Principais"
        INTEGRATED[Sistema Integrado]
        INVENTORY[Sistema de Inventário]
        MICROSERVICE[Microserviço de Download]
        ADVANCED[Sistema Avançado]
    end

    subgraph "🔧 Componentes Core"
        CONFIG[Configuração]
        LOGGING[Logging Estruturado]
        RETRY[Sistema de Retry]
        PROGRESS[Progress Tracker]
    end

    subgraph "🌐 Automação de Browser"
        SELENIUM[Selenium WebDriver]
        PLAYWRIGHT[Playwright]
        HYBRID[Sistema Híbrido]
    end

    subgraph "📊 Processamento de Dados"
        POLARS[Polars Processor]
        EXCEL[Excel Processor]
        CSV[CSV Manager]
    end

    subgraph "📥 Sistema de Downloads"
        ASYNC[Async Downloader]
        HTTPX[httpx Client]
        MICRO[Microserviço]
    end

    subgraph "📁 Arquivos de Dados"
        INPUT[input.xlsx]
        INVENTORY_CSV[download_inventory.csv]
        DOWNLOADS[~/Downloads/CoupaDownloads]
    end

    subgraph "🌍 Coupa System"
        COUPA[unilever.coupahost.com]
        PO_PAGES[Páginas de PO]
        ATTACHMENTS[Attachments]
    end

    %% Conexões principais
    GUI --> INTEGRATED
    GUI --> INVENTORY
    GUI --> MICROSERVICE
    GUI --> ADVANCED

    CLI --> INTEGRATED
    CLI --> INVENTORY
    CLI --> MICROSERVICE

    %% Fluxo do Sistema Integrado
    INTEGRATED --> CONFIG
    INTEGRATED --> INVENTORY
    INTEGRATED --> MICROSERVICE

    %% Fluxo do Sistema de Inventário
    INVENTORY --> SELENIUM
    INVENTORY --> CONFIG
    INVENTORY --> LOGGING
    INVENTORY --> CSV

    %% Fluxo do Microserviço
    MICROSERVICE --> CSV
    MICROSERVICE --> ASYNC
    MICROSERVICE --> DOWNLOADS

    %% Fluxo do Sistema Avançado
    ADVANCED --> PLAYWRIGHT
    ADVANCED --> POLARS
    ADVANCED --> ASYNC
    ADVANCED --> RETRY
    ADVANCED --> PROGRESS

    %% Conexões com dados
    INPUT --> EXCEL
    EXCEL --> INVENTORY
    INVENTORY --> INVENTORY_CSV
    INVENTORY_CSV --> MICROSERVICE
    MICROSERVICE --> DOWNLOADS

    %% Conexões com Coupa
    SELENIUM --> COUPA
    PLAYWRIGHT --> COUPA
    HYBRID --> COUPA
    COUPA --> PO_PAGES
    PO_PAGES --> ATTACHMENTS

    %% Estilos
    classDef uiClass fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef systemClass fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef coreClass fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef browserClass fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef dataClass fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef downloadClass fill:#e0f2f1,stroke:#004d40,stroke-width:2px
    classDef fileClass fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    classDef coupaClass fill:#fff8e1,stroke:#ff6f00,stroke-width:2px

    class GUI,CLI uiClass
    class INTEGRATED,INVENTORY,MICROSERVICE,ADVANCED systemClass
    class CONFIG,LOGGING,RETRY,PROGRESS coreClass
    class SELENIUM,PLAYWRIGHT,HYBRID browserClass
    class POLARS,EXCEL,CSV dataClass
    class ASYNC,HTTPX,MICRO downloadClass
    class INPUT,INVENTORY_CSV,DOWNLOADS fileClass
    class COUPA,PO_PAGES,ATTACHMENTS coupaClass
```

## 🔄 Fluxo de Execução Detalhado

```mermaid
sequenceDiagram
    participant U as Usuário
    participant GUI as CustomTkinter GUI
    participant INT as Sistema Integrado
    participant INV as Sistema Inventário
    participant MS as Microserviço
    participant EDGE as Edge WebDriver
    participant COUPA as Coupa System
    participant CSV as download_inventory.csv
    participant DOWN as Downloads Folder

    U->>GUI: Configura parâmetros
    GUI->>INT: Executa Sistema Integrado

    Note over INT: Fase 1: Inventário
    INT->>INV: Inicia Sistema de Inventário
    INV->>EDGE: Configura WebDriver
    INV->>COUPA: Navega para POs
    COUPA-->>INV: Retorna páginas de PO
    INV->>INV: Extrai URLs de attachments
    INV->>CSV: Salva URLs no CSV

    Note over INT: Fase 2: Downloads
    INT->>MS: Inicia Microserviço
    MS->>CSV: Lê URLs pendentes
    MS->>COUPA: Baixa attachments
    COUPA-->>MS: Retorna arquivos
    MS->>DOWN: Salva arquivos
    MS->>CSV: Atualiza status

    INT-->>GUI: Retorna resultados
    GUI-->>U: Exibe estatísticas
```

## 🏗️ Arquitetura dos Componentes

```mermaid
graph LR
    subgraph "📋 Sistema de Inventário"
        TAB_MGR[FIFO Tab Manager]
        PROFILE[Profile Verifier]
        ATTACH_EXTRACT[Attachment Extractor]
        ERROR_DETECT[Error Detector]
    end

    subgraph "📥 Microserviço de Download"
        CSV_MONITOR[CSV Monitor]
        BATCH_PROC[Batch Processor]
        DOWNLOAD_MGR[Download Manager]
        STATUS_UPD[Status Updater]
    end

    subgraph "⚡ Sistema Avançado"
        PLAYWRIGHT_MGR[Playwright Manager]
        ASYNC_DOWNLOAD[Async Downloader]
        POLARS_PROC[Polars Processor]
        RETRY_MGR[Retry Manager]
    end

    subgraph "🔧 Componentes de Suporte"
        CONFIG_MGR[Config Manager]
        LOG_MGR[Log Manager]
        PROGRESS_TRACK[Progress Tracker]
        UI_MGR[UI Manager]
    end

    %% Conexões internas
    TAB_MGR --> ATTACH_EXTRACT
    TAB_MGR --> ERROR_DETECT
    PROFILE --> TAB_MGR

    CSV_MONITOR --> BATCH_PROC
    BATCH_PROC --> DOWNLOAD_MGR
    DOWNLOAD_MGR --> STATUS_UPD

    PLAYWRIGHT_MGR --> ASYNC_DOWNLOAD
    ASYNC_DOWNLOAD --> POLARS_PROC
    RETRY_MGR --> PLAYWRIGHT_MGR

    CONFIG_MGR --> TAB_MGR
    CONFIG_MGR --> CSV_MONITOR
    CONFIG_MGR --> PLAYWRIGHT_MGR

    LOG_MGR --> TAB_MGR
    LOG_MGR --> CSV_MONITOR
    LOG_MGR --> PLAYWRIGHT_MGR

    PROGRESS_TRACK --> TAB_MGR
    PROGRESS_TRACK --> CSV_MONITOR

    UI_MGR --> CONFIG_MGR
    UI_MGR --> LOG_MGR
    UI_MGR --> PROGRESS_TRACK
```

## 📊 Estados e Transições

```mermaid
stateDiagram-v2
    [*] --> Configurado: Sistema Inicializado

    Configurado --> InventarioExecutando: Executar Inventário
    Configurado --> MicroservicoExecutando: Executar Microserviço
    Configurado --> IntegradoExecutando: Executar Sistema Integrado
    Configurado --> AvancadoExecutando: Executar Sistema Avançado

    InventarioExecutando --> InventarioConcluido: Processamento Completo
    InventarioExecutando --> ErroInventario: Falha no Processamento

    MicroservicoExecutando --> MicroservicoConcluido: Downloads Completo
    MicroservicoExecutando --> ErroMicroservico: Falha nos Downloads

    IntegradoExecutando --> InventarioExecutando: Fase 1 - Inventário
    IntegradoExecutando --> MicroservicoExecutando: Fase 2 - Downloads
    IntegradoExecutando --> IntegradoConcluido: Ambas Fases Completas
    IntegradoExecutando --> ErroIntegrado: Falha no Sistema

    AvancadoExecutando --> AvancadoConcluido: Processamento Completo
    AvancadoExecutando --> ErroAvancado: Falha no Sistema

    InventarioConcluido --> Configurado: Reset Sistema
    MicroservicoConcluido --> Configurado: Reset Sistema
    IntegradoConcluido --> Configurado: Reset Sistema
    AvancadoConcluido --> Configurado: Reset Sistema

    ErroInventario --> Configurado: Reset Sistema
    ErroMicroservico --> Configurado: Reset Sistema
    ErroIntegrado --> Configurado: Reset Sistema
    ErroAvancado --> Configurado: Reset Sistema

    note right of InventarioExecutando
        - Carrega POs do Excel
        - Navega com Edge WebDriver
        - Extrai URLs de attachments
        - Salva no CSV
    end note

    note right of MicroservicoExecutando
        - Monitora CSV
        - Baixa attachments
        - Atualiza status
        - Salva arquivos
    end note
```

## 🔧 Tecnologias e Bibliotecas

```mermaid
mindmap
  root((MyScript System))
    Frontend
      CustomTkinter
        Modern UI
        Dark Theme
        Responsive Design
      Rich Console
        Terminal UI
        Progress Bars
        Tables
    Backend
      Selenium
        WebDriver
        Edge Browser
        Tab Management
      Playwright
        Modern Automation
        Async Support
        Better Reliability
      httpx
        Async HTTP
        Fast Downloads
        Retry Logic
    Data Processing
      Polars
        Fast DataFrame
        Memory Efficient
        Lazy Evaluation
      Pandas
        Excel Processing
        CSV Management
        Data Analysis
    Infrastructure
      asyncio
        Async Programming
        Concurrent Processing
        Performance
      Threading
        Parallel Execution
        Background Tasks
        UI Responsiveness
      Logging
        Structured Logs
        Performance Metrics
        Error Tracking
```

## 📈 Métricas e Monitoramento

```mermaid
graph TB
    subgraph "📊 Métricas Coletadas"
        PO_METRICS[POs Processadas]
        ATTACH_METRICS[Attachments Encontrados]
        DOWNLOAD_METRICS[Downloads Concluídos]
        ERROR_METRICS[Taxa de Erro]
        TIME_METRICS[Tempo de Execução]
        SIZE_METRICS[Tamanho Total]
    end

    subgraph "📈 Análise de Performance"
        THROUGHPUT[Throughput Analysis]
        TREND[Trend Analysis]
        BOTTLENECK[Bottleneck Detection]
        OPTIMIZATION[Optimization Suggestions]
    end

    subgraph "🎯 Alertas e Notificações"
        ERROR_ALERTS[Error Alerts]
        PROGRESS_ALERTS[Progress Updates]
        COMPLETION_ALERTS[Completion Notifications]
        PERFORMANCE_ALERTS[Performance Warnings]
    end

    PO_METRICS --> THROUGHPUT
    ATTACH_METRICS --> THROUGHPUT
    DOWNLOAD_METRICS --> THROUGHPUT
    TIME_METRICS --> TREND
    ERROR_METRICS --> BOTTLENECK

    THROUGHPUT --> OPTIMIZATION
    TREND --> OPTIMIZATION
    BOTTLENECK --> OPTIMIZATION

    ERROR_METRICS --> ERROR_ALERTS
    PO_METRICS --> PROGRESS_ALERTS
    DOWNLOAD_METRICS --> COMPLETION_ALERTS
    TIME_METRICS --> PERFORMANCE_ALERTS
```

## 🚀 Como Usar o Sistema

### 1. **Interface Gráfica (Recomendado)**

```bash
# Instalar dependências
pip install customtkinter

# Executar GUI
python src/MyScript/gui_main.py
```

### 2. **Sistema Integrado**

```bash
# Executar sistema completo
poetry run python src/MyScript/integrated_system.py
```

### 3. **Sistema Avançado**

```bash
# Executar com tecnologias modernas
poetry run python src/MyScript/advanced_system.py
```

### 4. **Componentes Individuais**

```bash
# Apenas inventário
poetry run python src/MyScript/inventory_system.py

# Apenas microserviço
poetry run python src/MyScript/download_microservice.py
```

## 📋 Funcionalidades Principais

- ✅ **Interface Gráfica Moderna** com CustomTkinter
- ✅ **Sistema de Inventário** para coleta de URLs
- ✅ **Microserviço de Download** em background
- ✅ **Sistema Integrado** combinando ambos
- ✅ **Sistema Avançado** com Playwright e async
- ✅ **Configuração Flexível** via UI ou arquivos
- ✅ **Monitoramento em Tempo Real** de progresso
- ✅ **Logs Estruturados** para debugging
- ✅ **Sistema de Retry** inteligente
- ✅ **Processamento Paralelo** otimizado
- ✅ **Detecção de Erros** automática
- ✅ **Estatísticas Detalhadas** de performance

## 🎯 Benefícios da Arquitetura

1. **Modularidade**: Componentes independentes e reutilizáveis
2. **Escalabilidade**: Suporte a múltiplos workers e janelas
3. **Confiabilidade**: Sistema de retry e detecção de erros
4. **Performance**: Processamento paralelo e assíncrono
5. **Usabilidade**: Interface gráfica intuitiva
6. **Manutenibilidade**: Código bem estruturado e documentado
7. **Flexibilidade**: Múltiplas opções de execução
8. **Monitoramento**: Métricas detalhadas de performance

