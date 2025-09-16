# PR 02 — CLI interativo para RAG (embeddinggemma_feasibility)

## Objetivo
Adicionar um menu interativo (linha de comando) no subprojeto `embeddinggemma_feasibility` para facilitar as operações de RAG sem precisar lembrar parâmetros:
- Build do índice (selecionar pasta‐fonte, diretório de persistência, modelo, chunk size/overlap).
- Query do índice (pergunta, top-k, return-k, com/sem reranker).
- Visualizar configurações atuais (paths, modelo default, etc.).

Sem alterações de arquitetura/global; uso apenas de stdlib (sem novas dependências).

## Escopo
- Novo módulo `embeddinggemma_feasibility/interactive_cli.py` com menu textual:
  - Opção 1: Build index (usa funções de `embeddinggemma_feasibility.rag.*`).
  - Opção 2: Query index (usa funções de `rag.index`/`rag.retrieve`/`rag.rerank`).
  - Opção 3: Mostrar configurações (RAGConfig, diretórios, defaults).
  - Opção 0: Sair.
- Entradas com valores default sensatos (por exemplo, `data/sample_documents` e `data/rag_index`).
- Mensagens claras de sucesso/erro; validação de caminhos.
- Sem entry point no `pyproject.toml` neste PR (chamada via `python -m embeddinggemma_feasibility.interactive_cli`).
- Atualizar documentação do subprojeto (`docs/RAG_MINIMAL.md`) com seção “Interactive mode”.

## Contexto para usuários (explicações rápidas)
- O que é RAG? Um fluxo que indexa seus documentos (gera "vetores" que representam o texto) e depois busca trechos relevantes para uma pergunta.
- Quando usar “Build index”? Quando você adicionou/alterou documentos e quer atualizar a base. É um passo pesado, mas feito esporadicamente.
- Quando usar “Query”? Para fazer perguntas e recuperar trechos relevantes. É rápido quando o índice já existe.
- O que é “reranker”? Um refinamento da ordem dos resultados usando um modelo pequeno. Melhora a qualidade, mas pode baixar um modelo na primeira vez e ser mais lento. Em ambientes offline, desative.
- Onde ficam os dados? Por padrão em `embeddinggemma_feasibility/data/rag_index`. Seus documentos de exemplo estão em `embeddinggemma_feasibility/data/sample_documents`.

## Decisões e trade-offs (em linguagem simples)
- Modelo de embeddings (default: `intfloat/multilingual-e5-small`): pequeno e bom para PT/EN; consome pouca memória (bom para MacBook Air M3 8GB).
- Splitter por caracteres (não por tokens): mais simples e não depende de bibliotecas extras; funciona bem para POC.
- HNSW (hnswlib) como índice: rápido e offline, sem precisar de banco de dados externo.
- Reranker opcional: qualidade melhor vs. tempo extra. Se prioriza velocidade/offline, deixe desativado.

## Fluxo típico (com Poetry)
1) Ative o ambiente: `poetry env use 3.12 && poetry install --with ml`
2) Garanta as libs do subprojeto: `poetry run pip install -r embeddinggemma_feasibility/requirements.txt`
3) Rode o menu: `poetry run python -m embeddinggemma_feasibility.interactive_cli`
4) Opção 1 (Build): aceite os defaults (source = `data/sample_documents`, persist = `data/rag_index`) ou personalize.
5) Opção 2 (Query): digite sua pergunta; ative `reranker` se quiser melhores resultados.
6) Opção 3 (Config): veja os caminhos e parâmetros atuais para entender o que o sistema está usando.

## Erros comuns e como decidir
- “Torch/transformers não encontrado” ou erro de instalação: falta do grupo `ml` no Poetry ou conflitos de versão. Refaça “Passo 1/2” do fluxo típico.
- “Baixando modelo do reranker” em ambiente sem internet: desative `reranker` (responda “não” quando perguntado) ou rode online uma vez para cachear.
- “Nenhum documento encontrado”: confirme o caminho de `source` e a extensão dos arquivos (suportados: `.txt`, `.md`, `.pdf`).
- “Memória alta no build”: reduza `max_chars` (tamanho dos chunks) e/ou use menos documentos por vez.

