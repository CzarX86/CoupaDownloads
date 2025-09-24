# PR 52 — Correção das dependências do PdfViewer (frontend-pdf-viewer-deps-fix)

- Status: draft
- Implementação: pending
- Data: 2025-09-24
- Responsáveis: ChatGPT (desenvolvimento)
- Observações: Correção urgente para garantir que o build do SPA funcione após o PR 45

## Objetivo

Garantir que o componente `PdfViewer`, introduzido no PR 45, possua todas as dependências de runtime declaradas para que o build do SPA conclua sem erros.

## Escopo

- Declarar `react-pdf` e `pdfjs-dist` como dependências do projeto `src/spa`.
- Atualizar o `package-lock.json` para refletir a instalação dessas bibliotecas e seus transitivos.
- Documentar os passos mínimos de verificação do build.

## Arquivos afetados

- `src/spa/package.json`
- `src/spa/package-lock.json`

## Critérios de aceitação

1. O comando `npm install` no diretório `src/spa` completa sem erros e inclui `react-pdf` e `pdfjs-dist` no lockfile.
2. O build do SPA (`npm run build`) reconhece o módulo `react-pdf` sem falhas de importação.
3. O `PdfViewer` continua renderizando PDFs utilizando o endpoint `/documents/{document_id}/content`.

## Testes manuais

1. Executar `npm install` em `src/spa` e confirmar que as dependências são resolvidas.
2. Rodar `npm run build` e verificar ausência de erros.
3. Carregar um PDF via UI e checar renderização no `PdfViewer`.

## Riscos e mitigação

- **Risco:** Introdução de dependências incompatíveis com o ambiente atual do SPA.
  - **Mitigação:** Verificar as versões recomendadas pela documentação oficial e validar o build localmente.
- **Risco:** Aumento do bundle size com as novas bibliotecas.
  - **Mitigação:** Monitorar o tamanho gerado pelo `npm run build` e avaliar tree-shaking se necessário.

## Notas adicionais

- A correção depende da disponibilidade de acesso ao registro npm público para baixar os pacotes.
