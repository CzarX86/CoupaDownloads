# Dados descobertos nas páginas do Coupa

## Objetivo

Este documento registra a sondagem realizada para identificar quais dados das páginas de Purchase Order (PO) do Coupa podem ser incorporados ao relatório final do Contract Downloader.

A sondagem foi somente leitura. Foram consultadas as cinco primeiras POs de `input.csv`:

- `PO16801298`
- `PO17105916`
- `PO17191804`
- `PO16194384`
- `PO16365577`

Não foram alterados dados no Coupa, arquivos de origem, banco de sessões ou anexos.

## Conclusão da sondagem

Os dados abaixo estão disponíveis nas páginas consultadas:

- Dados gerais da PO.
- Nome e identificador do fornecedor.
- Company Code.
- Endereço e usuário de entrega.
- Payment Term.
- Dados de cada linha da PO.
- Conta contábil completa.
- Dados exibidos no mouse-over da conta.
- Anexos e links de download.
- Requisição (PR) relacionada.
- Recebimentos.
- Histórico de alterações e comentários.
- Histórico de integrações.

Os dados do mouse-over da conta estavam presentes no HTML inicial da página. Portanto, a primeira implementação não precisa simular o movimento do mouse com Selenium para esses campos.

## Escopo inicial aprovado para o relatório

A primeira versão deve extrair somente estes campos:

| Campo do relatório | Nível | Origem observada | Regra inicial |
|---|---|---|---|
| `company_code` | PO/endereço de entrega | Campo `Company Code` | Preservar como texto, mesmo quando for numérico |
| `crg_code` | Linha/account | Campo `CC FuncA`, por exemplo `R5600-General Overheads` | Extrair o código de quatro dígitos quando o padrão for reconhecido |
| `crg_raw` | Linha/account | Valor completo de `CC FuncA` | Preservar o valor original para auditoria |
| `ship_to_user` | PO | Campo `Ship To User` | Preservar o texto exibido |
| `payment_term` | PO | Campo `Payment Term`, por exemplo `P090` | Preservar o código original |
| `currency_code` | Linha | Moeda associada a `Price` e `Total` | Extrair o código exibido, como `EUR`; não inferir moeda ausente |

### Supplier/Vendor Code

A solicitação anterior mencionou `supplier code`. Esse campo também aparece no escopo de descoberta:

| Campo do relatório | Nível | Origem observada | Observação |
|---|---|---|---|
| `supplier_name_raw` | PO | Nome do fornecedor exibido no painel Supplier | Preservar o texto completo |
| `supplier_code` | PO | Sufixo numérico junto ao nome do fornecedor | O valor deve ser tratado inicialmente como candidato e validado contra o cadastro de fornecedores |
| `supplier_tooltip_raw` | PO | Atributo `title` do nome do fornecedor | Preservar para auditoria; pode conter identificadores adicionais |

A expressão “currículo code” foi interpretada como possível referência a `Currency Code`. Por segurança, esta documentação mantém os dois conceitos separados: `supplier_code`/`vendor_code` e `currency_code`.

## Campos gerais da PO encontrados

Os seguintes campos foram identificados no bloco General Info:

- PO Number.
- Status.
- Order Date.
- Revision Date.
- Requisition Number.
- Requester.
- Ship To User.
- Department.
- Hide Price.
- Payment Term.
- Migrated PO Number.
- Sponsorship ID.
- Purchase Summary.
- Total Paid Amount.
- Reason for Priority Request.
- PR Type.
- Reason for not using catalogue.
- Alternate Approver.
- Reason for not using Preferred Supplier.
- Place of Service or Nature of Payment.
- Invoicing Method.
- Preferred Supplier Status.
- ToA Approver.
- Attachments.

Alguns campos estavam vazios em parte das POs. A ausência de valor deve ser registrada como vazio/`None`, nunca como um valor inventado.

## Supplier, shipping e Company Code

