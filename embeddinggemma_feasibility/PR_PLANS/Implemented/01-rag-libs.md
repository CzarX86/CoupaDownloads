# PR 01 — RAG local mínimo (LlamaIndex + hnswlib)

Repositório: CoupaDownloads — subprojeto `embeddinggemma_feasibility`.
Tipo: Plan PR (documentação apenas, sem alterações de código).

## Objetivo
Adicionar uma stack mínima de RAG local, leve e reproduzível, para suportar:
- Busca semântica em documentos (PDF/Texto) do domínio Coupa/contratos.
- Reranking opcional para melhorar precisão dos top-k resultados.
- Persistência de índice em disco, com controle por flags/env.

Foco em execução no MacBook Air M3 (8GB), priorizando modelos pequenos e indexador leve.

## Escopo
- Orquestrador: `llama-index` (simples para POCs; evitamos LangChain neste PR para reduzir complexidade).
- Vetor store: `hnswlib` (leve, rápido, sem servidor).
- Embeddings: `sentence-transformers` (default: `intfloat/multilingual-e5-small` ou `bge-small-en-v1.5`, 384 dims).
- Reranker opcional: `cross-encoder/ms-marco-MiniLM-L-6-v2` via `sentence-transformers`.
- Novos módulos em `embeddinggemma_feasibility/rag/` com pipeline ingest → split → index → retrieve → rerank.
- Persistência padrão do índice em `embeddinggemma_feasibility/data/rag_index/` (configurável).
- Atualização da documentação do subprojeto para instruções de uso.

Fora de escopo: agentes, ferramentas externas, LLM local, mudanças em extratores existentes, alterações de arquitetura global.

## Arquivos afetados
- Novo: `embeddinggemma_feasibility/rag/__init__.py`
- Novo: `embeddinggemma_feasibility/rag/config.py`
- Novo: `embeddinggemma_feasibility/rag/splitters.py`
- Novo: `embeddinggemma_feasibility/rag/ingest.py`
- Novo: `embeddinggemma_feasibility/rag/index.py`
- Novo: `embeddinggemma_feasibility/rag/retrieve.py`
- Novo: `embeddinggemma_feasibility/rag/rerank.py`
- Novo: `embeddinggemma_feasibility/rag/cli.py`
- Novo: `embeddinggemma_feasibility/docs/RAG_MINIMAL.md` (guia rápido)
- Alterado: `embeddinggemma_feasibility/requirements.txt` (adicionar deps) — apenas na implementação.

## Pseudodiff (representativo)
```
+ embeddinggemma_feasibility/rag/__init__.py
+ embeddinggemma_feasibility/rag/config.py
+ embeddinggemma_feasibility/rag/splitters.py
+ embeddinggemma_feasibility/rag/ingest.py
+ embeddinggemma_feasibility/rag/index.py
+ embeddinggemma_feasibility/rag/retrieve.py
+ embeddinggemma_feasibility/rag/rerank.py
+ embeddinggemma_feasibility/rag/cli.py
+ embeddinggemma_feasibility/docs/RAG_MINIMAL.md
~ embeddinggemma_feasibility/requirements.txt
```

Excertos ilustrativos:

`rag/config.py`
```python
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class RAGConfig:
    index_dir: Path = Path(os.getenv("RAG_INDEX_DIR", "embeddinggemma_feasibility/data/rag_index"))
    embed_model: str = os.getenv("RAG_EMBED_MODEL", "intfloat/multilingual-e5-small")
    use_reranker: bool = os.getenv("RAG_USE_RERANKER", "0") == "1"
    top_k: int = int(os.getenv("RAG_TOP_K", 8))
    return_k: int = int(os.getenv("RAG_RETURN_K", 3))
```

`rag/index.py`
```python
from llama_index.core import VectorStoreIndex, Document, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.hnswlib import HnswlibVectorStore

# build_index(texts, metadatas) -> persist in config.index_dir
```

`rag/retrieve.py`
```python
# query_index(query: str, top_k: int) -> List[Candidate]
```

`rag/rerank.py`
```python
# rerank(candidates, query) using CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
```

