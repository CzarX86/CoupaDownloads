# RELATÓRIO TECNOLÓGICO - SISTEMA DE EXTRAÇÃO COUPA

## 📊 RESUMO EXECUTIVO

O sistema atual utiliza **6 tecnologias principais** funcionando em conjunto para extração de campos de contratos PDF:

1. **PDF Processing** (pdfplumber + PyPDF2)
2. **NLP Básico** (spaCy NER)
3. **NLP Avançado** (BERT NER)
4. **LLM Local** (Ollama phi3:mini)
5. **Busca Semântica** (Sentence Transformers)
6. **Padrões Treinados** (Regex baseado em dados reais)

## 🔧 TECNOLOGIAS IMPLEMENTADAS

### 1. PDF PROCESSING

- **Bibliotecas**: pdfplumber, PyPDF2
- **Status**: ✅ Funcionando
- **Função**: Extração de texto de PDFs
- **Performance**: Boa para PDFs com texto, limitada para PDFs escaneados

### 2. NLP BÁSICO (spaCy)

- **Modelo**: en_core_web_sm
- **Status**: ✅ Funcionando
- **Função**: Named Entity Recognition (NER) básico
- **Capacidades**: Identifica organizações, valores, datas
- **Limitações**: Modelo geral, não especializado em contratos

### 3. NLP AVANÇADO (BERT)

- **Modelo**: dbmdz/bert-large-cased-finetuned-conll03-english
- **Status**: ✅ Funcionando
- **Função**: NER avançado para entidades específicas
- **Capacidades**: Reconhecimento de entidades mais preciso
- **Limitações**: Warning sobre pesos não utilizados (resolvido)

### 4. LLM LOCAL (Ollama)

- **Modelo**: phi3:mini
- **Status**: ✅ Funcionando
- **Função**: Extração inteligente de campos usando prompts estruturados
- **Capacidades**: Compreensão contextual, extração de campos complexos
- **Performance**: ~30 segundos por documento

### 5. BUSCA SEMÂNTICA (Sentence Transformers)

- **Modelo**: all-MiniLM-L6-v2 (fallback do EmbeddingGemma)
- **Status**: ✅ Funcionando
- **Função**: Busca semântica para campos específicos
- **Capacidades**: Similaridade semântica, embeddings de texto
- **Limitações**: EmbeddingGemma não disponível (modelo gated)

### 6. PADRÕES TREINADOS

- **Fonte**: Planilha Contract_Tracker (275 registros)
- **Status**: ✅ Funcionando
- **Função**: Regex patterns baseados em dados reais
- **Capacidades**: 6 padrões específicos para campos críticos
- **Validação**: Baseada em distribuições dos dados reais

## 📈 PERFORMANCE ATUAL

### Confiança de Extração

- **Antes**: 85% (com dados inconsistentes)
- **Depois**: 100% (com validação melhorada)
- **Campos Extraídos**: 13/22 campos (59%)

### Tempo de Processamento

- **PDF Processing**: ~2 segundos
- **NLP Libraries**: ~5 segundos
- **Ollama LLM**: ~30 segundos
- **Total**: ~37 segundos por documento

### Campos Mais Precisos

1. **contract_name**: 90.9% dos dados disponíveis
2. **contract_type**: 89.1% dos dados disponíveis
3. **contract_start_date**: 89.5% dos dados disponíveis
4. **contract_end_date**: 89.5% dos dados disponíveis
5. **managed_by**: 89.5% dos dados disponíveis

## 🎯 LIMITAÇÕES IDENTIFICADAS

### 1. Campos com Poucos Dados

- **Minimum Commitment Value**: 0% dos dados disponíveis
- **Inflation %**: 0% dos dados disponíveis
- **Opportunity Available**: 0% dos dados disponíveis
- **Procurement negotiation strategy**: 0% dos dados disponíveis
- **Supporting information**: 0% dos dados disponíveis

### 2. Problemas de Qualidade

- **Dados Inconsistentes**: Mesmo com 100% de confiança, dados não condizentes
- **Validação Insuficiente**: Necessário melhorar validação de valores extraídos
- **Contexto Limitado**: LLM pode estar extraindo informações incorretas

### 3. Performance

- **Tempo de Processamento**: 37 segundos por documento é lento
- **Uso de Memória**: Múltiplas bibliotecas carregadas simultaneamente
- **Escalabilidade**: Não otimizado para processamento em lote

## 🚀 PRÓXIMOS PASSOS RECOMENDADOS

### 1. Melhorar Validação de Dados

- Implementar validação cruzada entre diferentes técnicas
- Adicionar verificações de consistência lógica
- Criar sistema de scoring por campo individual

### 2. Otimizar Performance

- Implementar processamento em lote
- Cache de resultados intermediários
- Paralelização de extrações

### 3. Expandir Dados de Treinamento

- Usar mais registros da planilha (atualmente usando apenas 20)
- Implementar aprendizado incremental
- Criar validação manual de resultados

### 4. Implementar Fallback Inteligente

- Sistema de fallback baseado em confiança
- Validação cruzada entre técnicas
- Correção automática de valores inconsistentes

## 📊 MÉTRICAS DE SUCESSO

### Atuais

- ✅ 6/6 tecnologias funcionando
- ✅ 13/22 campos extraídos (59%)
- ✅ 100% de confiança técnica
- ❌ Qualidade dos dados inconsistente

### Objetivos

- 🎯 18/22 campos extraídos (82%)
- 🎯 95%+ de precisão nos dados
- 🎯 <20 segundos por documento
- 🎯 Validação automática de consistência

## 🔍 CONCLUSÃO

O sistema está **tecnicamente funcional** com todas as tecnologias implementadas, mas precisa de **melhorias na qualidade dos dados extraídos**. A confiança de 100% não reflete a precisão real dos dados, indicando necessidade de:

1. **Validação mais rigorosa** dos valores extraídos
2. **Melhor integração** entre as diferentes técnicas
3. **Otimização de performance** para uso prático
4. **Expansão dos dados de treinamento** para melhorar precisão

O sistema tem uma **base sólida** e está pronto para refinamentos focados na qualidade dos dados.

