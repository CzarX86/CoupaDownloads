# Relatório de Implementação: SQLite em Diretório Persistente de Estado da Aplicação

## 1. Resumo
O SQLite de sessão foi movido para um diretório persistente de estado da aplicação, separado do cache do EdgeDriver. O shutdown agora fecha handlers sem apagar os bancos persistentes gerados pelo runtime.

## 2. Entregas Realizadas
- Adição de `application_state_dir` e `sqlite_session_dir` em `AppConfig`.
- Criação do path persistente do SQLite em `CSVManager`.
- Remoção da remoção automática do banco quando ele pertence ao diretório persistente da aplicação.
- Testes unitários para resolução de path e persistência do banco.

## 3. Testes Executados
- `python3 -m py_compile src/config/app_config.py src/csv_manager.py tests/unit/test_csv_manager_sqlite_path.py`
- Execução de `pytest` não realizada neste ambiente pelos mesmos bloqueios de toolchain já identificados anteriormente.
