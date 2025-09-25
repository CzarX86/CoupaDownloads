# PR 48 — Backend - Endpoints de Anotação Interativa (backend-interactive-annotation-endpoints)

- Status: implemented
- Implementação: concluída
- Data: 2025-09-23
- Responsáveis: Gemini
- Observações: Este PR é crucial para permitir a interação do usuário com as anotações. Depende do PR 46 (Backend - Servir Entidades Pré-processadas).

## Estado da revisão (2025-09-25)

- [x] Implementado no código-base. Os endpoints `POST /documents/{document_id}/annotations`, `PUT /annotations/{annotation_id}` e `DELETE /annotations/{annotation_id}` foram adicionados em `src/server/pdf_training_app/api.py`, com serviços e repositório cobrindo CRUD completo e esquemas Pydantic atualizados.

## Objetivo

Implementar endpoints de API no backend que permitam ao frontend criar, atualizar e excluir anotações de forma granular e interativa, substituindo o fluxo atual de ingestão de exportações em lote.

## Escopo

- Criação de novos endpoints FastAPI para operações CRUD (Create, Read, Update, Delete) em anotações individuais.
- Modificação da lógica de serviço para interagir diretamente com o modelo `Annotation` no banco de dados.
- Adaptação do modelo `Annotation` (se necessário) para suportar a estrutura de dados das anotações interativas (ex: tipo de entidade, valor, localização, status).

## Arquivos afetados

- `src/server/pdf_training_app/api.py` (adicionar novos endpoints)
- `src/server/pdf_training_app/services.py` (adicionar/modificar funções de serviço para CRUD de anotações)
- `src/server/db/models.py` (potencialmente modificar o modelo `Annotation`)
- `src/server/pdf_training_app/models.py` (adicionar modelos Pydantic para requisição/resposta de anotações)

## Critérios de aceitação

- Deve ser possível criar uma nova anotação para um documento específico via API.
- Deve ser possível atualizar os detalhes de uma anotação existente (ex: tipo, valor, status) via API.
- Deve ser possível excluir uma anotação existente via API.
- As operações devem ser persistidas corretamente no banco de dados.
- Erros (ex: anotação não encontrada, dados inválidos) devem ser tratados com respostas HTTP apropriadas.

## Testes manuais

- Fazer upload de um PDF e acionar sua análise.
- Chamar o endpoint de criação de anotação para adicionar uma nova anotação a um documento.
- Chamar o endpoint de atualização para modificar a anotação criada.
- Chamar o endpoint de exclusão para remover a anotação.
- Verificar o banco de dados para confirmar a persistência das mudanças.
- Testar casos de erro (ex: IDs inválidos).

## Riscos e mitigação

- **Risco:** Conflitos de concorrência ao atualizar a mesma anotação. **Mitigação:** Implementar controle de concorrência otimista (ex: versionamento de anotações) se o problema surgir. Para o escopo inicial, aceitar o último a gravar.
- **Risco:** Complexidade na estrutura de dados da anotação. **Mitigação:** Começar com uma estrutura simples (tipo, valor, localização) e expandir conforme a necessidade da UI. Pode ser necessário um ADR para definir a estrutura canônica da anotação.

## Notas adicionais

Este PR substitui o mecanismo de `ingest_annotation_export` para anotações interativas. O `ingest_annotation_export` pode ser mantido para cenários de importação em lote de ferramentas externas, mas o foco será nos novos endpoints granulares.