# PR 51 — Frontend - Integrar Feedback do Modelo (frontend-integrate-model-feedback)

- Status: draft
- Implementação: pending
- Data: 2025-09-23
- Responsáveis: Gemini
- Observações: Este PR fecha o ciclo de feedback humano-no-loop no frontend. Depende do PR 49 (Frontend - UI de Anotação Interativa) e do PR 50 (Backend - Gatilho de Feedback Imediato do Modelo).

## Objetivo

Integrar a funcionalidade de acionamento do feedback imediato do modelo no frontend, permitindo que o usuário, após realizar anotações, possa enviar essas informações para o backend para fine-tuning do modelo, com o objetivo de melhorar as predições futuras.

## Escopo

- Adicionar um botão ou ação na UI (ex: no `AnnotationForm` ou no `PdfTrainingWizard`) para "Enviar Feedback" ou "Treinar Modelo com Feedback".
- Implementar a lógica no frontend para chamar o novo endpoint de feedback do modelo no backend (PR 50).
- Exibir feedback visual ao usuário sobre o status do processo de fine-tuning (ex: mensagem de sucesso, indicador de carregamento).

## Arquivos afetados

- `src/spa/src/components/AnnotationForm.tsx` (modificação para adicionar botão/ação)
- `src/spa/src/pages/PdfTrainingWizard.tsx` (modificação para adicionar botão/ação ou gerenciar o fluxo)
- `src/spa/src/api/pdfTraining.ts` (adicionar função para chamar o endpoint de feedback)

## Critérios de aceitação

- O usuário deve ser capaz de acionar o processo de feedback do modelo através de um elemento da UI.
- A chamada para o endpoint de feedback do modelo no backend deve ser feita corretamente com o `document_id` e as anotações atualizadas.
- A UI deve indicar que o feedback foi enviado e que o processo de fine-tuning foi iniciado (ex: mensagem de sucesso, job ID).
- O processo de feedback não deve bloquear a UI.

## Testes manuais

- Fazer upload de um PDF, acionar análise e corrigir/adicionar anotações via UI (após PR 49).
- Clicar no botão "Enviar Feedback" ou similar.
- Verificar o console do navegador e as ferramentas de rede para garantir que a chamada de API para o endpoint de feedback foi feita.
- Verificar a UI para a mensagem de sucesso ou status do job.
- Fazer upload de um novo PDF similar e verificar se as predições do modelo mostram melhoria de precisão (teste qualitativo).

## Riscos e mitigação

- **Risco:** Confusão do usuário sobre o que o botão de feedback faz. **Mitigação:** Fornecer texto claro e tooltips explicativos na UI. Explicar o benefício do feedback.
- **Risco:** Feedback visual inadequado para o processo assíncrono. **Mitigação:** Utilizar indicadores de carregamento e mensagens de sucesso/erro claras, possivelmente com links para o status do job.

## Notas adicionais

Este PR completa a funcionalidade de feedback humano-no-loop, permitindo que o sistema aprenda continuamente com as interações do usuário. A experiência do usuário deve ser intuitiva e informativa.