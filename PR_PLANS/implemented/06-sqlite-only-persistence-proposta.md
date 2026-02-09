# Proposta de Mudança: Persistência Somente em SQLite e Exportação Final para Cópia do CSV

## 1. Identificação
- **Número da Proposta**: 06
- **Título**: Persistência Somente em SQLite e Exportação Final para Cópia do CSV
- **Data de Criação**: 9 de fevereiro de 2026
- **Autor**: Codex (a pedido do usuário)
- **Status**: Aprovado (solicitado pelo usuário em 9 de fevereiro de 2026)
- **Dependências**: Nenhuma

## 2. Contexto e Problema
Hoje o fluxo pode atualizar o CSV durante a execução (via ExcelProcessor) e, ao final, regravar o arquivo de input. Isso torna o input mutável e conflita com o objetivo de usar o CSV apenas como fonte de leitura, mantendo os resultados somente em SQLite até o fim.

## 3. Objetivo
Garantir que:
- Durante a execução, **apenas** SQLite seja usado como persistência.
- O arquivo de input **não seja modificado**.
- Ao final do processamento, seja gerada **uma cópia** do CSV de input contendo os dados processados.

## 4. Escopo
### In Scope
- Desabilitar atualizações incrementais no CSV durante o run.
- Persistência exclusiva em SQLite durante a execução.
- Exportação final para **cópia** do CSV (com timestamp).
- Novas chaves de configuração para esse comportamento.

### Out of Scope
- Alterar formato de dados ou schema.
- Mudanças em Selenium/Playwright.
- Novas telas/UI.

## 5. Critérios de Aceitação
- O CSV de input permanece intacto (sem alterações).
- Um novo arquivo de saída é gerado ao final com os resultados.
- Logs indicam que a exportação final ocorreu para a cópia.
- Sem criação de `*_progress.csv` durante execução.

## 6. Riscos e Mitigações
- **Risco**: Falha na inicialização do SQLite pode resultar em ausência de persistência.
  - **Mitigação**: Log explícito e checagens na inicialização do handler.

## 7. Plano de Implementação (Alto Nível)
1. Adicionar flag para desabilitar atualizações legacy via ExcelProcessor.
2. Manter persistência apenas em SQLite durante o run.
3. Exportar resultados para cópia do CSV ao final.
4. Atualizar logs e configurações.

## 8. Próximos Passos
- Elaborar design doc.
- Implementar mudanças e gerar relatório.
