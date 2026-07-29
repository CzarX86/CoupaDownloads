# Plano de implementação — alinhamento de input, template e relatórios

## Objetivo

Unificar o contrato de entrada entre a GUI e o pipeline canônico `process_all_pos.py`, mantendo o input original intacto e garantindo que relatórios normais, retries e exportações do histórico preservem todas as colunas fornecidas pelo usuário.

A integração com Power BI não faz parte deste plano. Ela está registrada em `docs/roadmap-integracao-powerbi.md` como evolução futura.

## Escopo desta entrega

### Incluído

- Template Excel configurável, com defaults conhecidos.
- Dropdowns para seleção dos níveis de hierarquia de pastas.
- Normalização consistente de aliases entre validação, GUI e CLI.
- Preservação das colunas originais do input.
- Relatório canônico com dados do input e resultados da execução.
- Relatórios de retry baseados no input arquivado da execução original.
- Exportação pelo histórico usando a mesma fonte do relatório canônico.
- Testes para colunas personalizadas, hierarquia e retries.

### Explicitamente fora do escopo

- Consulta a datasets ou relatórios Power BI.
- Login Microsoft/OAuth.
- Power Query, XMLA ou Power BI REST API.
- Enriquecimento automático de Supplier, Legal Entity, Country ou Management Unit.

Até a integração futura com Power BI, `SUPPLIER` continuará sendo obrigatório no input.

## Contrato provisório de input

O template deve continuar simples, sem colunas de resultado:

```text
PO_NUMBER
SUPPLIER
<|>
Company
Year
Quarter
Business Unit
```

Regras:

- `PO_NUMBER` é obrigatório.
- `SUPPLIER` é obrigatório enquanto não existir um provedor de enriquecimento.
- `<|>` marca o início dos níveis de pasta.
- Todas as colunas após `<|>` são opcionais e configuráveis.
- As colunas de resultado (`STATUS`, `DOWNLOAD_FOLDER`, `ATTACHMENTS_FOUND` etc.) não serão necessárias para um novo input.
- Inputs antigos que já contenham colunas de resultado continuarão sendo aceitos.

Os nomes default de hierarquia ficam centralizados em uma lista configurável. A lista oficial desta fase será mantida como está atualmente:

```text
Company
Year
Quarter
Business Unit
```

O usuário poderá enriquecer ou substituir os níveis usando os dropdowns do template.

## Template Excel configurável

A geração do template deverá:

1. manter `PO_NUMBER`, `SUPPLIER` e `<|>` fixos;
2. preencher níveis padrão após `<|>`;
3. criar uma aba oculta ou auxiliar com a lista de campos permitidos;
4. aplicar validação de dados nos headers dos níveis de hierarquia;
5. impedir seleção de campos desconhecidos;
6. detectar headers repetidos e impedir duas seleções iguais;
7. manter a aba `Instructions` explicando que os campos após `<|>` controlam a pasta;
8. não gravar dados de execução no template.

A validação no header serve para escolher o campo que será usado como nível de pasta. Os valores das linhas continuam vindo do arquivo preenchido pelo usuário.

## Normalização de schema

Criar uma camada única de normalização, usada pela GUI e pelo pipeline:

- `PO_NUMBER`, `PO` e `Pedido` → `PO_NUMBER`;
- `SUPPLIER`, `LegalEntity`, `CompanyCode` e `Empresa` → `SUPPLIER`;
- nomes são comparados sem diferença de maiúsculas, espaços, pontuação ou acentos;
- a normalização ocorre em uma cópia em memória;
- o arquivo original nunca é sobrescrito automaticamente.

O pipeline não deve continuar aceitando um alias na tela e ignorá-lo durante a execução real.

## Preservação do input e relatórios

### Fonte única

Cada sessão já arquiva o input. A implementação deverá fazer o gerador de relatório resolver a fonte nesta ordem:

1. input original ainda existente;
2. input arquivado na própria sessão;
3. input arquivado na sessão de origem, em caso de retry;
4. somente como último recurso, dados do banco.

### Relatório normal

O relatório deverá:

- começar com o input simplificado original;
- preservar todas as colunas fornecidas pelo usuário e sua ordem;
- preservar os valores originais dessas colunas;
- acrescentar as colunas de resultado da execução;
- manter as colunas de hierarquia;
- fazer o merge por `PO_NUMBER` normalizado;
- lidar com POs duplicadas de forma explícita na validação.

As colunas abaixo são **colunas de saída**, criadas e populadas pelo script depois da execução. Elas não fazem parte do novo input simplificado:

```text
STATUS
ATTACHMENTS_FOUND
ATTACHMENTS_DOWNLOADED
AttachmentName
LAST_PROCESSED
ERROR_MESSAGE
DOWNLOAD_FOLDER
COUPA_URL
```

