# PR 01 — Backend - Servir Conteúdo PDF para Visualização (backend-serve-pdf-content)

- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: Gemini
- Observações: Este PR é o primeiro passo para habilitar a visualização interativa de PDFs no frontend.

## Objetivo

Implementar um endpoint na API para permitir que o frontend acesse o conteúdo bruto de um documento PDF armazenado, viabilizando a renderização visual do PDF na interface do usuário.

## Escopo

Criação de um novo endpoint GET `/documents/{document_id}/content` na API FastAPI que retorna o arquivo PDF.

## Arquivos afetados

- `src/server/pdf_training_app/api.py` (adicionar o novo endpoint)
- `src/server/pdf_training_app/services.py` (adicionar a lógica para buscar o caminho do arquivo PDF)

## Critérios de aceitação

- O endpoint `/documents/{document_id}/content` deve retornar o conteúdo do arquivo PDF correspondente ao `document_id` fornecido.
- O `media_type` da resposta deve ser `application/pdf`.
- Se o `document_id` não existir ou o arquivo PDF não for encontrado, o endpoint deve retornar um erro 404.

## Testes manuais

- Fazer upload de um PDF via API existente.
- Chamar o novo endpoint `/documents/{document_id}/content` com o ID do documento carregado e verificar se o PDF é baixado corretamente.
- Chamar o endpoint com um `document_id` inválido e verificar se um erro 404 é retornado.

## Riscos e mitigação

- **Risco:** Exposição de arquivos sensíveis. **Mitigação:** O endpoint só deve servir PDFs que foram previamente carregados e associados a um `document_id` válido no banco de dados. A autenticação/autorização (se implementada) deve ser aplicada.
- **Risco:** Performance ao servir arquivos grandes. **Mitigação:** FastAPI `FileResponse` é otimizado para servir arquivos. Monitorar performance e considerar streaming se necessário.

## Notas adicionais

Este PR é um pré-requisito para a implementação do visualizador de PDF no frontend.