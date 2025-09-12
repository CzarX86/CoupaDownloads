# 🚀 Sistema MyScript - Diagrama de Workflow e Arquitetura

## 📋 Visão Geral do Sistema

O Sistema MyScript é uma solução avançada para automação de downloads de anexos do sistema Coupa, organizado em módulos especializados com interface gráfica moderna.

## 🔄 Diagrama de Fluxo Principal

```mermaid
graph TD
    A[🚀 Início do Sistema] --> B{Modo de Execução}

    B -->|Apenas Inventário| C[📋 Fase de Inventário]
    B -->|Apenas Download| D[⬇️ Fase de Download]
    B -->|Inventário + Download| E[🔄 Workflow Completo]

    C --> F[📊 Leitura Excel]
    F --> G[🔗 Construção URLs]
    G --> H[🌐 Navegação Playwright]
    H --> I[📝 Salvamento CSV]

    D --> J[📖 Leitura CSV]
    J --> K[⬇️ Downloads Assíncronos]
    K --> L[📁 Organização Arquivos]

    E --> M[📋 Inventário]
    M --> N[⬇️ Downloads]
    N --> O[📊 Relatório Final]

    I --> P[✅ Conclusão]
    L --> P
    O --> P

    P --> Q[🧹 Limpeza Recursos]
```

## 🏗️ Arquitetura por Módulos

```mermaid
graph LR
    subgraph "🎨 Interface Gráfica"
        GUI[gui_main.py<br/>CustomTkinter Interface]
        CONFIG[⚙️ Configurações<br/>UI Controls]
        LOGS[📝 Logs<br/>Real-time Display]
    end

    subgraph "🧠 Sistema Principal"
        ADV[advanced_system.py<br/>AdvancedCoupaSystem]
        INT[integrated_system.py<br/>Sistema Integrado]
        MAIN[main.py<br/>Entry Point]
    end

    subgraph "🌐 Automação Web"
        PLAY[playwright_system.py<br/>Playwright Manager]
        HYB[hybrid_processor.py<br/>Processador Híbrido]
        INV[inventory_system.py<br/>Sistema Inventário]
    end

    subgraph "📊 Processamento Dados"
        POL[polars_processor.py<br/>Polars Data Processor]
        CSV[csv_processor.py<br/>CSV Manager]
        EXCEL[excel_processor.py<br/>Excel Manager]
    end

    subgraph "⬇️ Sistema Downloads"
        ASYNC[async_downloader.py<br/>Async Download Manager]
        MICRO[download_microservice.py<br/>Microservice]
        CTRL[download_control.py<br/>Control Manager]
    end

    subgraph "🔧 Utilitários"
        CONF[config_advanced.py<br/>Configurações Avançadas]
        LOG[logging_advanced.py<br/>Sistema Logging]
        RETRY[retry_advanced.py<br/>Retry Logic]
    end

    GUI --> ADV
    ADV --> PLAY
    ADV --> POL
    ADV --> ASYNC
    PLAY --> INV
    POL --> CSV
    ASYNC --> MICRO
    ADV --> CONF
    ADV --> LOG
    ADV --> RETRY
```

## 🔄 Fluxo Detalhado de Execução

```mermaid
sequenceDiagram
    participant U as 👤 Usuário
    participant G as 🎨 GUI
    participant A as 🧠 Advanced System
    participant P as 🌐 Playwright
    participant D as 📊 Data Processor
    participant DL as ⬇️ Download Manager

    U->>G: Seleciona modo execução
    G->>A: Inicia sistema avançado
    A->>A: Valida configurações
    A->>P: Inicializa Playwright
    A->>D: Carrega processadores

    alt Modo Inventário
        A->>D: Lê números PO do Excel
        D-->>A: Retorna lista POs
        A->>P: Processa URLs em lotes
        P->>P: Navega páginas Coupa
        P-->>A: Retorna attachments
        A->>D: Salva no CSV
    end

    alt Modo Download
        A->>D: Lê downloads pendentes
        D-->>A: Retorna lista downloads
        A->>DL: Executa downloads assíncronos
        DL->>DL: Baixa arquivos
        DL-->>A: Retorna resultados
        A->>D: Atualiza status CSV
    end

    A->>A: Gera relatório final
    A->>G: Retorna status
    G->>U: Exibe resultados
```

## 📁 Estrutura de Dados

