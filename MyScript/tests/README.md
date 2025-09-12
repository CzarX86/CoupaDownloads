# 🧪 Pasta de Testes - Sistema MyScript

## 📋 Visão Geral

Esta pasta contém todos os arquivos de teste, validação e experimentação do sistema MyScript, organizados de forma centralizada para facilitar a manutenção e execução dos testes.

## 📁 Estrutura da Pasta

### 🔬 **Testes Principais**

| Arquivo                                 | Descrição                                 | Tipo de Teste |
| --------------------------------------- | ----------------------------------------- | ------------- |
| `test_gui_execution.py`                 | Teste de execução da GUI sem abrir janela | Interface     |
| `test_complete.py`                      | Teste completo de todas as importações    | Integração    |
| `test_integration.py`                   | Teste de integração do sistema avançado   | Integração    |
| `test_advanced_system_comprehensive.py` | Teste abrangente do sistema avançado      | Sistema       |
| `test_new_system.py`                    | Teste do novo sistema de inventário       | Sistema       |

### 🔧 **Testes de Validação**

| Arquivo                       | Descrição                              | Tipo de Teste |
| ----------------------------- | -------------------------------------- | ------------- |
| `test_complete_system.py`     | Teste completo do sistema refatorado   | Validação     |
| `test_simple_verification.py` | Verificação simples de funcionalidades | Validação     |
| `test_refactored_system.py`   | Teste do sistema após refatoração      | Validação     |
| `test_final_gui.py`           | Teste final da GUI                     | Interface     |

### 📦 **Arquivos de Suporte**

| Arquivo                      | Descrição                       | Propósito         |
| ---------------------------- | ------------------------------- | ----------------- |
| `inventory_system_fixed.py`  | Sistema de inventário corrigido | Backup/Referência |
| `inventory_system_backup.py` | Backup do sistema de inventário | Backup            |
| `install_gui.py`             | Script de instalação da GUI     | Utilitário        |

## 🚀 Como Executar os Testes

### 📋 **Pré-requisitos**

1. **Dependências instaladas**: Certifique-se de que todas as dependências estão instaladas
2. **Configuração**: Arquivo `config.py` configurado corretamente
3. **Perfil Edge**: Perfil do Edge configurado (se necessário)

### 🔧 **Execução Individual**

```bash
# Teste de GUI
python3 tests/test_gui_execution.py

# Teste de integração
python3 tests/test_integration.py

# Teste completo
python3 tests/test_complete.py

# Teste do sistema avançado
python3 tests/test_advanced_system_comprehensive.py
```

### 🧪 **Execução em Lote**

```bash
# Executar todos os testes
for test in tests/test_*.py; do
    echo "Executando: $test"
    python3 "$test"
    echo "---"
done
```

## 📊 **Categorias de Teste**

### 🎨 **Testes de Interface (GUI)**

- `test_gui_execution.py` - Testa importação e inicialização da GUI
- `test_final_gui.py` - Teste final da interface gráfica

### 🔗 **Testes de Integração**

- `test_integration.py` - Testa integração entre módulos
- `test_complete.py` - Testa todas as importações básicas

### 🧠 **Testes de Sistema**

- `test_advanced_system_comprehensive.py` - Teste abrangente do sistema
- `test_new_system.py` - Teste do novo sistema de inventário

### ✅ **Testes de Validação**

- `test_complete_system.py` - Validação do sistema completo
- `test_simple_verification.py` - Verificação simples
- `test_refactored_system.py` - Validação pós-refatoração

## 🔍 **Detalhes Técnicos**

### 📁 **Estrutura de Importações**

Todos os arquivos de teste foram configurados para importar corretamente os módulos do diretório pai:

```python
# Adicionar o diretório pai ao path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Agora pode importar os módulos do MyScript
from coupa_workflow_orchestrator import AdvancedCoupaSystem
from coupa_inventory_collector import manage_inventory_system
```

### 🔄 **Módulos Atualizados**

Os testes foram atualizados para usar os novos nomes de módulos:

- `advanced_system` → `coupa_workflow_orchestrator`
- `inventory_system` → `coupa_inventory_collector`
- `services` → `download_services`
- `tab_managers` → `browser_tab_manager`
- `interfaces` → `ui_component_interfaces`

## 📈 **Cobertura de Testes**

### ✅ **Módulos Testados**

- ✅ `gui_main.py` - Interface principal
- ✅ `coupa_workflow_orchestrator.py` - Orquestrador principal
- ✅ `coupa_inventory_collector.py` - Coletor de inventário
- ✅ `playwright_system.py` - Sistema Playwright
- ✅ `download_services.py` - Serviços de download
- ✅ `browser_tab_manager.py` - Gerenciador de abas
- ✅ `config_advanced.py` - Configuração avançada

### 🔧 **Funcionalidades Testadas**

- ✅ Importação de módulos
- ✅ Inicialização de classes
- ✅ Configuração do sistema
- ✅ Execução da GUI
- ✅ Integração entre componentes
- ✅ Detecção de erros
- ✅ Validação de configurações

## 🚨 **Troubleshooting**

### ❌ **Problemas Comuns**

1. **Erro de Importação**

   ```
   ModuleNotFoundError: No module named 'coupa_workflow_orchestrator'
   ```

   **Solução**: Verifique se está executando da pasta `src/MyScript/`

2. **Erro de Dependências**

   ```
   ModuleNotFoundError: No module named 'customtkinter'
   ```

   **Solução**: Instale as dependências com `pip install -r requirements.txt`

3. **Erro de Configuração**
   ```
   FileNotFoundError: config.py not found
   ```
   **Solução**: Verifique se o arquivo `config.py` existe no diretório pai

### 🔧 **Comandos de Diagnóstico**

```bash
# Verificar estrutura de pastas
ls -la ../

# Verificar dependências
python3 -c "import customtkinter; print('✅ GUI OK')"

# Verificar configuração
python3 -c "from config import config_manager; print('✅ Config OK')"
```

## 📚 **Documentação Relacionada**

- `../README_GUI.md` - Documentação da GUI
- `../EXECUTION_GUIDE.md` - Guia de execução
- `../SYSTEM_WORKFLOW_DIAGRAM.md` - Diagrama do workflow
- `../REFACTORING_REPORT.md` - Relatório de refatoração

## 🎯 **Próximos Passos**

### 🔄 **Melhorias Planejadas**

1. **Testes automatizados** com pytest
2. **Cobertura de código** com coverage
3. **Testes de performance** com benchmarks
4. **Testes de integração** mais robustos

### 📊 **Métricas de Qualidade**

- **Cobertura de testes**: 85%+ (meta)
- **Tempo de execução**: < 5 minutos (meta)
- **Taxa de sucesso**: 95%+ (meta)

---

**Última Atualização**: 6 de Setembro de 2024  
**Status**: ✅ **Organização Concluída**  
**Próxima Revisão**: Após implementação de testes automatizados
