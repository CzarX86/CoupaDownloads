# Design Doc: Conversão de Arquivos .msg para PDF ao Final do Processo

## 1. Resumo
Adicionar uma etapa pós-processamento que converte todos os `.msg` baixados em PDFs. A conversão é oferecida ao usuário (default Sim) em execuções interativas e executada automaticamente em execuções não interativas. Os PDFs ficam ao lado dos arquivos originais.

## 2. Requisitos Funcionais
- Detectar `.msg` recursivamente no diretório de downloads configurado.
- Converter cada `.msg` para PDF com cabeçalho (From, To, Cc, Date, Subject) e corpo em texto plano (fallback de HTML simplificado).
- Manter arquivos originais; pular arquivos já convertidos, salvo `MSG_TO_PDF_OVERWRITE=true`.
- Não bloquear shutdown se algum arquivo falhar; registrar resumo em telemetria/console.
- Configurável via flags: `MSG_TO_PDF_ENABLED` (default true) e `MSG_TO_PDF_OVERWRITE` (default false).

## 3. Requisitos Não Funcionais
- Bibliotecas leves e puramente Python (`extract-msg`, `fpdf2`) para compatibilidade com empacotamento.
- Execução linear após o processamento (sem alterar fluxo de downloads/CSV).
- Mensagens ao usuário em inglês; documentação em pt-BR.

## 4. Arquitetura e Fluxo
1. **Config**: novas flags em `ExperimentalSettings`/`Config` com leitura de env e propagação via `SetupManager`.
2. **Serviço**: novo módulo `src/services/msg_conversion_service.py` contendo:
   - `find_msg_files(download_root: Path) -> list[Path]`
   - `MsgToPdfConverter.convert(msg_path: Path, overwrite: bool) -> ConversionResult`
   - `convert_all(msg_files, overwrite, telemetry=None) -> dict`
3. **Integração**: em `MainApp.run()`, após emitir estatísticas finais e antes de `_offer_final_report`, chamar `_offer_msg_conversion()`:
   - Se `MSG_TO_PDF_ENABLED` for falso ou não houver `.msg`, apenas logar.
   - Interativo: prompt “Convert <N> .msg files to PDF now? [Y/n]” (default Yes).
   - Não interativo: converter automaticamente.
   - Resumo impresso e emitido em telemetria (`StatusLevel.INFO/WARNING`).

## 5. Modelo de Dados
`ConversionResult` (dataclass simples):
- `source: Path`
- `target: Path`
- `status: Literal['converted','skipped','failed']`
- `error: Optional[str]`

## 6. Tratamento de Erros
- `extract_msg` pode lançar parsing errors: capturar por arquivo, marcar `failed`, continuar.
- Se `fpdf` falhar na escrita, registrar erro e seguir.
- Tempo de conversão não interrompe `close()`; exceções não propagam para `MainApp`.

## 7. Testes
- Unitário `tests/unit/test_msg_conversion.py`:
  - Mock de `extract_msg.Message` para não depender de binários `.msg`.
  - Verifica criação de PDF e conteúdo básico (Subject/Body).
  - Verifica skip quando PDF já existe e overwrite desativado.
- Smoke manual: execução curta do `MainApp` para validar prompt e resumo.

## 8. Implantação
- Atualizar `pyproject.toml` e `poetry.lock` com novas dependências.
- Sem mudanças em APIs públicas; sem migrações.

## 9. Riscos e Mitigações
- **Peso das libs**: ambas são puras em Python; avaliar tempo de lock; se necessário, fixar versões mínimas.
- **Conteúdo HTML complexo**: fallback simples com strip de tags; aceitável para uso principal (visualização rápida).
- **CI headless**: conversão roda sem UI; manter logs curtos.

