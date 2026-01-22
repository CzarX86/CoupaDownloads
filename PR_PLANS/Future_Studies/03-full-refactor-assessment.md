# Future Study — Avaliação de Refatoração Ampla

## Contexto Atual
- O núcleo do projeto está organizado por domínios em `src/core`, com classes dedicadas para navegador, download, processamento de planilhas e hierarquia de pastas, além de um processador unificado que orquestra CSV e Excel.【F:src/core/downloader.py†L1-L120】【F:src/core/unified_processor.py†L1-L114】【F:src/core/driver_manager.py†L1-L104】【F:src/core/folder_hierarchy.py†L1-L103】
- O fluxo principal (`src/Core_main.py`) já encapsula a maior parte da lógica de orquestração em helpers e uma classe `MainApp`, suportando execução interativa e em paralelo com processos dedicados por PO.【F:src/Core_main.py†L1-L199】【F:src/Core_main.py†L200-L308】

## Sinais Observados
### Fatores a favor de manter evolução incremental
1. **Modularidade existente**: classes como `Downloader`, `UnifiedProcessor`, `DriverManager` e `FolderHierarchyManager` já separam responsabilidades, reduzindo o acoplamento entre ingestão de dados, controle de navegador e manipulação de arquivos.【F:src/core/downloader.py†L1-L163】【F:src/core/unified_processor.py†L1-L150】
2. **Fluxos consolidados**: o `MainApp` reutiliza os componentes centrais e inclui caminhos de recuperação para falhas comuns do Selenium, indicando maturidade do fluxo atual e mitigando risco de regressões abruptas.【F:src/Core_main.py†L200-L308】【F:src/Core_main.py†L308-L400】
3. **Ferramentas de suporte**: existe uma bateria de scripts utilitários e testes direcionados em `src/utils`, cobrindo cenários específicos (detecção de driver, hierarquia de pastas, downloads web) que servem como âncoras para ajustes incrementais.【F:src/utils/test_edge_api.py†L1-L53】【F:src/utils/test_hierarchy_system.py†L1-L80】

### Pontos que merecem atenção
1. **Código duplicado entre modos de execução**: funções auxiliares para aguardar downloads e renomear pastas aparecem tanto em workers multiprocessados quanto na classe `MainApp`, sugerindo uma extração futura para módulo compartilhado em vez de refatorar todo o projeto.【F:src/Core_main.py†L1-L118】【F:src/Core_main.py†L308-L373】
2. **Acoplamento com E/S interativa**: `_interactive_setup` manipula `input()` e variáveis de ambiente diretamente, o que complica testes automatizados, mas pode ser isolado gradualmente (ex.: camada CLI dedicada).【F:src/Core_main.py†L230-L307】
3. **Logging manual via `print`**: a instrumentação espalhada por `print` dificulta observabilidade padronizada; migrar para um logger estruturado pode ser feito módulo a módulo sem exigir reescrita completa.【F:src/Core_main.py†L72-L199】【F:src/core/downloader.py†L64-L163】

## Avaliação
- Uma refatoração total neste momento adicionaria risco elevado: o código cobre automação de navegador, manipulação de arquivos e processamento de planilhas, áreas sensíveis a regressões sutis. O fluxo existente já trata de falhas de sessão, alterna entre execução sequencial e multiprocessada e possui scripts auxiliares especializados, indicando que a base atual é funcional e extensível.【F:src/Core_main.py†L200-L400】【F:src/utils/test_edge_api.py†L1-L53】【F:src/utils/test_hierarchy_system.py†L1-L80】
- A dívida técnica identificada está concentrada em oportunidades pontuais (reduzir duplicação, encapsular entrada interativa, padronizar logging). Essas melhorias podem ser entregues em PRs menores com cobertura progressiva de testes, preservando a confiabilidade atual.

## Recomendação
- **Não prosseguir com uma refatoração ampla agora.** Priorizar um roadmap incremental:
  1. Extrair utilidades compartilhadas (ex.: espera por downloads, renomeação de pastas) para um módulo dedicado em `src/utils` ou `src/core/common.py`.
  2. Introduzir camada de logging estruturado (`structlog`/`logging`) começando pelos módulos com mais `print`.
  3. Encapsular `_interactive_setup` em CLI formal (ex.: `typer`) para facilitar testes e parametrização.
  4. Expandir scripts em `src/utils` para testes automatizados (transformando casos críticos em testes PyTest) antes de ajustes maiores.
- Revisitar a hipótese de refatoração total somente após estabilizar essas entregas incrementais e medir gargalos reais (ex.: métricas de manutenção, tempo de onboarding ou número de incidentes ligados a acoplamento atual).
