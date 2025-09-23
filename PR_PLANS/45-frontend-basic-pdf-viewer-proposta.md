# PR 45 — Frontend - Visualizador Básico de PDF (frontend-basic-pdf-viewer)

- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: Gemini
- Observações: Este PR depende do PR 44 (Backend - Servir Conteúdo PDF para Visualização).

## Objetivo

Implementar um componente React básico no frontend para renderizar documentos PDF, utilizando o endpoint de backend criado no PR 44 para buscar o conteúdo do arquivo.

## Escopo

- Criação de um novo componente `PdfViewer` em `src/spa/src/components/`.
- Integração do `PdfViewer` no `PdfTrainingWizard` para exibir o PDF do documento selecionado.
- Utilização de uma biblioteca de renderização de PDF para React (ex: `react-pdf`).

## Arquivos afetados

- `src/spa/src/components/PdfViewer.tsx` (novo arquivo)
- `src/spa/src/pages/PdfTrainingWizard.tsx` (integração do componente)
- `src/spa/src/api/pdfTraining.ts` (adicionar função para buscar o PDF)

## Critérios de aceitação

- O componente `PdfViewer` deve ser capaz de carregar e exibir um documento PDF válido.
- Ao selecionar um documento na `DocumentTable`, o `PdfViewer` deve exibir o PDF correspondente.
- O visualizador deve exibir pelo menos a primeira página do PDF.
- Erros de carregamento do PDF devem ser tratados e exibidos na UI.

## Testes manuais

- Fazer upload de um PDF via API.
- Navegar para a página do `PdfTrainingWizard`.
- Selecionar o documento carregado na `DocumentTable`.
- Verificar se o PDF é exibido corretamente no `PdfViewer`.
- Tentar selecionar um documento que não tenha um PDF válido associado e verificar a mensagem de erro.

## Riscos e mitigação

- **Risco:** Complexidade da biblioteca de PDF. **Mitigação:** Escolher uma biblioteca madura e bem documentada (ex: `react-pdf`). Começar com funcionalidades básicas e adicionar complexidade iterativamente.
- **Risco:** Performance de renderização para PDFs grandes. **Mitigação:** Implementar carregamento sob demanda de páginas (lazy loading) se a biblioteca suportar. Monitorar performance e otimizar conforme necessário.

## Notas adicionais

Este PR foca apenas na renderização básica do PDF. A sobreposição de entidades e a interatividade serão abordadas em PRs subsequentes.