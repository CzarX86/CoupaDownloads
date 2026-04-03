# Proposta de Mudança: SQLite em Diretório Persistente de Estado da Aplicação

## 1. Identificação
- **Número da Proposta**: 10
- **Título**: SQLite em Diretório Persistente de Estado da Aplicação
- **Data de Criação**: 5 de março de 2026
- **Autor**: Codex (a pedido do usuário)
- **Status**: Aprovado (execução solicitada pelo usuário)
- **Dependências**: 09-edgedriver-user-cache

## 2. Contexto e Problema
Após mover o EdgeDriver para cache persistente por usuário, surgiu a decisão de onde manter o SQLite de sessão. O banco não é um artefato recriável como o driver; ele representa estado da aplicação e não deve ser armazenado na mesma pasta de cache nem removido como arquivo temporário.

## 3. Objetivo
- Separar o SQLite do cache do EdgeDriver.
- Armazenar o banco em diretório persistente de estado da aplicação por SO.
- Manter suporte a override explícito de diretório quando necessário.

## 4. Escopo
### In Scope
- Resolver diretório persistente de estado por SO.
- Salvar SQLite em subdiretório próprio sob o estado da aplicação.
- Ajustar cleanup para não remover bancos persistentes.
- Atualizar documentação e adicionar testes unitários.

### Out of Scope
- Mudanças no schema do SQLite.
- Consolidação de múltiplas sessões em um único banco.

## 5. Critérios de Aceitação
- O SQLite gerado pelo `CSVManager` deixa de ser criado ao lado do CSV.
- O SQLite passa a ser criado em diretório persistente da aplicação.
- O banco não é apagado no shutdown normal do fluxo.
- Existe override configurável para o diretório do SQLite.
