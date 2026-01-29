# Documento de Design: Otimização - Um Driver por Service Worker (Processo), Reutilizado para Múltiplas POs

## 1. Visão Geral
Este documento detalha o design para a Proposta 01: otimizar o processamento paralelo de POs para usar um driver por worker (processo), reutilizado para múltiplas POs. O objetivo é reduzir overhead de inicialização de drivers, melhorando eficiência sem comprometer isolamento.

## 2. Arquitetura Atual
- **Modo Paralelo**: Cada PO é processado em um processo separado via `ProcessPoolExecutor` ou `PersistentWorkerPool`. Cada processo chama `process_po_worker`, que inicializa um driver isolado.
- **Problemas**: Overhead alto (inicialização/destruição de drivers por PO), ineficiência em recursos para lotes grandes.
- **Componentes Chave**:
  - `process_po_worker`: Função executada por processo, inicializa driver e processa um PO.
  - `BrowserManager`: Gerencia inicialização e cleanup do driver.
  - `FolderHierarchyManager`: Cria pastas por PO.

## 3. Arquitetura Proposta
- **Mudança Principal**: Modificar `process_po_worker` para aceitar uma lista de POs. Inicializar o driver uma vez por worker e reutilizá-lo em um loop interno para processar múltiplas POs.
- **Estrutura**:
  - Worker (processo): Inicializa driver uma vez, processa fila de POs sequencialmente com o mesmo driver.
  - Isolamento: Manter processos separados; adicionar limpeza de sessão entre POs (ex.: deletar cookies).
- **Benefícios**: Redução de ~20-30% em tempo de processamento para lotes grandes, melhor reutilização de recursos.

## 4. Componentes e Interfaces
- **process_po_worker (Modificado)**:
  - Entrada: Lista de POs (dicts), config headless, download_root, csv_path.
  - Lógica: Inicializar driver uma vez; loop sobre POs (criar pasta, atualizar download dir, chamar Downloader, esperar downloads, persistir CSV).
  - Saída: Lista de resultados por PO.
- **BrowserManager**:
  - Adicionar método para limpeza de sessão (ex.: `clear_session()`).
- **PersistentWorkerPool**:
  - Modificar para distribuir filas de POs por worker (ex.: dividir lista total em sublistas por worker).
- **FolderHierarchyManager**:
  - Sem mudanças; pasta por PO permanece isolada.

## 5. Fluxo de Dados
1. MainApp chama _process_po_entries com lista de POs.
2. PersistentWorkerPool divide POs em filas por worker.
3. Cada worker executa process_po_worker:
   - Inicializa driver e perfil clonado.
   - Para cada PO na fila: Cria pasta, atualiza download dir, navega e baixa anexos, limpa sessão.
4. Resultados retornam para MainApp.

## 6. Considerações de Segurança
- **Isolamento**: Perfis clonados por worker; limpeza de sessão entre POs para evitar vazamento de dados (ex.: cookies de fornecedores).
- **Credenciais**: Não armazenar em código; usar variáveis de ambiente.
- **Rede**: Downloads isolados por PO; validar URLs para evitar ataques.

## 7. Plano de Implementação
1. Modificar process_po_worker para loop sobre lista de POs.
2. Adicionar limpeza de sessão em BrowserManager.
3. Atualizar PersistentWorkerPool para dividir filas.
4. Testar com 2-3 POs por worker.
5. Validar isolamento (ex.: POs de fornecedores diferentes não interferem).

## 8. Testes e Validação
- **Unit Tests**: Testar limpeza de sessão e processamento de múltiplas POs em um worker.
- **Integration Tests**: Executar lote de POs paralelos; medir tempo e validar pastas/arquivos.
- **Benchmarks**: Comparar tempo antes/depois com lotes de 10-50 POs.

## 9. Riscos e Mitigações
- **Contaminação de Sessão**: Mitigação - Implementar limpeza obrigatória entre POs.
- **Falhas de Driver**: Mitigação - Adicionar try/except e reinicialização se necessário.
- **Compatibilidade**: Mitigação - Manter fallback para modo sequencial.

## 10. Métricas de Sucesso
- Redução de tempo de processamento >20%.
- Zero conflitos entre POs (validado por testes).
- Código passa em todos testes existentes.</content>
<parameter name="filePath">/Users/juliocezar/Dev/CoupaDownloads_Refactoring/PR_PLANS/01-driver-per-worker-design-doc.md