# 🚀 Sistema Integrado de Inventário + Microserviço de Download

## 📋 Visão Geral

Este sistema implementa a nova arquitetura solicitada:

1. **Sistema de Inventário**: Coleta URLs de anexos sem baixar
2. **Microserviço de Download**: Monitora CSV e executa downloads em background
3. **Controle FIFO**: Gerencia abas por janela com limite configurável

## 🏗️ Arquitetura

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Sistema de    │    │   CSV de        │    │  Microserviço   │
│   Inventário    │───▶│   Controle      │◀───│  de Download    │
│                 │    │                 │    │                 │
│ • Carrega abas  │    │ • po_number     │    │ • Monitora CSV  │
│ • Inventaria    │    │ • url           │    │ • Download      │
│ • Salva URLs    │    │ • filename      │    │ • Atualiza      │
│ • Fecha abas    │    │ • status        │    │   status        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📁 Estrutura de Arquivos

```
src/MyScript/
├── inventory_system.py      # Sistema de inventário
├── download_microservice.py # Microserviço de download
├── integrated_system.py     # Sistema integrado
├── profile_config.py        # Configuração crítica do perfil
└── input.xlsx              # Arquivo Excel com POs
```

## 🚀 Como Usar

### 1. **Sistema Integrado (Recomendado)**

```bash
poetry run python src/MyScript/integrated_system.py
```

### 2. **Sistema de Inventário Apenas**

```bash
poetry run python src/MyScript/inventory_system.py
```

### 3. **Microserviço Apenas**

```bash
poetry run python src/MyScript/download_microservice.py
```

## ⚙️ Configurações

### Sistema de Inventário

- **Janelas**: 2-8 janelas paralelas
- **Abas por Janela**: 2-10 abas (FIFO)
- **Workers**: 2-10 workers paralelos
- **Perfil Edge**: Temporário, mínimo ou completo

### Microserviço de Download

- **Workers**: 2-10 downloads paralelos
- **Lote**: 3-20 arquivos por lote
- **Intervalo**: 1-30 segundos entre verificações
- **Diretório**: Configurável (padrão: ~/Downloads/CoupaDownloads)

## 📊 CSV de Controle

O sistema cria um arquivo `download_inventory.csv` com:

| Campo           | Descrição                            |
| --------------- | ------------------------------------ |
| `po_number`     | Número da PO                         |
| `url`           | URL do anexo                         |
| `filename`      | Nome do arquivo                      |
| `file_type`     | Tipo (pdf, document, etc.)           |
| `status`        | pending/downloading/completed/failed |
| `created_at`    | Data de criação                      |
| `downloaded_at` | Data de download                     |
| `error_message` | Mensagem de erro (se houver)         |
| `file_size`     | Tamanho do arquivo (bytes)           |

## 🔄 Fluxo de Execução

### 1. **Inventário**

```
PO1 → Aba → Inventário → URLs → CSV → Fecha Aba
PO2 → Aba → Inventário → URLs → CSV → Fecha Aba
PO3 → Aba → Inventário → URLs → CSV → Fecha Aba
...
```

### 2. **Download**

```
CSV → URLs Pendentes → Download Paralelo → Atualiza Status
CSV → URLs Pendentes → Download Paralelo → Atualiza Status
CSV → URLs Pendentes → Download Paralelo → Atualiza Status
...
```

## 🛡️ Proteção do Perfil

O sistema mantém a proteção crítica do perfil Edge:

- ✅ Função `verify_edge_profile_login_status()` protegida
- ✅ Configuração centralizada em `profile_config.py`
- ✅ Backup automático da configuração
- ✅ Script de verificação de integridade

## 📈 Monitoramento

### Interface Rich

- 📊 Estatísticas em tempo real
- 🔄 Status dos downloads
- 📦 Tamanho total baixado
- ⏱️ Tempo de execução

### Logs Detalhados

- ✅ Sucessos e falhas
- 🔍 Progresso por PO
- ⚠️ Avisos e erros
- 📝 URLs coletadas

## 🎯 Benefícios

### ✅ **Performance**

- Downloads paralelos e assíncronos
- Controle FIFO evita abas travadas
- Processamento em lotes otimizado

### ✅ **Confiabilidade**

- Sistema de inventário separado do download
- CSV como fonte única da verdade
- Recuperação automática de falhas

### ✅ **Flexibilidade**

- Configuração interativa
- Máximo de abas por janela configurável
- Workers e lotes ajustáveis

### ✅ **Monitoramento**

- Interface visual em tempo real
- Estatísticas detalhadas
- Logs completos

## 🔧 Troubleshooting

### Problema: CSV não encontrado

**Solução**: Execute primeiro o sistema de inventário

### Problema: Downloads falham

**Solução**: Verifique conexão e URLs no CSV

### Problema: Perfil não carrega

**Solução**: Execute `verify_profile_function.py` para verificar integridade

### Problema: Muitas abas abertas

**Solução**: Reduza `max_tabs_per_window` na configuração

## 📝 Exemplo de Uso

```bash
# 1. Executar sistema integrado
poetry run python src/MyScript/integrated_system.py

# 2. Escolher opção 3 (Executar Ambos)
# 3. Configurar inventário (2 janelas, 3 abas cada, 4 workers)
# 4. Aguardar inventário concluir
# 5. Configurar microserviço (4 workers, lote 5, intervalo 2s)
# 6. Monitorar downloads em tempo real
```

## 🎉 Resultado Final

- 📄 CSV com todas as URLs coletadas
- 📁 Arquivos baixados em `~/Downloads/CoupaDownloads`
- 📊 Relatório completo de sucessos/falhas
- ⚡ Processamento paralelo e assíncrono
- 🛡️ Perfil Edge protegido e funcional

