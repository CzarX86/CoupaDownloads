# Roadmap futuro — enriquecimento de inputs via Power BI

## Status

**Adiado. Não implementar nesta fase.**

Este documento registra a arquitetura desejada para revisão futura. A execução atual do CoupaTurboDownloader continuará funcionando com input manual, exigindo `PO_NUMBER` e `SUPPLIER`.

## Visão

O usuário poderá informar somente os números das POs. O aplicativo consultará um dataset Power BI autorizado, fará um enriquecimento em lote e preencherá campos como:

- Supplier;
- Legal Entity;
- Country;
- Management Unit;
- Year;
- Quarter;
- demais campos selecionados para a hierarquia de pastas.

O comportamento será equivalente a um `VLOOKUP`, mas realizado em lote no Python por `PO_NUMBER`, evitando uma requisição por PO.

## Arquitetura planejada

```text
Input com PO_NUMBER
        |
        v
EnrichmentProvider
        |
        +-- ManualInputProvider (fase atual)
        |
        +-- PowerBIProvider (futuro)
                    |
                    +-- Microsoft OAuth
                    +-- Power BI REST ExecuteQueries
                    +-- Dataset/tabela configurados
        |
        v
Snapshot enriquecido da sessão
        |
        v
Pipeline canônico de download
```

O contrato futuro deverá ser semelhante a:

```python
class EnrichmentProvider(Protocol):
    def enrich(
        self,
        po_numbers: list[str],
        fields: list[str],
    ) -> EnrichmentResult:
        ...
```

O restante do pipeline não deverá depender diretamente de Power BI. Ele receberá um dataframe normalizado e um snapshot local do enriquecimento.

## Integração preferencial

A primeira opção a investigar é a Power BI REST API, especialmente o endpoint de execução de queries do dataset.

Power Query não será automatizado diretamente: ele é um mecanismo interno do Excel/Power BI, não uma API Python estável para uso standalone.

A API poderá consultar somente os POs listados usando uma consulta filtrada. Não será feito download indiscriminado do dataset.

## Pré-requisitos técnicos

Para avaliar a integração serão necessários:

- URL do relatório ou workspace;
- workspace ID;
- dataset/semantic model ID;
- tabela de POs;
- nome exato da coluna de PO;
- nomes exatos das colunas de enriquecimento;
- permissão `Build` ou equivalente no dataset;
- confirmação de que `ExecuteQueries` está habilitado no tenant;
- regra para registros duplicados ou POs inexistentes.

A existência de acesso visual ao dashboard não garante, por si só, permissão para consultar o dataset via API.

## Template futuro

O template poderá continuar contendo:

```text
PO_NUMBER
SUPPLIER (opcional quando o Power BI estiver disponível)
<|>
[dropdown de campo conhecido]
[dropdown de campo conhecido]
[dropdown de campo conhecido]
```

Os dropdowns deverão ser baseados em um catálogo de campos canônicos. Cada campo canônico terá um mapeamento para o nome real utilizado pelo dataset Power BI.

O usuário poderá escolher quais campos serão usados na hierarquia sem alterar o código do aplicativo.

## Cache e rastreabilidade

Cada enriquecimento deverá ser salvo junto à sessão com:

- lista de POs consultadas;
- campos solicitados;
- dataset e tabela utilizados;
- timestamp da consulta;
- hash do resultado;
- status de cada PO;
- origem dos dados.

Isso permitirá repetir uma execução sem depender de uma nova consulta e manter auditoria do que foi usado na organização das pastas.

## Falhas e fallback

O comportamento planejado é:

- dataset indisponível → informar claramente o erro;
- PO não encontrada → marcar a linha como erro de enriquecimento;
- múltiplos registros → exigir regra explícita ou bloquear a linha;
- autenticação expirada → solicitar novo login Microsoft;
- Power BI não configurado → manter fluxo manual atual.

Não haverá credenciais, tokens ou cookies do Power BI no repositório.

## Próximos passos quando o tema for retomado

1. Receber o esquema anonimizado do dataset.
2. Confirmar permissões de API.
3. Escolher REST API versus XMLA.
4. Definir o catálogo de campos canônicos.
5. Implementar um protótipo somente de consulta, sem iniciar downloads.
6. Validar os resultados contra uma exportação manual do Power BI.
7. Integrar o provider ao pipeline.
8. Adicionar cache, auditoria e fallback manual.
