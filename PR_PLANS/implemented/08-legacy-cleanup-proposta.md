# Proposta de Mudança: Limpeza de Legado com Backup de Referência

## 1. Identificação
- **Número da Proposta**: 08
- **Título**: Limpeza de Legado com Backup de Referência
- **Data de Criação**: 4 de março de 2026
- **Autor**: Codex (a pedido do usuário)
- **Status**: Aprovado (execução solicitada pelo usuário)
- **Dependências**: Nenhuma

## 2. Contexto e Problema
O código acumulou caminhos legados e configurações duplicadas, com impacto direto em manutenção:
- `src/lib/config.py` coexistia com `src/config/app_config.py`.
- Havia rotas legadas de execução no `WorkerManager`.
- Existia duplicação de composição de mensagens para CSV.
- Parte da persistência CSV mantinha fluxo legado junto com SQLite.

## 3. Objetivo
- Consolidar configuração em `src/config/app_config.py`.
- Remover dependência de runtime em módulos legados.
- Preservar referência histórica via backup explícito (branch/tag + arquivo em `docs/legacy/`).
- Simplificar persistência e reduzir duplicação de lógica.

## 4. Escopo
### In Scope
- Migração de imports de configuração para `app_config`.
- Arquivamento de `src/lib/config.py` e `src/config/defaults.py` em `docs/legacy/`.
- Remoção de rotas legadas (`process_parallel_legacy`, `_legacy_rename_folder_with_status`).
- Centralização de mensagem CSV em utilitário compartilhado.
- Simplificação de persistência para fluxo SQLite único.

### Out of Scope
- Mudanças de contrato público da CLI.
- Alterações de schema de dados.
- Reescrita completa de arquitetura de workers.

## 5. Critérios de Aceitação
- Não há imports de `src.lib.config` no código de runtime.
- Arquivos legados removidos do runtime e arquivados em `docs/legacy/`.
- `WorkerManager` sem funções legadas de execução/rename fallback.
- Mensagem de CSV reutilizada via utilitário compartilhado.
- Testes relevantes executam sem regressão crítica conhecida.

## 6. Riscos e Mitigações
- **Risco**: regressão por mudança de fonte de configuração.
  - **Mitigação**: manter compatibilidade via propriedades uppercase em `AppConfig`.
- **Risco**: diferença de comportamento na finalização de pastas.
  - **Mitigação**: manter `finalize_folder` como caminho principal e registrar falha sem rename legado.

## 7. Plano de Implementação (Alto Nível)
1. Criar branch/tag de backup.
2. Migrar imports e compatibilidade de configuração.
3. Remover caminhos legados de execução.
4. Simplificar persistência CSV.
5. Arquivar arquivos legados e documentar.
6. Validar com testes/smoke checks.

## 8. Próximos Passos
- Finalizar design doc e relatório de implementação.
