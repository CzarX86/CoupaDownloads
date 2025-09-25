# ADR 002: Remoção Completa do Fluxo de Trabalho Baseado em CSV

- Status: Proposto
- Data: 2025-09-23
- Responsáveis: Gemini (Developer)

## Estado da revisão (2025-09-25)

- [ ] Implementado no código-base. As rotas da CLI e documentação ainda aceitam o fluxo CSV e o script de migração permanece incompleto, portanto esta decisão arquitetural não foi concretizada.

## Contexto
Com a implementação do pipeline de treinamento baseado em banco de dados (Plano 41), o fluxo de trabalho legado que utiliza arquivos CSV tornou-se obsoleto. Ao lidar com código legado, temos duas opções principais:
1.  **Deprecation (Descontinuação)**: Manter o código legado na base de código, mas marcá-lo como "deprecated" e emitir avisos quando for usado. O código seria removido em um futuro distante.
2.  **Remoção Completa**: Remover ativamente todo o código relacionado ao fluxo legado da base de código como parte do processo de migração.

## Decisão
Optamos pela **remoção completa e imediata** de todo o código relacionado ao fluxo de trabalho baseado em CSV após a migração dos dados legados. Isso inclui a remoção de comandos da CLI, argumentos, e qualquer lógica interna que dependa de arquivos CSV para o processo de treinamento.

## Consequências
### Positivas
- **Redução da Complexidade**: A base de código se torna mais simples e fácil de manter, com um único fluxo de trabalho claramente definido.
- **Prevenção de Erros**: Elimina a possibilidade de os usuários executarem acidentalmente o fluxo de trabalho antigo, o que poderia levar a inconsistências nos dados.
- **Foco no Novo Paradigma**: Força a adoção completa do novo fluxo de trabalho baseado em banco de dados, garantindo que todos os novos desenvolvimentos sejam feitos sobre a nova arquitetura.
- **Redução de Débito Técnico**: Evita que o código legado se torne um débito técnico de longo prazo que precisa ser mantido.

### Negativas
- **Menos Flexibilidade a Curto Prazo**: Se a migração encontrar problemas inesperados, não haverá um caminho de fallback fácil para o fluxo antigo.
- **Impacto Imediato nos Usuários**: Os usuários da CLI serão forçados a se adaptar ao novo fluxo de trabalho imediatamente após a atualização.

### Mitigação
- O risco da migração será mitigado por um script de migração robusto com modo `dry-run` e relatórios de verificação.
- A documentação será atualizada extensivamente para guiar os usuários através do processo de migração e do novo fluxo de trabalho.
- Mensagens de erro claras serão adicionadas à CLI para guiar os usuários que tentarem usar os comandos antigos.