No painel Supplier foram encontrados:

- Nome do fornecedor.
- Código ou identificador junto ao nome.
- Tooltip com identificadores adicionais.
- Primary Address.
- Company Code do cadastro do fornecedor, quando preenchido.
- GST.
- Email Opened.
- Transmission Method.

No painel Shipping foram encontrados:

- Endereço de entrega.
- Location Code.
- Attn.
- Company Code.
- GST.
- Terms.

O `Company Code` do endereço de entrega é o candidato principal para o relatório inicial. Quando houver mais de uma ocorrência, recomenda-se guardar tanto `company_code` quanto a origem (`shipping` ou `supplier`).

## Campos encontrados por linha da PO

Cada linha pode conter:

- Line Number.
- Type.
- Item.
- Price.
- Currency.
- Total.
- Line Status.
- Received.
- Returned.
- Voided.
- Approved Invoiced.
- Credits/Returns.
- Pending Invoiced.
- Pending Credits/Returns.
- Total Invoiced.
- Pending Receipt.
- Expected Delivery/Completion Date.
- Supplier Part Number.
- Supplier Auxiliary Part Number.
- Commodity.
- Manufacturer Name.
- Manufacturer Part Number.
- Receipt Approval Required.
- Savings (%).
- MRP PR Number.
- MRP PR Line Number.
- CLM Contract/E-Tree Contract.
- Migrated PO Line Number.
- Paid Amount.
- SAP Material Number.
- Additional Details.
- Material Description.
- Invoicing Method.
- Tax Codes.
- AdManager Number.
- Start Date.
- Material Type.
- Catalog.
- Account.
- Period.
- Attachments.

A moeda é um atributo da linha, pois `Price` e `Total` são exibidos com o código de moeda. Se uma PO tiver várias linhas, o relatório não deve repetir uma única moeda de forma incorreta no nível da PO.

## Conta contábil e dados do mouse-over

A área `Account` apresenta uma combinação contábil completa. No mouse-over foram encontrados os seguintes componentes:

- `CommCode` — código e descrição da commodity.
- `GL Acct` — conta contábil e descrição.
- `Acct Cat` — categoria da conta, como `Cost Centre`.
- `CC/A` — centro de custo/área e descrição.
- `IO` — ordem interna, quando preenchida.
- `CC FuncA` — função/CRG e descrição, por exemplo `R5600-General Overheads`.
- `CC FncID` — identificador da função e descrição.

### Regra inicial para CRG

O valor completo deve ser guardado em `crg_raw`. Quando `CC FuncA` contiver um código no formato `R` seguido de quatro dígitos, o relatório pode preencher:

```text
CC FuncA: R5600-General Overheads
crg_code: 5600
crg_raw: R5600-General Overheads
```

A regra não deve descartar valores que não sigam esse padrão. Nesses casos, `crg_code` fica vazio e `crg_raw` permanece disponível para análise.

## Requisição relacionada (PR)

Todas as cinco POs possuíam uma requisição vinculada e a página da PR respondeu normalmente. Foram identificados campos como:

- Requisition Number.
- Requested By.
- Created By.
- Department.
- Application Name.
- Purchase Summary.
- PR Type.
- Business Justification/Quotation/SOW.
- Note To Approver.
- Reason for not using catalogue.
- Reason for not using Preferred Supplier.
- Alternate Approver.
- ToA Approver.
- UBuy Request ID.
- Sponsorship ID.
- Change Approver?
- Do legal triggers apply as per policy?
- Ship-To Address.
- Company Code.
- GST.
- Supplier Company Codes.
- Cart Items.
- Approvers.
- Comments.
- History.

Esses campos ficam fora do escopo inicial, mas devem ser considerados na evolução do relatório.

## Recebimentos

As páginas de recebimento relacionadas às linhas também foram acessíveis. Os cabeçalhos encontrados incluem:

