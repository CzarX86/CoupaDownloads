# 🚀 GUIA DE EXECUÇÃO - Sistema Refatorado

## 📋 Opções de Execução

### 1. **Sistema Principal (Recomendado)**
```bash
# Executar o sistema completo de inventário
poetry run python src/MyScript/inventory_system.py
```

### 2. **Sistema Original (Compatibilidade)**
```bash
# Executar o sistema original (se necessário)
poetry run python src/MyScript/myScript_advanced.py
```

### 3. **Testes**
```bash
# Testar configurações
poetry run python src/MyScript/test_refactored_system.py

# Testar funcionalidades
poetry run python src/MyScript/test_simple_verification.py
```

## 🎯 Sistema Principal - inventory_system.py

### **Funcionalidades:**
- ✅ **Detecção de erro** implementada
- ✅ **Salvamento no CSV** funcionando
- ✅ **Interface interativa** para configuração
- ✅ **Processamento paralelo** e assíncrono
- ✅ **Controle FIFO** de abas
- ✅ **Microserviço de download** em background

### **Fluxo de Execução:**
1. **Configuração Interativa**: Define número de janelas, abas por janela, etc.
2. **Carregamento do Perfil**: Verifica se o perfil Edge está funcionando
3. **Leitura do Excel**: Carrega números de PO do arquivo `input.xlsx`
4. **Inventário**: Coleta URLs de anexos sem baixar
5. **Salvamento CSV**: Salva todas as URLs coletadas em `download_inventory.csv`
6. **Microserviço**: Inicia download em background (opcional)

## 📁 Arquivos Importantes

- **`input.xlsx`**: Arquivo com números de PO para processar
- **`download_inventory.csv`**: CSV com URLs coletadas (criado automaticamente)
- **`profile_config.py`**: Configurações críticas do perfil Edge

## ⚙️ Configurações

O sistema usa configurações interativas, mas você pode modificar:
- **Número de janelas**: Quantas janelas do Edge usar
- **Abas por janela**: Máximo de abas por janela (padrão: 3)
- **Timeout**: Tempo limite para carregamento de páginas
- **Modo headless**: Executar sem interface gráfica

## 🔧 Solução de Problemas

### **Erro de Perfil Edge:**
```bash
# Fechar todas as instâncias do Edge primeiro
# Depois executar o sistema
```

### **Arquivo Excel não encontrado:**
```bash
# Verificar se src/MyScript/input.xlsx existe
# Ou modificar o caminho em config.py
```

### **Erro de Importação:**
```bash
# Usar sempre poetry run python para garantir dependências
poetry run python src/MyScript/inventory_system.py
```

## 📊 Monitoramento

Durante a execução, você verá:
- **Status das abas**: Quantas abas estão ativas por janela
- **Progresso**: URLs processadas e anexos encontrados
- **Erros detectados**: POs não acessíveis ou páginas de erro
- **CSV sendo populado**: URLs sendo salvas em tempo real

## 🎉 Resultado Final

Após a execução, você terá:
- **`download_inventory.csv`**: Com todas as URLs coletadas
- **Logs detalhados**: Do processamento
- **Estatísticas**: De sucessos e falhas
- **Microserviço**: Executando downloads em background (se ativado)

