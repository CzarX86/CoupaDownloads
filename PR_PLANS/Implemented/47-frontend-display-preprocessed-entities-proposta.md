# PR 47 — Frontend - Exibir Entidades Pré-processadas no PDF (frontend-display-preprocessed-entities)

- Status: implemented
- Implementação: concluída
- Data: 2025-09-23
- Responsáveis: Gemini
- Observações: Este PR depende do PR 45 (Frontend - Visualizador Básico de PDF) e do PR 46 (Backend - Servir Entidades Pré-processadas).

## Estado da revisão (2025-09-25)

- [x] Implementado no código-base. O `PdfViewer` agora busca entidades via `fetchEntities` e renderiza overlays conforme previsto em `src/spa/src/components/PdfViewer.tsx`, com modelos e client atualizados em `src/spa/src/models.ts` e `src/spa/src/api/pdfTraining.ts`.

## Objetivo

Implementar a funcionalidade no frontend para buscar e exibir as entidades pré-processadas (predições) diretamente sobre o PDF renderizado, permitindo que o usuário visualize as extrações do modelo.

## Escopo

- Adicionar lógica no componente `PdfViewer` para buscar entidades do novo endpoint de backend (`/documents/{document_id}/entities`).
- Desenvolver uma camada de sobreposição (overlay) no `PdfViewer` para desenhar as entidades (ex: retângulos de destaque) sobre o texto do PDF.
- Exibir o tipo e o valor da entidade ao interagir com o destaque (ex: tooltip ao passar o mouse).

## Arquivos afetados

- `src/spa/src/components/PdfViewer.tsx` (modificação para buscar e exibir entidades)
- `src/spa/src/api/pdfTraining.ts` (adicionar função para buscar entidades)
- `src/spa/src/models.ts` (novo arquivo ou modificação para definir o modelo de `Entity` no frontend)

## Critérios de aceitação

- Ao carregar um PDF no `PdfViewer`, as entidades pré-processadas devem ser buscadas e exibidas como destaques visuais sobre o PDF.
- Os destaques devem corresponder visualmente à localização das entidades no PDF (se a informação de localização estiver disponível).
- Ao passar o mouse sobre um destaque de entidade, um tooltip ou popover deve exibir o tipo e o valor da entidade.
- Erros na busca de entidades devem ser tratados e não devem impedir a renderização do PDF.

## Testes manuais

- Fazer upload de um PDF e acionar sua análise.
- Navegar para a página do `PdfTrainingWizard` e selecionar o documento.
- Verificar se o PDF é exibido e se as entidades são destacadas corretamente.
- Passar o mouse sobre as entidades destacadas e verificar se os tooltips exibem as informações corretas.
- Verificar o console do navegador para quaisquer erros relacionados à busca ou renderização de entidades.

## Riscos e mitigação

- **Risco:** Dificuldade em mapear coordenadas de entidades do backend para a renderização do PDF no frontend. **Mitigação:** Começar com uma abordagem mais simples (ex: destacar texto se as coordenadas forem difíceis de obter). Pesquisar e testar a compatibilidade da biblioteca `react-pdf` com sobreposições precisas. Pode ser necessário um ADR para definir um padrão de coordenadas.
- **Risco:** Performance da renderização de muitos destaques. **Mitigação:** Otimizar o componente de overlay para renderização eficiente. Considerar virtualização ou renderização sob demanda para PDFs com muitas entidades.

## Notas adicionais

Este PR estabelece a base visual para a interação com as entidades. A capacidade de editar, adicionar ou remover entidades será implementada em PRs futuros.