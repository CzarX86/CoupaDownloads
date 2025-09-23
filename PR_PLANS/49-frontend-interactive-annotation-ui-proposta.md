# PR 49 — Frontend - UI de Anotação Interativa (frontend-interactive-annotation-ui)

- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: Gemini
- Observações: Este PR é o coração da experiência de anotação interativa. Depende do PR 47 (Frontend - Exibir Entidades Pré-processadas no PDF) e do PR 48 (Backend - Endpoints de Anotação Interativa).

## Objetivo

Implementar a interface de usuário no frontend que permita aos usuários interagir diretamente com o PDF renderizado para criar, editar e excluir anotações, enviando essas alterações de forma granular para o backend.

## Escopo

- Adicionar funcionalidade de seleção de texto no `PdfViewer` para criar novas anotações.
- Implementar um formulário ou modal para editar os detalhes de uma anotação (tipo, valor, notas).
- Adicionar botões ou ações para excluir anotações.
- Integrar com os novos endpoints de anotação interativa do backend (PR 48).
- Atualizar a UI em tempo real para refletir as mudanças nas anotações.

## Arquivos afetados

- `src/spa/src/components/PdfViewer.tsx` (modificação para interatividade)
- `src/spa/src/components/AnnotationForm.tsx` (novo componente para formulário/modal de anotação)
- `src/spa/src/api/pdfTraining.ts` (adicionar funções para CRUD de anotações)
- `src/spa/src/pages/PdfTrainingWizard.tsx` (integração do fluxo de anotação)

## Critérios de aceitação

- O usuário deve ser capaz de selecionar um trecho de texto no PDF e criar uma nova anotação a partir dele.
- As anotações existentes devem ser clicáveis/editáveis, abrindo um formulário para modificação.
- Deve haver uma opção clara para excluir uma anotação.
- Todas as operações (criação, edição, exclusão) devem ser persistidas no backend via os novos endpoints de API.
- A UI deve refletir imediatamente as mudanças nas anotações após as operações.

## Testes manuais

- Fazer upload de um PDF e acionar sua análise.
- Navegar para a página do `PdfTrainingWizard` e selecionar o documento.
- Selecionar um trecho de texto no PDF e criar uma nova anotação, preenchendo o formulário.
- Editar uma anotação existente, alterando seu tipo ou valor.
- Excluir uma anotação.
- Verificar o console do navegador e as ferramentas de rede para garantir que as chamadas de API estão sendo feitas corretamente e que o backend está respondendo conforme o esperado.
- Recarregar a página para verificar se as anotações persistiram.

## Riscos e mitigação

- **Risco:** Complexidade da lógica de seleção de texto e mapeamento para coordenadas. **Mitigação:** Utilizar bibliotecas de seleção de texto se disponíveis ou desenvolver uma solução customizada robusta. Testar exaustivamente em diferentes navegadores e PDFs.
- **Risco:** Sincronização de estado entre o PDF, as anotações e o backend. **Mitigação:** Utilizar `react-query` para gerenciar o estado do lado do cliente e garantir a invalidação e re-busca de dados após cada operação de anotação.

## Notas adicionais

Este PR transforma o visualizador de PDF em uma ferramenta de anotação completa. A experiência do usuário será fundamental para o sucesso desta funcionalidade.