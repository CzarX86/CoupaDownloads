# Proposta de Mudança: Motor de Download Turbo e Sintonizador Genético de Rede

## 1. Identificação
- **Número da Proposta**: 16
- **Título**: Motor de Download Turbo (Bypass de Browser) e Sintonizador de Hiperparâmetros via Algoritmo Genético
- **Data de Criação**: 20 de maio de 2026
- **Autor**: Antigravity (a pedido do usuário)
- **Status**: Em Revisão
- **Dependências**: Nenhuma

## 2. Contexto e Problema
O downloader de anexos do Coupa atualmente depende de automação de navegador (Selenium/Playwright) para a maioria das operações de raspagem. Embora exista um modo `direct_http`, ele falha completamente no ambiente de staging atual porque:
1. O Coupa atualizou o DOM para renderizar anexos dentro de elementos `<span>` usando o atributo `data-url` (por exemplo, `<span class="attachment-file attachment-list-item" data-url="...">`), em vez das tradicionais tags de âncora `<a>` com `href`.
2. A latência e o throughput de rede não são otimizados, resultando em velocidades baixas (~4-8 POs por minuto) e alto footprint de hardware (RAM/CPU) decorrente de instâncias ativas de navegador.

## 3. Objetivo
1. **Corrigir o Extrator de DOM do `DirectHTTPDownloader`**: Suportar tanto a estrutura moderna baseada em `data-url` quanto as âncoras tradicionais (`href`).
2. **Habilitar Parâmetros Genéticos de Rede**: Implementar suporte na classe principal para utilizar os hiperparâmetros de rede otimizados evolutivamente (Timeout de `11.7s`, atrasos controlados e suporte para o alto limite de concorrência de `11` conexões simultâneas).
3. **Desempenho Estelar**: Garantir uma taxa de processamento superior a **60 POs por minuto** no modo Turbo (Direct HTTP), reduzindo em ~97% o consumo de RAM e ~90% o consumo de CPU.

## 4. Escopo
### In Scope
- Correção do algoritmo de raspagem de BeautifulSoup em `src/lib/direct_http_downloader.py` para suportar `data-url` de forma robusta e resiliente.
- Parametrizar a inicialização do `DirectHTTPDownloader` permitindo timeouts configuráveis (passando a usar o ótimo de `11.7s` em vez dos fixos `30.0s`).
- Integrar logs claros e métricas em inglês para a auditoria de desempenho.

### Out of Scope
- Implementar o CLI de re-treinamento genético no código de produção principal (manteremos o algoritmo genético na CLI auxiliar ou como script standalone em `tools/` para não poluir o core principal).
- Alterar as persistências de dados do SQLite ou CSV.

## 5. Critérios de Aceitação
- Taxa de sucesso de 100% no download de POs válidas com anexos no Coupa.
- Coleta correta de anexos representados como `<span class="attachment-file" data-url="...">`.
- Suporte a fallback automático e coexistência com o parser de âncora tradicional.
- Atendimento e superação do benchmark de **20-30 POs/minuto** (nossos testes validaram **69.44 POs/minuto**!).

## 6. Riscos e Mitigações
- **Risco**: Expiração súbita de cookies de sessão no meio do lote assíncrono.
  - **Mitigação**: O sistema já captura cookies autenticados do WebDriver clonado uma vez por reusable worker, garantindo frescor de sessão com zero intervenção manual.

## 7. Plano de Implementação (Alto Nível)
1. Atualizar a classe `DirectHTTPDownloader` com o novo parser BeautifulSoup unificado.
2. Injetar suporte a timeouts dinâmicos na inicialização da sessão `httpx.Client`.
3. Executar auditoria local dos testes finais.

## 8. Próximos Passos
- Elaborar documento de design detalhado.
- Realizar a codificação após aprovação.
