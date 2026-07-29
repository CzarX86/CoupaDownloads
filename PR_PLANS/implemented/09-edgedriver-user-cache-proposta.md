# Proposta de Mudança: Persistência de EdgeDriver via Cache de Usuário

## 1. Identificação
- **Número da Proposta**: 09
- **Título**: Persistência de EdgeDriver via Cache de Usuário
- **Data de Criação**: 5 de março de 2026
- **Autor**: Codex (a pedido do usuário)
- **Status**: Aprovado (execução solicitada pelo usuário)
- **Dependências**: Nenhuma

## 2. Contexto e Problema
O runtime validava o EdgeDriver a cada execução, mas o download automático era armazenado em diretório temporário e removido ao final do processo. Como consequência, o mesmo driver voltava a ser baixado minutos depois, mesmo sem mudança de versão do navegador.

Além disso, o projeto mantinha `drivers/` dentro do repositório como caminho suportado para binários locais, misturando artefatos de runtime com arquivos versionados.

## 3. Objetivo
- Persistir o EdgeDriver automaticamente em cache estável por usuário.
- Reutilizar o binário em execuções subsequentes sem redownload desnecessário.
- Baixar nova versão apenas quando o Edge exigir outro driver ou quando o cache estiver inválido.
- Remover `drivers/` do repositório como mecanismo suportado.
- Simplificar o código com separação clara de responsabilidades.

## 4. Escopo
### In Scope
- Refatoração do gerenciamento de EdgeDriver para cache persistente por usuário.
- Remoção do suporte a `drivers/` no workspace.
- Coordenação segura para workers concorrentes via lock por versão.
- Atualização de configuração, documentação principal e testes unitários.
- Remoção do diretório `drivers/` do repositório.

### Out of Scope
- Mudanças de contrato da CLI.
- Alterações na lógica de processamento de POs.
- Reescrita completa do fluxo Selenium/Playwright.

## 5. Critérios de Aceitação
- Primeira execução baixa e publica o driver compatível no cache do usuário.
- Execuções subsequentes reutilizam o cache sem novo download quando a versão do Edge não muda.
- Mudança de versão do Edge provoca novo download e atualização do cache.
- `drivers/` deixa de ser mecanismo suportado e é removido do repositório.
- Workers concorrentes não duplicam download da mesma versão.
- Testes unitários cobrem ordem de resolução, invalidação e concorrência.

## 6. Riscos e Mitigações
- **Risco**: corrida entre workers ao popular o cache.
  - **Mitigação**: lock por `platform/version` com revalidação após espera.
- **Risco**: cache corrompido reaproveitado.
  - **Mitigação**: validação antes de usar e remoção seletiva da entrada inválida.
- **Risco**: documentação desatualizada após remoção de `drivers/`.
  - **Mitigação**: revisão de README, `src/README.md` e `AGENTS.md` na mesma entrega.

## 7. Plano de Implementação (Alto Nível)
1. Refatorar `driver_manager` em componentes menores com fachada compatível.
2. Introduzir cache persistente por usuário e lock por versão.
3. Remover código e documentação associados a `drivers/`.
4. Adicionar testes unitários para cache, invalidação e concorrência.
5. Validar com `pytest` focado no novo módulo.

## 8. Próximos Passos
- Finalizar design doc e relatório de implementação.
