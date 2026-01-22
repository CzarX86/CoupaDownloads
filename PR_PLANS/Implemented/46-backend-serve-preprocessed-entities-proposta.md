# PR 46 — Backend - Servir Entidades Pré-processadas para Visualização (backend-serve-preprocessed-entities)

- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: Gemini
- Observações: Este PR depende do PR 44 (Backend - Servir Conteúdo PDF para Visualização) e é um pré-requisito para o PR 47 (Frontend - Exibir Entidades Pré-processadas).

## Objetivo

Implementar um endpoint na API para permitir que o frontend acesse as entidades pré-processadas (predições) de um documento PDF, viabilizando a sobreposição dessas entidades no visualizador de PDF no frontend.

## Escopo

Criação de um novo endpoint GET `/documents/{document_id}/entities` na API FastAPI que retorna uma estrutura de dados JSON contendo as entidades extraídas e suas localizações (se disponíveis).

## Arquivos afetados

- `src/server/pdf_training_app/api.py` (adicionar o novo endpoint)
- `src/server/pdf_training_app/services.py` (adicionar a lógica para buscar e formatar as entidades)
- `embeddinggemma_feasibility/pdf_information_extractor.py` (potencialmente adaptar para retornar informações de localização mais detalhadas)
- `src/server/pdf_training_app/models.py` (adicionar um modelo de resposta para as entidades)

## Critérios de aceitação

- O endpoint `/documents/{document_id}/entities` deve retornar uma lista de entidades para o `document_id` fornecido.
- Cada entidade deve incluir o tipo (ex: "PO Number", "Amount"), o valor e, idealmente, informações de localização (ex: coordenadas de bounding box ou offsets de texto) dentro do PDF.
- Se o `document_id` não existir ou as entidades não puderem ser processadas, o endpoint deve retornar um erro 404 ou 500, respectivamente.

## Testes manuais

- Fazer upload de um PDF via API existente.
- Acionar a análise do documento (`POST /documents/{document_id}/analyze`).
- Chamar o novo endpoint `/documents/{document_id}/entities` com o ID do documento e verificar se uma estrutura JSON com entidades é retornada.
- Verificar a presença de tipos de entidades esperados (ex: "PO Number", "Amount").
- Chamar o endpoint com um `document_id` inválido e verificar se um erro 404 é retornado.

## Riscos e mitigação

- **Risco:** Dificuldade em obter informações de localização precisas das entidades. **Mitigação:** Inicialmente, retornar apenas o valor e o tipo da entidade. Se a biblioteca de extração de PDF (`pdfplumber`) puder fornecer coordenadas, integrá-las. Caso contrário, explorar bibliotecas adicionais ou métodos de inferência de localização.
- **Risco:** Performance da extração de entidades em tempo real. **Mitigação:** O endpoint deve retornar entidades *pré-processadas* (geradas durante a análise). Se a análise ainda não tiver ocorrido, o endpoint pode acioná-la ou retornar um status indicando que a análise está pendente.

## Notas adicionais

Este PR é crucial para a funcionalidade de sobreposição de entidades no visualizador de PDF do frontend. A precisão das informações de localização das entidades impactará diretamente a qualidade da experiência do usuário.