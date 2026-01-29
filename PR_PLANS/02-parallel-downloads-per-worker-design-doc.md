# Documento de Design: Otimização - Downloads Paralelos por Worker com Pool de Downloads

## 1. Visão Geral
Este documento detalha o design para a Proposta 02: introduzir downloads paralelos dentro de cada worker, usando um pool de downloads para processar anexos de um PO simultaneamente. O objetivo é acelerar processamento de POs com múltiplos anexos, integrando com a Proposta 01 (um driver por worker).

## 2. Arquitetura Atual
- **Downloads**: Sequenciais via `Downloader.download_attachments_for_po()`, que identifica anexos e baixa um por vez, esperando conclusão.
- **Problemas**: Lentidão para POs com muitos anexos; subutilização de rede/CPU.
- **Componentes Chave** (após refatoração PR 03):
  - `Downloader`: Classe que navega e baixa anexos.
  - `WorkerManager`: Contém `_wait_for_downloads_complete()` e lógica de processamento.
  - `ProcessingController`: Coordena processamento.

## 3. Arquitetura Proposta
- **Mudança Principal**: Modificar `Downloader` para usar um pool de threads (`ThreadPoolExecutor`) dentro do worker. O worker identifica anexos, enfileira-os, e o pool processa downloads em paralelo (até N simultâneos).
- **Estrutura**:
  - Worker (via WorkerManager): Navega página, coleta anexos em fila.
  - Subworker (threads): Processa fila, inicia downloads, monitora status.
  - Isolamento: Downloads vão para pasta do PO; usar nomes únicos para evitar conflitos.
- **Benefícios**: Redução de ~30-50% em tempo para POs com >1 anexo; melhor eficiência.

## 4. Componentes e Interfaces
- **Downloader (Modificado)**:
  - Novo método: `download_attachments_parallel(attachments_list, max_concurrent=4)` - Usa ThreadPoolExecutor para downloads simultâneos.
  - Entrada: Lista de anexos (URLs/nomes), pasta de download.
  - Lógica: Enfileirar downloads, monitorar progresso, aguardar conclusão.
- **WorkerManager (Modificado)**:
  - Funções worker: Após navegar, coletar anexos e chamar `download_attachments_parallel`.
- **ThreadPoolExecutor**:
  - Configurável (ex.: 2-4 threads por worker); integrado com `_wait_for_downloads_complete()` adaptado.
- **ProcessingController**:
  - Coordena chamada para WorkerManager.

## 5. Fluxo de Dados
1. Worker (via WorkerManager) navega para PO e identifica anexos (lista de dicts com URL, nome).
2. Enfileira anexos em uma fila (Queue).
3. ThreadPoolExecutor processa fila: Para cada anexo, iniciar download via Selenium, monitorar arquivo em pasta.
4. Aguardar todos downloads completarem; validar integridade.
5. Retornar resultados para ProcessingController.

## 6. Considerações de Segurança
- **Isolamento**: Downloads isolados por PO.
- **Recursos**: Limitar threads para evitar sobrecarga; monitorar uso de CPU/rede.
- **Dados**: Não expor credenciais; usar HTTPS para downloads.

## 7. Plano de Implementação
1. Modificar `Downloader` para suportar pool de threads.
2. Atualizar funções worker em `WorkerManager` para coletar anexos e chamar método paralelo.
3. Adicionar configuração para max_concurrent (ex.: via PoolConfig).
4. Testar com PO de teste (múltiplos anexos).
5. Integrar com Proposta 01 se aprovada.

## 8. Testes e Validação
- **Unit Tests**: Testar enfileiramento e processamento paralelo.
- **Integration Tests**: Baixar múltiplos anexos; validar arquivos corretos em pasta.

## 9. Riscos e Mitigações
- **Conflitos de Arquivos**: Mitigação - tbd.
- **Falhas de Rede**: Mitigação - Retry em threads; logging detalhado.
- **Overhead de Threads**: Mitigação - Limitar a 4 threads; testar em ambientes limitados.

## 10. Métricas de Sucesso
- Redução de tempo >30% para POs com múltiplos anexos.
- Zero downloads perdidos ou corrompidos.
- Compatibilidade com empacotamento (threads leves).</content>