A regra será:

- input novo: não contém essas colunas;
- relatório: cria essas colunas com os resultados atuais;
- input histórico que já contenha essas colunas: é aceito por compatibilidade, e os valores antigos dessas colunas são substituídos pelos resultados da execução atual;
- nenhuma coluna de negócio ou hierarquia fornecida pelo usuário é descartada.

Assim, o arquivo de input permanece simples e o relatório final é o artefato enriquecido pela execução. Não será necessário introduzir nomes `RUN_*` enquanto o input novo não contiver colunas de resultado.

### Retry e atualização do relatório

Retries individuais, retries de erros e retries in-place devem reutilizar o snapshot do input de origem.

Para o fluxo in-place usado pela GUI:

- o mesmo `session_id` é mantido;
- o mesmo diretório `run_*` é reutilizado;
- o mesmo `report_session_<id>.xlsx` é sobrescrito de forma controlada;
- somente as POs reprocessadas têm seus resultados atualizados;
- POs que já estavam corretas permanecem no relatório;
- uma nova falha substitui a mensagem de erro anterior;
- uma nova tentativa bem-sucedida limpa a mensagem de erro e atualiza o status;
- `LAST_PROCESSED` recebe o timestamp da tentativa mais recente, inclusive quando ela falha;
- o timestamp deve ter precisão suficiente para diferenciar retries executados no mesmo segundo.

O relatório não poderá cair no fallback reduzido apenas com dados do banco quando houver um input arquivado disponível. Nenhum novo relatório será criado para o retry in-place.

### Histórico

`export_session_report` deverá procurar o relatório canônico e, se precisar reconstruí-lo, chamar o mesmo gerador usado pelo pipeline, em vez de criar um `DataFrame` apenas com `details["pos"]`.

## Plano de execução

### Fase 1 — Contrato e testes de caracterização

- Registrar headers dos inputs reais usados atualmente.
- Criar fixtures com:
  - input mínimo;
  - input com hierarquia;
  - input enriquecido com colunas de resultados;
  - aliases de PO e Supplier;
  - retry com input arquivado.
- Testar o comportamento atual para capturar regressões.

### Fase 2 — Normalização comum

- Criar módulo de schema/input.
- Fazer GUI e pipeline consumirem a mesma normalização.
- Garantir que aliases aceitos pela validação sejam processáveis pelo CLI.
- Manter o arquivo original inalterado.

### Fase 3 — Template configurável

- Atualizar a criação do workbook.
- Adicionar lista de campos permitidos.
- Adicionar validação de dados nos headers de hierarquia.
- Validar campos repetidos, vazios e desconhecidos.
- Atualizar as instruções da GUI.

### Fase 4 — Relatório preservativo

- Refatorar `export_original_like_excel_report` para aceitar qualquer formato suportado.
- Preservar schema e valores originais.
- Adicionar colunas de execução sem colisão destrutiva.
- Resolver input arquivado para todas as modalidades de retry.

### Fase 5 — Histórico e retries

- Fazer exportação do histórico usar o gerador canônico.
- Cobrir retry individual, retry de erros e retry in-place.
- Verificar que inputs e hierarquia permanecem disponíveis após a exclusão ou movimentação do arquivo original.

### Fase 6 — Validação final

- Rodar a suíte automatizada.
- Gerar um template novo e preenchê-lo com um caso real pequeno.
- Executar uma execução normal.
- Executar retry individual e retry de erros.
- Comparar headers do input, relatório normal e relatório de retry.
- Validar o bundle macOS e o build Windows.

## Critérios de aceite

- Um input com colunas personalizadas mantém essas colunas no relatório normal.
- Um retry não perde os níveis de hierarquia.
- Um retry atualiza o relatório existente em vez de criar um segundo relatório.
- `LAST_PROCESSED` e `ERROR_MESSAGE` refletem a tentativa mais recente, inclusive em caso de nova falha.
- Um input com aliases aceitos pela GUI é processado pelo pipeline.
- O template possui dropdowns nos níveis de hierarquia.
- O usuário não precisa preencher colunas de status para iniciar uma nova execução.
- O arquivo original permanece inalterado.
- Nenhum relatório depende exclusivamente da existência física do input original.
- A integração Power BI não é necessária para qualquer comportamento desta entrega.

## Decisões confirmadas

- A lista default de hierarquia permanece:
  - `Company`;
  - `Year`;
  - `Quarter`;
  - `Business Unit`.
- `STATUS` e as demais colunas de execução são criadas pelo script no relatório, não exigidas no input.
- Inputs históricos que já contenham colunas de resultado continuam compatíveis; essas colunas serão atualizadas com o resultado da execução atual.
- O input novo será simplificado e o relatório será o arquivo enriquecido após a execução.
