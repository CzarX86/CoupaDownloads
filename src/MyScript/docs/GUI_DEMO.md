# 🎨 Demonstração Visual da Interface MyScript GUI

## 📱 Layout da Interface Principal

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  🚀 MyScript - Sistema CoupaDownloads                                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│  📊 Dashboard  ⚙️ Configuração  📋 Inventário  📥 Downloads  ⚡ Avançado  📝 Logs │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  🚀 Sistema CoupaDownloads - Dashboard                                          │
│                                                                                 │
│  Status: 🔴 Sistema Parado                                                      │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  🔄 Executar Sistema Integrado  ⚡ Executar Sistema Avançado  ⏹️ Parar   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  📈 Estatísticas do Sistema                                                     │
│  ┌─────────────────┬─────────────────┬─────────────────┐                     │
│  │ POs Processadas  │ Attachments      │ Downloads       │                     │
│  │      0          │ Encontrados      │ Concluídos      │                     │
│  │                 │      0           │      0          │                     │
│  ├─────────────────┼─────────────────┼─────────────────┤                     │
│  │ Taxa de Sucesso │ Tempo Execução   │ Arquivos        │                     │
│  │      0%         │    00:00:00      │ Baixados        │                     │
│  │                 │                 │      0 MB       │                     │
│  └─────────────────┴─────────────────┴─────────────────┘                     │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## ⚙️ Aba de Configuração

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ⚙️ Configurações do Sistema                                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  📁 Arquivos                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ Arquivo Excel: [src/MyScript/input.xlsx                    ] [📂]      │   │
│  │ Arquivo CSV:   [src/MyScript/download_inventory.csv         ] [📂]      │   │
│  │ Diretório:     [~/Downloads/CoupaDownloads                  ] [📂]      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ⚡ Performance                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ Número de Janelas:     [━━━━━━━━━━] 2                                   │   │
│  │ Abas por Janela:       [━━━━━━━━━━] 3                                   │   │
│  │ Workers Paralelos:     [━━━━━━━━━━] 4                                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  🔧 Configurações Avançadas                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ ☐ Modo Headless (sem interface gráfica)                                │   │
│  │ Modo do Perfil: [minimal ▼]                                            │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  💾 Salvar Configuração  📂 Carregar Configuração  🔄 Resetar Padrões   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 📋 Aba de Inventário

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📋 Sistema de Inventário                                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  📋 Sistema de Inventário                                                        │
│  Coleta URLs de anexos das POs sem baixar os arquivos                          │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    🚀 Executar Inventário                               │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  Progresso: [████████████████████████████████████████████████████████████████]   │
│                                                                                 │
│  Status: Aguardando execução...                                                 │
│                                                                                 │
│  📊 Resultados do Inventário                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ PO        │ URL                    │ Attachments │ Status                │   │
│  ├───────────┼────────────────────────┼─────────────┼──────────────────────┤   │
│  │ PO123456  │ https://unilever...    │ 3           │ ✅ Concluído          │   │
│  │ PO123457  │ https://unilever...    │ 0           │ ❌ Erro               │   │
│  │ PO123458  │ https://unilever...    │ 2           │ ✅ Concluído          │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 📥 Aba de Downloads

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📥 Microserviço de Download                                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  📥 Microserviço de Download                                                    │
│  Monitora CSV e executa downloads em background                                │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    🔄 Iniciar Microserviço                             │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  Tamanho do Lote: [━━━━━━━━━━] 5                                               │
│                                                                                 │
│  Status: Microserviço parado                                                    │
│                                                                                 │
│  📊 Downloads em Andamento                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ PO        │ Arquivo           │ Status      │ Tamanho │ Progresso       │   │
│  ├───────────┼───────────────────┼─────────────┼─────────┼────────────────┤   │
│  │ PO123456  │ invoice.pdf       │ 🔄 Baixando │ 2.5 MB  │ [████████████]  │   │
│  │ PO123456  │ receipt.pdf       │ ✅ Concluído│ 1.2 MB  │ [████████████]  │   │
│  │ PO123457  │ contract.docx     │ ❌ Falhou   │ 0 MB    │ [            ]  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## ⚡ Aba Avançada

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ⚡ Sistema Avançado                                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ⚡ Sistema Avançado                                                             │
│  Sistema com Playwright, downloads assíncronos e processamento otimizado       │
│                                                                                 │
│  🔧 Recursos Avançados                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ ☑ 🎭 Playwright (automação moderna)                                   │   │
│  │ ☑ ⚡ Downloads Assíncronos                                            │   │
│  │ ☑ 📊 Polars (processamento rápido)                                     │   │
│  │ ☑ 🔄 Sistema de Retry Inteligente                                     │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    🚀 Executar Sistema Avançado                        │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  Status: Sistema avançado parado                                                │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 📝 Aba de Logs

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  📝 Logs do Sistema                                                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  📝 Logs do Sistema                                                             │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  🗑️ Limpar Logs  💾 Salvar Logs                    ☑ Auto-scroll      │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │ [14:30:15] 🚀 Sistema MyScript GUI iniciado                           │   │
│  │ [14:30:15] 📋 Interface carregada com sucesso                          │   │
│  │ [14:30:20] ⚙️ Configuração carregada de myscript_config.json           │   │
│  │ [14:30:25] 🚀 Iniciando Sistema Integrado...                           │   │
│  │ [14:30:26] 🔧 Configurando driver Edge...                              │   │
│  │ [14:30:27] ✅ Perfil Edge carregado: ~/Library/Application Support...  │   │
│  │ [14:30:28] 📋 Iniciando Sistema de Inventário...                       │   │
│  │ [14:30:30] 📊 Encontrados 150 números de PO no Excel                   │   │
│  │ [14:30:32] 🚀 Iniciando carregamento de 150 URLs do Coupa...           │   │
│  │ [14:30:35] 📄 Criando nova aba em Janela 1 para URL 1/150              │   │
│  │ [14:30:36] ✅ PO123456 processada com sucesso (3 attachments)          │   │
│  │ [14:30:38] 📄 Criando nova aba em Janela 2 para URL 2/150              │   │
│  │ [14:30:40] ✅ PO123457 processada com sucesso (2 attachments)          │   │
│  │ [14:30:42] 📄 Criando nova aba em Janela 1 para URL 3/150              │   │
│  │ [14:30:44] ❌ PO123458 não processada: Página de erro detectada         │   │
│  │ [14:30:45] 📊 Progresso do inventário: 2.0% (3/150)                     │   │
│  │ [14:30:50] 📥 Iniciando Microserviço de Download...                    │   │
│  │ [14:30:52] 📋 Encontrados 5 downloads pendentes                        │   │
│  │ [14:30:53] 🔄 Processando lote 1: 5 arquivos                            │   │
│  │ [14:30:55] ✅ Lote concluído: 4 sucessos, 1 falha                      │   │
│  │ [14:30:56] ✅ Sistema Integrado concluído com sucesso!                  │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🎨 Paleta de Cores da Interface