- Created Date.
- Status.
- Type.
- PO ID.
- Order Line Number.
- Invoice/ASN Line.
- Invoice Line Number/ASN Line.
- Item.
- Supplier.
- Receiver.
- Quantity.
- UOM.
- Price.
- Currency.
- Total.
- Receipts Batch Source.

Esses dados devem formar uma tabela filha, com uma linha por recebimento, e não ser concatenados na linha principal da PO.

## Histórico e integrações

A página da PO expõe endpoints adicionais para:

- Histórico de alterações.
- Comentários.
- Inclusão ou remoção de anexos.
- Alteração de status.
- Alteração de valores.
- Histórico de integrações.
- Nome de arquivos de exportação.
- Sistemas de destino, como DataLake, EasyGR, IPA e Unimart.

Esses eventos também devem ser tratados como tabelas filhas, uma linha por evento.

## Anexos

A página contém links e metadados de anexos, incluindo:

- Nome do arquivo.
- URL de download.
- Origem aparente, como fornecedor.
- Anexos de PO e de PR.

O texto exibido junto ao anexo pode conter informações de invoices e pagamentos. O parser deve distinguir o nome real do arquivo de texto histórico para não criar nomes de anexos incorretos.

## Estrutura recomendada para a implementação futura

Mesmo começando com poucos campos, recomenda-se manter duas tabelas principais:

### `po_summary`

```text
po_number
company_code
ship_to_user
payment_term
supplier_name_raw
supplier_code
supplier_tooltip_raw
```

### `po_lines`

```text
po_number
line_number
crg_code
crg_raw
currency_code
```

A estrutura pode evoluir posteriormente para:

- `po_accounting`
- `po_receipts`
- `po_attachments`
- `po_history`
- `po_integrations`
- `po_requisitions`

Todos os registros filhos devem conter `po_number` e, quando aplicável, `line_number`.

## Regras de qualidade e segurança

- Preservar os valores crus e os valores normalizados separadamente.
- Tratar Company Code, Payment Term, CRG e Currency como texto para não perder zeros à esquerda.
- Não preencher campos ausentes por inferência.
- Não assumir que o código numérico no nome do fornecedor é sempre o Vendor Code sem validação do cadastro.
- Não considerar `R5600` como CRG sem preservar também o texto completo de `CC FuncA`.
- Respeitar permissões do usuário: páginas, PRs, recebimentos e históricos podem ter visibilidade diferente.
- Fazer requisições adicionais com limite e baixa concorrência para não sobrecarregar o Coupa.
- Não armazenar cookies, credenciais ou HTML bruto no relatório final.
- A implementação deve ser somente leitura no Coupa.

## Implementação inicial

A primeira versão foi implementada em módulos desacoplados:

- `src/engine/coupa_metadata.py` — modelos e extração pura a partir do HTML.
- `src/db/coupa_metadata.py` — persistência SQLite dos metadados de PO e linha.
- `src/reports/coupa_excel.py` — enriquecimento do Excel e criação da aba `COUPA_LINES`.

O crawler salva os metadados durante o mesmo acesso usado para processar a PO. A GUI e o CLI reutilizam o mesmo repositório e o mesmo enriquecedor de relatório.

O relatório principal recebe:

- `COUPA_COMPANY_CODE`;
- `COUPA_SHIP_TO_USER`;
- `COUPA_PAYMENT_TERM`;
- `COUPA_CRG_CODES`;
- `COUPA_CRG_RAW`;
- `COUPA_CURRENCY_CODES`;
- `COUPA_METADATA_STATUS`;
- `COUPA_METADATA_SCRAPED_AT`;
- `COUPA_METADATA_ERROR`.

A aba `COUPA_LINES` mantém uma linha por linha da PO, evitando perder CRG ou moeda quando uma PO possuir várias linhas.

Falhas de extração não interrompem o download dos anexos. Nesses casos, o relatório registra `UNAVAILABLE` ou `PARTIAL` e preserva a mensagem de erro.