```mermaid
graph TD
    subgraph "📊 Entrada"
        EXCEL[input.xlsx<br/>PO_NUMBER Column]
    end

    subgraph "🔄 Processamento"
        URLS[URLs Construídas<br/>base_url/order_headers/{po_number}]
        ATTACH[Attachments Encontrados<br/>filename, url, file_type]
    end

    subgraph "💾 Armazenamento"
        CSV[download_inventory.csv<br/>po_number, filename, url, status]
        FILES[~/Downloads/CoupaDownloads/<br/>Organizados por PO]
    end

    EXCEL --> URLS
    URLS --> ATTACH
    ATTACH --> CSV
    CSV --> FILES
```

## ⚙️ Configurações do Sistema

```mermaid
graph LR
    subgraph "🎛️ Configurações UI"
        WINDOWS[Num Windows: 2]
        TABS[Max Tabs per Window: 3]
        WORKERS[Max Workers: 4]
        HEADLESS[Headless Mode: False]
        PROFILE[Profile Mode: minimal]
    end

    subgraph "📁 Caminhos"
        EXCEL_PATH[Excel Path]
        CSV_PATH[CSV Path]
        DOWNLOAD_DIR[Download Directory]
    end

    subgraph "🔧 Avançadas"
        BATCH_SIZE[Batch Size: 10]
        MAX_LINES[Max Lines: 1000]
        RETRY_COUNT[Retry Count: 3]
        TIMEOUT[Timeout: 30s]
    end
```

## 🚦 Estados do Sistema

```mermaid
stateDiagram-v2
    [*] --> Parado
    Parado --> Inicializando: Executar Sistema
    Inicializando --> Validando: Configurações OK
    Inicializando --> Erro: Configurações Inválidas
    Validando --> Inventário: Modo Inventário
    Validando --> Download: Modo Download
    Validando --> Completo: Modo Ambos
    Inventário --> Processando: URLs Construídas
    Download --> Processando: Downloads Pendentes
    Completo --> Inventário: Fase 1
    Inventário --> Download: Fase 2
    Processando --> Pausado: Usuário Pausa
    Processando --> Parado: Usuário Para
    Processando --> Concluído: Processo Completo
    Pausado --> Processando: Usuário Retoma
    Concluído --> Parado: Limpeza Recursos
    Erro --> Parado: Reset Sistema
```

## 🔍 Módulos Principais Detalhados

### 🎨 Interface Gráfica (gui_main.py)

- **Função**: Interface CustomTkinter moderna
- **Componentes**: Dashboard, Configurações, Logs
- **Controles**: Executar, Pausar, Parar
- **Modos**: Inventário, Download, Ambos

### 🧠 Sistema Avançado (advanced_system.py)

- **Função**: Orquestrador principal
- **Responsabilidades**: Coordenação de módulos, controle de fluxo
- **Integração**: Playwright + Downloads + Processamento

### 🌐 Playwright System (playwright_system.py)

- **Função**: Automação web com Edge
- **Recursos**: Múltiplas janelas, perfil Edge, retry logic
- **Fallback**: Sistema híbrido em caso de falha

### 📊 Processamento de Dados (polars_processor.py)

- **Função**: Manipulação eficiente de dados
- **Recursos**: Polars para performance, Excel/CSV processing
- **Operações**: Leitura, escrita, atualização de status

### ⬇️ Downloads Assíncronos (async_downloader.py)

- **Função**: Downloads paralelos eficientes
- **Recursos**: Async/await, controle de concorrência
- **Organização**: Hierarquia por PO

## 🎯 Fluxo de Dados

1. **Entrada**: Excel com números de PO
2. **Processamento**: Construção de URLs + Navegação web
3. **Inventário**: Coleta de links de anexos
4. **Armazenamento**: CSV com metadados
5. **Download**: Baixar arquivos em paralelo
6. **Organização**: Estrutura hierárquica por PO
7. **Relatório**: Estatísticas e status final

## 🔧 Configurações Avançadas

- **Performance**: Workers paralelos, lotes otimizados
- **Robustez**: Retry automático, fallback híbrido
- **Logging**: Logs especializados por módulo
- **Controle**: Pausar/retomar, parada segura
- **Perfil**: Integração com perfil Edge existente

---

_Este diagrama representa a arquitetura completa do Sistema MyScript, mostrando como os módulos se integram e o fluxo de dados através do sistema._
