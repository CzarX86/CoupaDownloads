# Advanced NLP Libraries Installation Guide

## 📚 Guia de Instalação de Bibliotecas NLP Avançadas

Este guia mostra como instalar e configurar as bibliotecas NLP para melhorar a extração de campos dos PDFs.

### 🚀 Instalação Rápida

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Instalar bibliotecas básicas
pip install spacy transformers sentence-transformers langchain ollama scikit-learn

# Baixar modelos spaCy
python -m spacy download pt_core_news_sm
python -m spacy download en_core_web_sm
```

### 📦 Bibliotecas Disponíveis

#### 1. **spaCy** - Named Entity Recognition (NER)

```bash
pip install spacy
python -m spacy download pt_core_news_sm  # Português
python -m spacy download en_core_web_sm   # Inglês
```

**Funcionalidades:**

- Extração de entidades nomeadas (datas, valores, organizações)
- Reconhecimento de padrões linguísticos
- Processamento de texto em português e inglês

#### 2. **Transformers/BERT** - Named Entity Recognition Avançado

```bash
pip install transformers torch
```

**Funcionalidades:**

- Modelos BERT pré-treinados para NER
- Reconhecimento de entidades em contexto
- Alta precisão para textos complexos

#### 3. **Sentence Transformers** - Busca Semântica

```bash
pip install sentence-transformers
```

**Funcionalidades:**

- Embeddings semânticos para busca de similaridade
- Suporte ao EmbeddingGemma
- Comparação de textos por significado

#### 4. **LangChain** - Processamento de Texto

```bash
pip install langchain
```

**Funcionalidades:**

- Divisão inteligente de texto
- Integração com múltiplos modelos
- Pipelines de processamento

#### 5. **Ollama** - Modelos Locais

```bash
pip install ollama
```

**Modelos Recomendados:**

```bash
# Instalar Ollama (macOS)
brew install ollama

# Baixar modelos
ollama pull phi3
ollama pull llama2
ollama pull mistral
```

### 🔧 Configuração Progressiva

#### **Fase 1: spaCy (NER Básico)**

```bash
pip install spacy
python -m spacy download pt_core_news_sm
```

**Teste:**

```bash
python extract_advanced_coupa_fields.py
```

#### **Fase 2: + Transformers (BERT)**

```bash
pip install transformers torch
```

**Teste novamente para ver melhoria na precisão.**

#### **Fase 3: + Sentence Transformers (Busca Semântica)**

```bash
pip install sentence-transformers
```

**Teste para ver melhoria na busca de campos.**

#### **Fase 4: + LangChain (Processamento Avançado)**

```bash
pip install langchain
```

#### **Fase 5: + Ollama (Modelos Locais)**

```bash
pip install ollama
ollama pull phi3
```

### 📊 Comparação de Performance

| Biblioteca                | Campos Encontrados   | Precisão   | Velocidade | Uso de Memória |
| ------------------------- | -------------------- | ---------- | ---------- | -------------- |
| **spaCy**                 | Datas, Valores, Orgs | Alta       | Rápida     | Baixa          |
| **BERT**                  | Entidades Complexas  | Muito Alta | Média      | Alta           |
| **Sentence Transformers** | Busca Semântica      | Alta       | Média      | Média          |
| **LangChain**             | Processamento        | Média      | Rápida     | Baixa          |
| **Ollama**                | Extração Geral       | Muito Alta | Lenta      | Alta           |

### 🎯 Estratégia de Implementação

#### **Abordagem Incremental**

1. **Começar com spaCy** - NER básico para datas e valores
2. **Adicionar BERT** - Melhorar reconhecimento de entidades
3. **Incluir Sentence Transformers** - Busca semântica para campos específicos
4. **Integrar LangChain** - Processamento de texto mais inteligente
5. **Implementar Ollama** - Modelos locais para extração geral

#### **Configuração por Ambiente**

**Desenvolvimento (Mínimo):**

```bash
pip install spacy sentence-transformers
python -m spacy download pt_core_news_sm
```

**Produção (Completo):**

```bash
pip install spacy transformers sentence-transformers langchain ollama
python -m spacy download pt_core_news_sm
python -m spacy download en_core_web_sm
ollama pull phi3
```

### 🔍 Teste de Funcionalidades

#### **Teste spaCy**

```python
import spacy
nlp = spacy.load("pt_core_news_sm")
doc = nlp("Contrato de R$ 50.000,00 válido de 01/01/2024 a 31/12/2024")
for ent in doc.ents:
    print(f"{ent.text}: {ent.label_}")
```

#### **Teste BERT**

```python
from transformers import pipeline
ner = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")
result = ner("Contract value: €125,000")
print(result)
```

#### **Teste Sentence Transformers**

```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(["contract value", "valor do contrato"])
similarity = cosine_similarity(embeddings[0], embeddings[1])
print(similarity)
```

#### **Teste Ollama**

```python
import ollama
response = ollama.generate(
    model='phi3',
    prompt='Extract contract information from: Contract ABC-123, Value: €50,000'
)
print(response['response'])
```

### 📈 Monitoramento de Performance

#### **Métricas Importantes**

- **Taxa de Sucesso**: % de documentos com campos extraídos
- **Precisão**: Qualidade dos campos encontrados
- **Velocidade**: Tempo por documento
- **Uso de Memória**: RAM utilizada

#### **Logs de Debug**

```bash
# Executar com logs detalhados
python extract_advanced_coupa_fields.py 2>&1 | grep -E "(spaCy|BERT|Semantic|LLM)"
```

### 🛠️ Troubleshooting

#### **Problemas Comuns**

1. **"spaCy model not found"**

   ```bash
   python -m spacy download pt_core_news_sm
   ```

2. **"CUDA out of memory" (BERT)**

   ```python
   # Usar CPU em vez de GPU
   pipeline("ner", model="...", device=-1)
   ```

3. **"Ollama connection failed"**

   ```bash
   # Verificar se Ollama está rodando
   ollama list
   ```

4. **"Sentence transformer download failed"**
   ```bash
   # Usar modelo menor
   SentenceTransformer("all-MiniLM-L6-v2")
   ```

### 🎯 Próximos Passos

1. **Instalar bibliotecas progressivamente**
2. **Testar cada adição individualmente**
3. **Monitorar melhoria na precisão**
4. **Ajustar configurações conforme necessário**
5. **Implementar modelos Ollama locais**

---

**Nota**: Este sistema é modular - você pode usar apenas as bibliotecas que desejar, e o sistema se adaptará automaticamente.
