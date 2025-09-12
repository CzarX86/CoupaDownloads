# 📁 Módulos Não Utilizados

Esta pasta contém módulos que foram identificados como não fazendo parte do workflow atual do sistema MyScript.

## 📋 Módulos Movidos

### 🔧 integrated_system.py

- **Status**: ❌ Não utilizado no workflow atual
- **Motivo**: O sistema atual usa `advanced_system.py` como orquestrador principal
- **Funcionalidade**: Sistema integrado com Selenium + microserviço de download
- **Substituído por**: `advanced_system.py` (Playwright + downloads assíncronos)

### 🚀 main.py

- **Status**: ❌ Não utilizado no workflow atual
- **Motivo**: Apenas um wrapper que chama `gui_main.py`
- **Funcionalidade**: Entry point alternativo para o sistema
- **Substituído por**: `gui_main.py` é o entry point principal atual

### 📜 myScript.py

- **Status**: ❌ Não utilizado no workflow atual
- **Motivo**: Sistema antigo baseado em Selenium com gerenciamento manual de abas
- **Funcionalidade**: Gerenciamento de múltiplas abas no Edge WebDriver
- **Substituído por**: `playwright_system.py` (Playwright com gerenciamento automático)

### 🚀 myScript_advanced.py

- **Status**: ❌ Não utilizado no workflow atual
- **Motivo**: Versão avançada do sistema antigo, não integrada ao sistema atual
- **Funcionalidade**: Sistema avançado baseado em Selenium
- **Substituído por**: `advanced_system.py` (Sistema atual com Playwright)

### 🐍 run_poetry.py

- **Status**: ❌ Não utilizado no workflow atual
- **Motivo**: Script de execução específico para Poetry, não integrado ao sistema
- **Funcionalidade**: Execução do sistema via Poetry
- **Substituído por**: `gui_main.py` (Interface gráfica principal)

### 🏃 run.py

- **Status**: ❌ Não utilizado no workflow atual
- **Motivo**: Script de execução alternativo, não referenciado no sistema atual
- **Funcionalidade**: Entry point alternativo
- **Substituído por**: `gui_main.py` (Entry point principal atual)

## 🔍 Análise Realizada

### Verificação de Importações

- ✅ Verificado que `integrated_system` é importado mas nunca usado em `gui_main.py`
- ✅ Verificado que `main.py` não é referenciado em nenhum lugar do sistema atual
- ✅ Confirmado que o sistema atual usa `advanced_system.py` como orquestrador
- ✅ Verificado que módulos Selenium antigos não são mais utilizados
- ✅ Confirmado que scripts de execução alternativos não são referenciados

### Workflow Atual

O sistema MyScript atual segue este fluxo:

1. **Entry Point**: `gui_main.py` (Interface CustomTkinter)
2. **Orquestrador**: `advanced_system.py` (AdvancedCoupaSystem)
3. **Automação Web**: `playwright_system.py` (Playwright + Edge)
4. **Processamento**: `polars_processor.py` (Dados eficientes)
5. **Downloads**: `async_downloader.py` (Downloads assíncronos)

## 💡 Possível Reutilização

Estes módulos podem ser úteis para:

- **Desenvolvimento futuro**: Se precisar de funcionalidades específicas
- **Referência**: Como exemplos de implementação alternativa
- **Migração**: Se decidir voltar ao sistema Selenium
- **Histórico**: Manter registro das versões anteriores do sistema

## 🗑️ Remoção Segura

Estes arquivos podem ser removidos permanentemente se:

- ✅ Não forem necessários para funcionalidades futuras
- ✅ O sistema atual atender todas as necessidades
- ✅ Não houver planos de migração de volta ao Selenium
- ✅ Não precisar manter histórico de versões anteriores

---

_Análise realizada em: $(date)_
_Sistema atual: MyScript v2.0 (Playwright + Async)_
