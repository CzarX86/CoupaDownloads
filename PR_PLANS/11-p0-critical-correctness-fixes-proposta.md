# Proposta de Mudança: Correções Críticas de Corretude (P0)

## 1. Identificação
- **Número da Proposta**: 11
- **Título**: Correções Críticas: Path do Edge no Windows + Remoção de Lock/Driver Depreciados
- **Data de Criação**: 1 de abril de 2026
- **Autor**: GitHub Copilot
- **Status**: Aprovado — Em Implementação
- **Dependências**: Nenhuma

## 2. Contexto e Problema

### 2.1 Path do Edge no Windows não expandido
`src/config/app_config.py` linha 119 define o caminho do perfil Edge no Windows como:
```
"%LOCALAPPDATA%/Microsoft Edge/User Data"
```
Esse é um **literal de string**, não um caminho expandido. Python não interpreta `%VARIAVEL%` — esse é o formato do `cmd.exe`. O resultado é que no Windows o campo `edge_profile_dir` aponta para um caminho incorreto, fazendo com que qualquer checagem de existência (`Path.exists()`, `Path.is_dir()`) falhe silenciosamente, impedindo o uso de perfis e potencialmente causando falha de inicialização do browser.

### 2.2 `MainApp.driver` e `MainApp.lock` depreciados ainda ativos
`src/main.py` linhas 187–188 inicializam `self.driver = None` e `self.lock = threading.Lock()` marcados como depreciados. O `driver` é sempre `None` (nunca é atribuído num valor válido), mas é passado para `self.processing_service.driver` em cada chamada de `process_single_po`, sobrescrevendo o driver interno do serviço para `None` — forçando recriação do browser a cada PO no modo sequencial.

O `self.lock` é um segundo ponto de sincronização paralelo ao `BrowserOrchestrator.lock`, que é o lock real. Essa duplicação sem hierarquia de aquisição documentada é um risco latente de deadlock.

O método `initialize_browser_once()` (linha 390) é um wrapper depreciado em torno de `browser_orchestrator.initialize_browser()`.

## 3. Objetivo
- Corrigir o path do Edge no Windows usando `os.environ` com expansão correta.
- Remover `self.driver`, `self.lock` e o método `initialize_browser_once()` de `MainApp`.
- Eliminar o override de driver/lock no `process_single_po`, permitindo que o `ProcessingService` reutilize seu driver entre POs no modo sequencial.

## 4. Escopo
**Incluso:**
- Correção do campo `edge_profile_dir` em `src/config/app_config.py`.
- Remoção de `self.driver = None`, `self.lock = threading.Lock()` de `MainApp.__init__`.
- Remoção de `self.processing_service.driver = self.driver` e `self.processing_service.lock = self.lock` de `process_single_po`.
- Remoção do bloco `if self.driver: ... self.driver = None` em `_cleanup_resources`.
- Renomeação de `initialize_browser_once()` para `_initialize_browser_once()` (privado) — remoção da API pública.

**Fora de escopo:**
- Mudanças na lógica de `BrowserOrchestrator`.
- Alterações de schema de dados ou CLI.

## 5. Critérios de Aceitação
- No Windows, `app_config.edge_profile_dir` resolve para um caminho real com `LOCALAPPDATA` expandido.
- `MainApp` não possui atributos públicos `driver` nem `lock`.
- `process_single_po` não sobrescreve `processing_service.driver` nem `processing_service.lock`.
- `uv run pytest` executa sem regressões.

## 6. Riscos e Mitigações
- **Risco**: sem o override de driver, ProcessingService pode inicializar driver diferente do esperado em modal sequencial.
  - **Mitigação**: ProcessingService já inicializa driver via `browser_manager` internamente; remover o override melhora comportamento (reutilização entre POs).
- **Risco**: no Windows, `LOCALAPPDATA` pode não estar definido em contextos de serviço.
  - **Mitigação**: fallback para `Path.home() / "AppData" / "Local"`.

## 7. Plano de Validação
- `uv run pytest` sem erros.
- Grep por `self\.driver\s*=\s*None` e `self\.lock\s*=\s*threading` em `src/main.py` — zero resultados.
