# Proposta de Mudança: Inicialização do Coupa Turbo Downloader (App Independente e Portátil)

## 1. Identificação
- **Número da Proposta**: 17
- **Título**: Criação do Coupa Turbo Downloader (Aplicação Standalone, Portátil e Ultra-Resiliente)
- **Data de Criação**: 20 de maio de 2026
- **Autor**: Antigravity (a pedido do usuário)
- **Status**: Em Revisão
- **Dependências**: Nenhuma (totalmente isolado do código-fonte legado)

## 2. Contexto e Problema
Com base no benchmark evolutivo de rede que realizamos (utilizando cookies de sessão ativa e conexões assíncronas diretas via `httpx` + `asyncio`), conseguimos atingir a impressionante marca de **69.44 POs/minuto** com consumo de memória de apenas **35MB** (uma redução de ~97% em relação aos workers gráficos baseados em Selenium/Playwright). 

O usuário solicitou a criação de um novo projeto totalmente independente do original, localizado em uma pasta dedicada deste repositório (`CoupaTurboDownloader`). O aplicativo deve ser multiplataforma, portátil (sem requisição de privilégios admin ou instaladores complexos), com uma interface visual ultra-premium e moderna em Tkinter nativo, mecanismos de rate limiting adaptativo para mitigar bans no Coupa e persistência de continuidade resiliente via SQLite.

## 3. Objetivo e Metas
1. **Isolamento de Projeto**: Criar a pasta `/CoupaTurboDownloader` contendo seu próprio ecossistema Python (gerenciado via `uv`) e sua própria estrutura de planejamento GSD (`.planning/`).
2. **Portabilidade Absoluta**: Sem dependências externas de navegadores gráficos ou webviews pesadas. O app deve ser compilado via PyInstaller para Windows (`.exe` portátil) e macOS (`.app` portátil) sem requerer direitos de administrador.
3. **Resiliência e Continuidade**: Arquitetar um banco SQLite leve interno que salve o estado detalhado de processamento de cada PO. Em caso de falha de conexão ou pausa do usuário, a aplicação retoma exatamente de onde parou.
4. **UI Premium e Minimalista**: Uma interface limpa baseada em customização profunda do Tkinter, apresentando telemetria em tempo real (POs processadas, taxa de POs/min, estimativa de tempo (ETA), barra de progresso, alertas de rede e ações de pausa/continuidade).
5. **Segurança de Rate Limiting**: Implementar buffers de cooldown automáticos para sessões extensas e atrasos dinâmicos por lote para evitar bans por atividade robótica no Coupa.

## 4. Escopo

### In Scope
- Criação do diretório `/CoupaTurboDownloader`.
- Inicialização do ambiente `uv` local e criação de `.planning/` (`PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `config.json`, `STATE.md`).
- Implementação de um motor HTTP assíncrono portátil usando `asyncio` e `httpx`, incorporando os parâmetros ideais do algoritmo genético (11 workers, 0.03s delay, 11.7s timeout, parser híbrido `data-url` + `href`).
- Criação de uma UI moderna e minimalista usando Tkinter com estilização customizada e responsiva de alta qualidade.
- Criação de persistência transacional SQLite no diretório de dados do usuário local.
- Scripts de build portátil com PyInstaller.

### Out of Scope
- Modificações no core legacy da pasta `src/` ou `tools/` original (para manter 100% de isolamento).

## 5. Critérios de Aceitação
- Inicialização correta de todas as etapas de planejamento do GSD na nova pasta.
- Inicialização rápida do app compilado sem direitos de administrador em Windows e Mac.
- Velocidade de download de POs com arquivos de anexos validada acima de 30 POs/minuto.
- Recuperação transparente após interrupção simulada de rede sem duplicação de downloads de arquivos já completados.
- UI exibindo telemetria exata e responsiva em tempo real.

## 6. Próximos Passos
- Alinhamento de design detalhado (Documento de Design).
- Obter aprovação das perguntas estratégicas do Socratic Gate e criar a pasta.
