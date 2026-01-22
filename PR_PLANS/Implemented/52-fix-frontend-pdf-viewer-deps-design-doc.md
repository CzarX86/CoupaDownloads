# Arquitetura 52 — Correção das dependências do PdfViewer (frontend-pdf-viewer-deps-fix)

- Status: draft
- Data: 2025-09-24
- Responsáveis: ChatGPT (desenvolvimento)
- Observações: Complementa a Proposta PR 52

## Resumo executivo

O PR 45 introduziu o componente `PdfViewer`, que depende da biblioteca `react-pdf`. Contudo, as dependências `react-pdf` e `pdfjs-dist` não foram adicionadas ao `package.json`, resultando em falha de build. Este design descreve os passos para alinhar a configuração do SPA com o código existente, garantindo builds reprodutíveis.

## Objetivos e não objetivos

- **Objetivos:**
  - Declarar explicitamente as dependências `react-pdf` e `pdfjs-dist` no SPA.
  - Regenerar o lockfile de forma determinística para refletir as novas bibliotecas.
  - Validar que o build e o lint permanecem funcionais.
- **Não objetivos:**
  - Modificar o comportamento do `PdfViewer` além da resolução de dependências.
  - Alterar o pipeline de CI/CD.
  - Introduzir testes automatizados adicionais.

## Estado atual

- O `PdfViewer` importa `react-pdf`, mas a dependência não está presente em `package.json`.
- Builds e lints falham ao resolver o módulo ausente.
- Usuários precisam instalar dependências manualmente, gerando inconsistência entre ambientes.

## Visão proposta

### Componentes e responsabilidades

- `package.json`: declara dependências runtime do SPA.
- `package-lock.json`: garante reprodutibilidade das versões.

### Fluxos

1. Adicionar `react-pdf` (v6+) e `pdfjs-dist` (versão compatível) à seção `dependencies`.
2. Executar `npm install` para atualizar o `package-lock.json`.

### Dados e contratos

- Nenhuma alteração de API; apenas alinhamento de dependências.

## Plano de implementação

1. Atualizar `package.json` com as novas dependências.
2. Regenerar `package-lock.json` com `npm install`.
3. Executar `npm run lint` e `npm run build` para validar o SPA.
4. Atualizar documentação interna, se necessário.

### Feature flags / rollback

- Não há feature flags. Em caso de problemas, reverter o commit que altera `package.json` e `package-lock.json`.

## Impactos

- **Performance:** A inclusão de `react-pdf` aumenta o tamanho do bundle, mas é necessária para o funcionamento do componente; sem impacto adicional além do já previsto no PR 45.
- **Segurança:** Dependências amplamente utilizadas; monitorar CVEs através do GitHub Advisory.
- **Operações / suporte:** Reduz suporte manual para instalação local.

## Testes e evidências

- `npm run lint`
- `npm run build`
- Smoke test manual do `PdfViewer` carregando um PDF real.

## Decisões, trade-offs e alternativas consideradas

- Considerou-se remover temporariamente o `PdfViewer`, mas isso quebraria o objetivo do PR 45. Optou-se por alinhar dependências.
- Não se adotará CDN externo para o worker do PDF; manteremos pacotes npm oficiais.

## Pendências e próximos passos

- Avaliar, em PR futuro, testes automatizados específicos para o `PdfViewer`.