### Tema Dark (Padrão)

- **Background Principal**: `#2b2b2b` (Cinza escuro)
- **Background Secundário**: `#3a3a3a` (Cinza médio)
- **Texto Principal**: `#ffffff` (Branco)
- **Texto Secundário**: `#b0b0b0` (Cinza claro)
- **Accent Blue**: `#1f538d` (Azul principal)
- **Accent Green**: `#2d5a2d` (Verde para sucesso)
- **Accent Red**: `#5a2d2d` (Vermelho para erro)
- **Accent Orange**: `#5a4a2d` (Laranja para avisos)

### Elementos Visuais

- **Bordas**: Cantos arredondados com `border_radius=10`
- **Sombras**: Efeito de profundidade sutil
- **Ícones**: Emojis para identificação rápida
- **Sliders**: Controles deslizantes com feedback visual
- **Botões**: Estados hover e active diferenciados

## 🔄 Estados da Interface

### Sistema Parado

```
Status: 🔴 Sistema Parado
Botões: [🔄 Executar Sistema Integrado] [⚡ Executar Sistema Avançado] [⏹️ Parar Sistema]
Cor: Vermelho (#5a2d2d)
```

### Sistema Executando

```
Status: 🟡 Sistema Integrado Executando
Botões: [🔄 Executar Sistema Integrado] [⚡ Executar Sistema Avançado] [⏹️ Parar Sistema]
Cor: Amarelo (#5a4a2d)
```

### Sistema Concluído

```
Status: 🟢 Sistema Integrado Concluído
Botões: [🔄 Executar Sistema Integrado] [⚡ Executar Sistema Avançado] [⏹️ Parar Sistema]
Cor: Verde (#2d5a2d)
```

### Sistema com Erro

```
Status: 🔴 Erro no Sistema Integrado
Botões: [🔄 Executar Sistema Integrado] [⚡ Executar Sistema Avançado] [⏹️ Parar Sistema]
Cor: Vermelho (#5a2d2d)
```

## 📱 Responsividade

### Tamanhos de Janela

- **Mínimo**: 1000x700 pixels
- **Recomendado**: 1200x800 pixels
- **Máximo**: Sem limite (expande conforme necessário)

### Adaptação de Layout

- **Abas**: Redimensionam automaticamente
- **Tabelas**: Scroll horizontal quando necessário
- **Sliders**: Mantêm proporção em diferentes tamanhos
- **Botões**: Expandem para preencher espaço disponível

## 🎯 Experiência do Usuário

### Fluxo de Navegação

1. **Dashboard** → Visão geral e controle principal
2. **Configuração** → Ajustar parâmetros
3. **Inventário/Downloads** → Monitorar execuções específicas
4. **Avançado** → Recursos avançados
5. **Logs** → Debugging e análise

### Feedback Visual

- **Cores**: Indicam status e tipo de informação
- **Ícones**: Facilitam identificação rápida
- **Progresso**: Barras e percentuais em tempo real
- **Animações**: Transições suaves entre estados

### Acessibilidade

- **Contraste**: Alto contraste para legibilidade
- **Tamanhos**: Fontes e elementos adequados
- **Navegação**: Tab order lógico
- **Atalhos**: Teclas de acesso rápido (futuro)

---

**🎨 Interface projetada para máxima usabilidade e eficiência!**