`rag/cli.py`
```bash
# Build
python -m embeddinggemma_feasibility.rag.cli build \
  --source embeddinggemma_feasibility/data/sample_documents \
  --persist embeddinggemma_feasibility/data/rag_index

# Query
python -m embeddinggemma_feasibility.rag.cli query \
  --index embeddinggemma_feasibility/data/rag_index \
  --q "Como está definido o prazo de pagamento?" \
  --top-k 8 --return-k 3 --reranker 1
```

`embeddinggemma_feasibility/requirements.txt`
```
+ llama-index>=0.10
+ hnswlib>=0.8.0
# já temos: sentence-transformers, transformers, torch, pdfplumber
+ diskcache>=5.6.1  # cache leve de embeddings/queries (opcional)
```

## Critérios de aceitação
- Build do índice:
  - Comando de build ingere PDFs/texto de um diretório, gera chunks e persiste índice HNSW + metadados em disco.
  - Permite escolher modelo de embedding via flag/env; default compatível com 8GB RAM.
- Consulta e reranking:
  - Comando de query retorna top-k com score e metadados; reranker opcional melhora ordenação quando ativado.
  - Parâmetros `top_k` e `return_k` configuráveis; latência aceitável (<2s em 500–1k chunks, sem reranker).
- Estruturas e validação:
  - Respostas usam modelos `pydantic` (shape: id, score, snippet, source_path, chunk_idx).
  - Persistência reabrível: após reiniciar, `query` funciona sem rebuild.
- Documentação:
  - `docs/RAG_MINIMAL.md` descreve instalação, build, query, flags e troubleshooting.
- Não regressão:
  - Nenhum código existente é alterado ou quebrado; RAG é módulo isolado.

## Testes manuais mínimos
1) Instalação deps do subprojeto (ambiente isolado):
   - `pip install -r embeddinggemma_feasibility/requirements.txt`
2) Build do índice com documentos de exemplo:
   - `python -m embeddinggemma_feasibility.rag.cli build --source embeddinggemma_feasibility/data/sample_documents --persist embeddinggemma_feasibility/data/rag_index`
3) Consulta sem reranker:
   - `python -m embeddinggemma_feasibility.rag.cli query --index embeddinggemma_feasibility/data/rag_index --q "termos de entrega" --top-k 8 --return-k 3`
4) Consulta com reranker:
   - `RAG_USE_RERANKER=1 python -m embeddinggemma_feasibility.rag.cli query --index embeddinggemma_feasibility/data/rag_index --q "prazo de pagamento"`
5) Verificar persistência (apagar cache de memória, reutilizar diretório `rag_index`).

## Considerações de performance (M3 8GB)
- Chunking: 300–500 tokens, overlap 30–50; máximo ~50k tokens indexados por batch.
- hnswlib: `M=16`, `efConstruction=100`, `ef=50–100` no retrieval.
- Modelos ≤512 dims (ex.: 384) para reduzir RAM/armazenamento.
- Reranker aplicado apenas nos top-k (ex.: 8 → retorna 3) para manter latência baixa.

## Riscos e mitigação
- Peso de dependências: manter apenas `llama-index` + `hnswlib` além do que já existe; nada de servidores externos.
- PDFs problemáticos: fallback para extrair texto com `pdfplumber`; logs claros quando falhar.
- Internacionalização: default `multilingual-e5-small` cobre pt/en; documentar como trocar.

## Mensagem e branch sugeridos
- Branch (plan): `plan/01-rag-libs`
- Commit (plan): `docs(pr-plan): PR 01 — RAG local mínimo (LlamaIndex + hnswlib)`
- Branch (implementação): `feat/01-rag-libs`
- Commit (implementação): `feat(rag): PR 01 — RAG local mínimo (LlamaIndex + hnswlib)`

## Checklist (requerido)
- [x] Objetivo e Escopo claros e limitados
- [x] Arquivos afetados listados
- [x] Pseudodiff pequeno e representativo
- [x] Critérios de aceitação e testes manuais
- [x] Mensagem e branch sugeridos

## Notas
- Este PR não altera defaults globais nem lógica existente; é módulo opt-in.
- Caso precisar de `faiss-cpu` ou `langchain` no futuro, submeter novo Plan PR (ex.: PR 02 ou maior) referenciando este.

