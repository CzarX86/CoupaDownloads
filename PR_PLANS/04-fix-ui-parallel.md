# Proposta de Mudança: Correção da UI no Modo Paralelo

## 1. Identificação
- **Número da Proposta**: 04
- **Título**: Correção da UI no Modo Paralelo
- **Data de Criação**: 28 de janeiro de 2026
- **Autor**: GitHub Copilot
- **Status**: Em Revisão
- **Dependências**: Após Fase 3 da Proposta 03 (refatoração main.py).

## 2. Contexto e Problema
Após a refatoração da Fase 3 (Separação de UI), a UI funciona corretamente no modo sequencial: tempo global atualiza em tempo real, e outros valores (ETA, eficiência, progress, etc.) atualizam após cada PO processado.

No entanto, no modo paralelo (>1 worker), a UI não atualiza os valores dinâmicos. Os valores permanecem estáticos (ex.: ETA "⏳", eficiência "⏳", progress "0/0 POs") durante toda a execução.

Problema identificado: O callback `_parallel_progress_callback` não é chamado durante o processamento paralelo, impedindo a atualização da UI via `UIController.update_display()`.

## 3. Objetivo
Corrigir a atualização da UI no modo paralelo, garantindo que os valores sejam exibidos em tempo real, assim como no sequencial.

Benefícios:
- UI consistente entre modos sequencial e paralelo.
- Melhor experiência do usuário com feedback visual durante processamento paralelo.
- Validação completa da refatoração UI.

## 4. Escopo
- **In Scope**:
  - Investigar por que o callback não é chamado no `ProcessingSession` ou `WorkerManager`.
  - Corrigir a chamada do callback durante processamento paralelo.
  - Garantir que `UIController` receba updates e atualize o display Rich.
- **Out of Scope**:
  - Mudanças na lógica de processamento (deixar para Proposta 01/02).
  - Otimizações de performance do paralelo.

## 5. Critérios de Aceitação
- UI atualiza valores em tempo real no modo paralelo (tempo global a cada segundo, outros após progress).
- Callback `_parallel_progress_callback` é chamado corretamente.
- Funcionalidade idêntica ao sequencial.
- Sem regressões na UI ou processamento.

## 6. Riscos e Mitigações
- **Risco**: Alterações no processamento paralelo podem introduzir bugs.
  - **Mitigação**: Testes isolados no parallel, rollback se necessário.
- **Risco**: Overhead de callbacks frequentes.
  - **Mitigação**: Otimizar frequência de updates.

## 7. Plano de Implementação
### Investigação (1 dia)
- Adicionar logs no `ProcessingSession` para verificar se o callback é registrado e chamado.
- Verificar se `WorkerManager.process_parallel_with_session` passa o callback corretamente.
- Executar testes com prints para confirmar fluxo.

### Correção (1-2 dias)
- Se callback não registrado: Corrigir passagem do callback.
- Se registrado mas não chamado: Corrigir lógica no `ProcessingSession` para chamar em updates de progress.
- Testar com lote pequeno de POs.

### Validação (1 dia)
- Executar com >1 worker, verificar UI atualiza.
- Comparar com sequencial.
- Performance check (sem lag excessivo).

Total estimado: 3-4 dias.

## 8. Dependências
- Fase 3 da Proposta 03 aprovada.

## 9. Próximos Passos
- Aprovar proposta.
- Investigar e implementar correção.
- Gerar Relatório de Implementação.</content>
<parameter name="filePath">/Users/juliocezar/Dev/CoupaDownloads_Refactoring/PR_PLANS/04-fix-ui-parallel.md