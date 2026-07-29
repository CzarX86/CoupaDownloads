# Documento de Design: SQLite em Diretório Persistente de Estado da Aplicação

## 1. Contexto
O SQLite era tratado como arquivo temporário de sessão, criado perto do CSV de entrada e removido no shutdown. Isso conflita com a nova política de separar cache de runtime de dados persistentes da aplicação.

## 2. Decisão Técnica
- Introduzir `application_state_dir` em `AppConfig`, com defaults por SO:
  - macOS: `~/Library/Application Support/CoupaDownloads`
  - Windows: `%APPDATA%/CoupaDownloads` com fallback para `%LOCALAPPDATA%`
  - Linux: `$XDG_STATE_HOME/CoupaDownloads` com fallback `~/.local/state/CoupaDownloads`
- Introduzir `sqlite_session_dir` como override opcional.
- `CSVManager` passa a criar bancos de sessão em `<application_state_dir>/sqlite/` ou no override configurado.
- Shutdown fecha handlers, mas não remove bancos persistentes criados nesse diretório.

## 3. Impactos em Interface Interna
- Novas configurações internas expostas por `Config`: `APPLICATION_STATE_DIR` e `SQLITE_SESSION_DIR`.
- `CSVManager` encapsula a política de resolução do path do SQLite.

## 4. Validação
- Testes para resolução do diretório de estado por plataforma/variável XDG.
- Testes para criação do path do SQLite em diretório persistente.
- Testes para garantir que o shutdown não apaga o banco persistente.
