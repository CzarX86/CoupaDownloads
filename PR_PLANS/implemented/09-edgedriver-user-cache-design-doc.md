# Documento de Design: Persistência de EdgeDriver via Cache de Usuário

## 1. Contexto
O `DriverManager` concentrava detecção de versão, busca local em `drivers/`, download temporário, extração, validação e limpeza. Esse desenho gerava acoplamento alto e descartava o binário baixado no encerramento da execução, causando redownload recorrente.

## 2. Decisão Técnica
### 2.1 Política única de resolução
- `EDGE_DRIVER_PATH` continua apenas como override explícito.
- Fora do override, o fluxo padrão será: cache persistente por usuário -> download -> publicação atômica no cache.
- O repositório deixa de ser local suportado para EdgeDriver.

### 2.2 Separação de responsabilidades
- `EdgeVersionProvider`: detecta a versão instalada do navegador.
- `DriverValidator`: valida binário, arquitetura e execução.
- `DriverCache`: resolve diretório de cache, localiza entradas, publica binários e limpa versões antigas.
- `DriverDownloader`: consulta versão compatível online, baixa e extrai em staging temporário.
- `DriverResolver`: orquestra override, cache, download, lock e publicação.
- `DriverManager`: permanece como fachada fina para não espalhar mudanças pelos workers.

### 2.3 Cache persistente
- Local por SO:
  - macOS: `~/Library/Caches/CoupaDownloads/drivers/edgedriver/`
  - Windows: `%LOCALAPPDATA%/CoupaDownloads/drivers/edgedriver/`
  - Linux: `$XDG_CACHE_HOME/CoupaDownloads/drivers/edgedriver/` com fallback `~/.cache/CoupaDownloads/drivers/edgedriver/`
- Estrutura: `<cache_root>/<platform>/<driver_version>/msedgedriver`
- Publicação via cópia para arquivo temporário e `os.replace` no destino final.

### 2.4 Concorrência
- Lock por versão em `<cache_root>/<platform>/<driver_version>/.lock`.
- Worker que não obtiver lock aguarda, depois revalida o binário publicado antes de tentar novo download.
- Locks antigos podem ser descartados após janela de stale timeout.

### 2.5 Invalidação e limpeza
- Cache inválido é removido seletivamente quando falha em validação.
- Versões antigas são limpas de forma conservadora após publicação bem-sucedida.
- Política default: manter a atual e a anterior mais recente por plataforma.

## 3. Impactos em Interface Interna
- `WorkerProcess` continua chamando `DriverManager`, mas deixa de depender de busca em `drivers/`.
- `AppConfig` passa a expor `EDGE_DRIVER_CACHE_DIR`, `DRIVER_CACHE_ENABLED` e `DRIVER_CACHE_CLEANUP_ENABLED`.
- `SetupManager` deixa de oferecer scanner de drivers locais.

## 4. Fluxo Atualizado
1. Worker solicita `DriverManager.get_driver_path()`.
2. Resolver valida `EDGE_DRIVER_PATH`, se configurado.
3. Resolver detecta a versão do Edge.
4. Cache é consultado localmente sem chamada de rede.
5. Em cache miss, o resolver consulta a versão compatível online, baixa em staging, valida e publica no cache.
6. Worker usa o binário final validado.

## 5. Validação
- Executar testes unitários do novo módulo de driver.
- Validar cenário de cache hit sem chamada de download.
- Validar cenário concorrente com apenas um download efetivo.
