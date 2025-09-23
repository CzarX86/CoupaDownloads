# 🚀 MyScript GUI - Interface Gráfica para Sistema CoupaDownloads

## 📋 Visão Geral

A **MyScript GUI** é uma interface gráfica moderna desenvolvida com **CustomTkinter** que fornece controle completo sobre o sistema CoupaDownloads. A interface oferece uma experiência intuitiva para configurar, executar e monitorar todos os componentes do sistema.

## ✨ Características Principais

- 🎨 **Interface Moderna**: Design dark theme com CustomTkinter
- ⚙️ **Configuração Visual**: Sliders, checkboxes e campos de texto intuitivos
- 📊 **Dashboard Completo**: Estatísticas em tempo real e controle centralizado
- 🔄 **Execução Flexível**: Múltiplas opções de execução (Integrado, Inventário, Microserviço, Avançado)
- 📝 **Logs em Tempo Real**: Monitoramento completo com auto-scroll
- 💾 **Gerenciamento de Configurações**: Salvar/carregar configurações personalizadas
- 📈 **Monitoramento de Progresso**: Barras de progresso e status detalhados

## 🏗️ Arquitetura da Interface

### 📊 Dashboard Principal

- **Status do Sistema**: Indicador visual do estado atual
- **Botões de Execução**: Controles principais para iniciar sistemas
- **Estatísticas**: Métricas em tempo real (POs processadas, downloads, etc.)
- **Controle de Parada**: Botão para interromper execuções

### ⚙️ Aba de Configuração

- **Arquivos**: Caminhos para Excel, CSV e diretório de downloads
- **Performance**: Configuração de janelas, abas e workers
- **Avançado**: Modo headless, perfil Edge, etc.
- **Gerenciamento**: Salvar/carregar/resetar configurações

### 📋 Aba de Inventário

- **Execução**: Controle do sistema de inventário
- **Progresso**: Barra de progresso e status
- **Resultados**: Tabela com POs processadas e attachments encontrados

### 📥 Aba de Downloads

- **Microserviço**: Controle do sistema de downloads
- **Configuração**: Tamanho de lote e workers
- **Monitoramento**: Downloads em andamento com status

### ⚡ Aba Avançada

- **Recursos**: Seleção de tecnologias (Playwright, Async, Polars, Retry)
- **Execução**: Sistema avançado com todas as melhorias
- **Status**: Monitoramento do sistema avançado

### 📝 Aba de Logs

- **Visualização**: Logs em tempo real com timestamp
- **Controles**: Limpar, salvar logs
- **Auto-scroll**: Rastreamento automático de novas mensagens

## 🚀 Instalação e Execução

### 1. Instalação Automática

```bash
# Executar script de instalação
python src/MyScript/install_gui.py
```

### 2. Instalação Manual

```bash
# Preparar dependências com Poetry
poetry install
```

### 3. Execução da GUI

```bash
# Executar interface gráfica
python src/MyScript/gui_main.py

# Ou usando Poetry
poetry run python src/MyScript/gui_main.py
```

## 📱 Capturas de Tela da Interface

### Dashboard Principal

```
┌─────────────────────────────────────────────────────────────┐
│  🚀 Sistema CoupaDownloads - Dashboard                      │
├─────────────────────────────────────────────────────────────┤
│  Status: 🔴 Sistema Parado                                  │
│                                                             │
│  [🔄 Executar Sistema Integrado] [⚡ Executar Sistema Avançado] [⏹️ Parar Sistema] │
│                                                             │
│  📈 Estatísticas do Sistema                                │
│  ┌─────────────┬─────────────┬─────────────┐                │
│  │ POs Processadas │ Attachments Encontrados │ Downloads Concluídos │ │
│  │      0      │      0      │      0      │                │
│  └─────────────┴─────────────┴─────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

### Aba de Configuração

```
┌─────────────────────────────────────────────────────────────┐
│  ⚙️ Configurações do Sistema                                 │
├─────────────────────────────────────────────────────────────┤
│  📁 Arquivos                                                │
│  Arquivo Excel: [src/MyScript/input.xlsx        ] [📂]     │
│  Arquivo CSV:   [src/MyScript/download_inventory.csv] [📂] │
│  Diretório:     [~/Downloads/CoupaDownloads     ] [📂]     │
│                                                             │
│  ⚡ Performance                                             │
│  Número de Janelas: [━━━━━━━━━━] 2                          │
│  Abas por Janela:   [━━━━━━━━━━] 3                          │
│  Workers Paralelos: [━━━━━━━━━━] 4                          │
│                                                             │
│  🔧 Configurações Avançadas                                │
│  ☐ Modo Headless (sem interface gráfica)                   │
│  Modo do Perfil: [minimal ▼]                               │
│                                                             │
│  [💾 Salvar] [📂 Carregar] [🔄 Resetar]                    │
└─────────────────────────────────────────────────────────────┘
```

## 🔧 Configuração da Interface

### Temas Disponíveis

- **Dark Theme** (padrão): Interface escura moderna
- **Light Theme**: Interface clara tradicional

### Personalização

```python
# Alterar tema
ctk.set_appearance_mode("dark")  # ou "light"