## Privacidade e desempenho
- Tudo roda localmente; não enviamos documentos para serviços externos por padrão.
- O reranker pode baixar um modelo público da internet na primeira execução; se não quiser, mantenha-o desativado.

## UX do menu (para leigos)
- Sempre mostramos valores padrão entre colchetes: basta pressionar Enter para aceitar.
- Mensagens de sucesso/erro explicarão o próximo passo (“onde encontrar o índice”, “como ajustar parâmetros”).
- Opção “Voltar ao menu” após cada ação para facilitar novas tentativas.

## Arquivos afetados
- Novo: `embeddinggemma_feasibility/interactive_cli.py`
- Alterado: `embeddinggemma_feasibility/docs/RAG_MINIMAL.md` (instruções do modo interativo)

## Pseudodiff (representativo)
```
+ embeddinggemma_feasibility/interactive_cli.py
+   def main():
+       while True:
+           print("1) Build index")
+           print("2) Query index")
+           print("3) Show config")
+           print("0) Exit")
+           choice = input("> ").strip()
+           if choice == "1":
+               # perguntar source, persist, modelo, max_chars, overlap
+               # chamar load_documents(...) e build_index(...)
+           elif choice == "2":
+               # perguntar index dir, query, top_k, return_k, reranker
+               # chamar load_index(...) e query_index(...), opcional rerank
+           elif choice == "3":
+               # imprimir RAGConfig() atual
+           elif choice == "0":
+               break
+           else:
+               print("Opção inválida")

~ embeddinggemma_feasibility/docs/RAG_MINIMAL.md
+ ## Interactive mode
+ poetry run python -m embeddinggemma_feasibility.interactive_cli
```

## Critérios de aceitação
- Executando `poetry run python -m embeddinggemma_feasibility.interactive_cli` exibe o menu com as 4 opções e retorna ao menu após cada ação.
- Build index com defaults usando a pasta existente `embeddinggemma_feasibility/data/sample_documents` persiste em `embeddinggemma_feasibility/data/rag_index` sem erros.
- Query index permite informar uma pergunta e retorna JSON com lista reduzida (`return_k`) e metadados (source_path, chunk_idx).
- Sem novas dependências; funciona com o ambiente configurado no PR 11 (Poetry 3.12.x, grupo `ml`).
- Documentação do `RAG_MINIMAL.md` inclui instruções para o modo interativo.

## Testes manuais
1) Preparar ambiente (Poetry):
   - `poetry env use 3.12 && poetry install --with ml`
   - `poetry run pip install -r embeddinggemma_feasibility/requirements.txt`
2) CLI interativo:
   - `poetry run python -m embeddinggemma_feasibility.interactive_cli`
   - Opção 1: aceitar defaults (source: `embeddinggemma_feasibility/data/sample_documents`, persist: `embeddinggemma_feasibility/data/rag_index`). Ver "build ok".
   - Opção 2: digitar uma pergunta (ex.: "termos de entrega"), ver JSON de resultados (com/sem `reranker`).
3) Opção 3: ver configurações atuais; confirmar diretórios.

## Mensagem e branch sugeridos
- Branch (plan): `plan/02-interactive-cli`
- Commit (plan): `docs(pr-plan): PR 02 — CLI interativo para RAG`
- Branch (implementação): `feat/02-interactive-cli`
- Commit (implementação): `feat(rag-cli): PR 02 — menu interativo para RAG`

## Checklist (requerido)
- [x] Objetivo e Escopo claros e limitados
- [x] Arquivos afetados listados
- [x] Pseudodiff pequeno e representativo
- [x] Critérios de aceitação e testes manuais
- [x] Mensagem e branch sugeridos