# Alterar cor principal
ctk.set_default_color_theme("blue")  # "blue", "green", "dark-blue"
```

### Configurações Salvas

A GUI salva automaticamente as configurações em `myscript_config.json`:

```json
{
  "excel_path": "src/MyScript/input.xlsx",
  "csv_path": "src/MyScript/download_inventory.csv",
  "download_dir": "~/Downloads/CoupaDownloads",
  "num_windows": 2,
  "max_tabs_per_window": 3,
  "max_workers": 4,
  "batch_size": 5,
  "headless": false,
  "profile_mode": "minimal"
}
```

## 🎯 Fluxo de Uso Típico

1. **Configuração Inicial**

   - Abrir aba "⚙️ Configuração"
   - Definir caminhos dos arquivos
   - Ajustar parâmetros de performance
   - Salvar configuração

2. **Execução do Sistema**

   - Ir para aba "📊 Dashboard"
   - Escolher tipo de execução:
     - **Sistema Integrado**: Inventário + Downloads
     - **Sistema Avançado**: Com Playwright e async
     - **Apenas Inventário**: Coleta de URLs
     - **Apenas Microserviço**: Downloads em background

3. **Monitoramento**

   - Acompanhar progresso nas abas específicas
   - Verificar logs em tempo real
   - Monitorar estatísticas no dashboard

4. **Análise de Resultados**
   - Verificar resultados do inventário
   - Analisar downloads concluídos
   - Revisar logs para debugging

## 🔍 Troubleshooting

### Problemas Comuns

#### 1. CustomTkinter não instalado

```bash
# Solução
pip install customtkinter
```

#### 2. Erro de importação de módulos

```bash
# Verificar se está no diretório correto
cd /path/to/CoupaDownloads
python src/MyScript/gui_main.py
```

#### 3. Interface não responsiva

- Verificar se sistemas estão executando em threads separadas
- Usar botão "⏹️ Parar Sistema" para interromper execuções

#### 4. Configurações não salvas

- Verificar permissões de escrita no diretório
- Usar caminhos absolutos para arquivos

### Logs de Debug

A GUI gera logs detalhados que podem ser salvos para análise:

- Timestamp de todas as operações
- Status de execução dos sistemas
- Erros e exceções capturadas
- Métricas de performance

## 🚀 Recursos Avançados

### Integração com Sistemas Existentes

A GUI integra-se perfeitamente com todos os sistemas MyScript:

- **Sistema Integrado**: `integrated_system.py`
- **Sistema de Inventário**: `inventory_system.py`
- **Microserviço**: `download_microservice.py`
- **Sistema Avançado**: `advanced_system.py`

### Extensibilidade

A interface é facilmente extensível:

- Adicionar novas abas para funcionalidades específicas
- Integrar novos sistemas de automação
- Personalizar temas e cores
- Adicionar novos tipos de monitoramento

### Performance

- Interface responsiva com threading
- Atualizações em tempo real sem bloqueio
- Gerenciamento eficiente de memória
- Logs otimizados para grandes volumes

## 📚 Documentação Relacionada

- **Diagrama do Sistema**: `SYSTEM_DIAGRAM.md`
- **Guia de Execução**: `EXECUTION_GUIDE.md`
- **Sistema Avançado**: `README_ADVANCED.md`
- **Sistema Integrado**: `README_NEW_SYSTEM.md`

## 🤝 Contribuição

Para contribuir com melhorias na GUI:

1. Fork do repositório
2. Criar branch para nova funcionalidade
3. Implementar mudanças na interface
4. Testar com diferentes configurações
5. Submeter pull request

## 📄 Licença

Este projeto segue a mesma licença do projeto principal CoupaDownloads.

---

**🎉 Aproveite a nova interface gráfica do MyScript!**
