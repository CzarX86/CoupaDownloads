# Proposta de Mudança: Conversão de Arquivos .msg para PDF ao Final do Processo

## 1. Identificação
- **Número da Proposta**: 07
- **Título**: Conversão de .msg para .pdf pós-download
- **Data de Criação**: 4 de março de 2026
- **Autor**: Codex
- **Status**: Em Revisão
- **Dependências**: Nenhuma dependência lógica de PRs anteriores; requer instalação das novas libs `extract-msg` e `fpdf2`.

## 2. Contexto e Problema
Usuários recebem anexos Coupa em formato Outlook `.msg`, que dificultam visualização rápida e compartilhamento. Hoje o fluxo encerra após o download, sem oferecer conversão. Em ambientes não interativos (CI), não há mecanismo para gerar PDFs automaticamente.

## 3. Objetivo
Oferecer, ao final do processamento, a conversão de todos os arquivos `.msg` encontrados no diretório de download para `.pdf`, mantendo os originais. Em modo interativo, perguntar ao usuário (default = Sim); em modo não interativo, converter automaticamente.

## 4. Escopo
- **Incluso**:
  - Scanner de `.msg` no diretório raiz de downloads (recursivo).
  - Conversor `.msg` → `.pdf` com cabeçalho (remetente, destinatários, assunto, data) e corpo do e-mail.
  - Flags de configuração `MSG_TO_PDF_ENABLED` e `MSG_TO_PDF_OVERWRITE`.
  - Integração no fluxo `MainApp.run()` após finalização das POs e antes do relatório final.
  - Testes unitários cobrindo conversão e comportamento de sobrescrita.
- **Fora de escopo**:
  - Conversão/extração de anexos internos do `.msg`.
  - Alterações em CSV/relatórios existentes.

## 5. Critérios de Aceitação
- Prompt exibido em execução interativa quando existirem `.msg`; padrão confirma conversão.
- Em execução não interativa, `.msg` são convertidos automaticamente sem bloquear shutdown, mesmo em caso de falhas pontuais.
- PDFs são gravados no mesmo diretório do `.msg`; arquivos existentes não são sobrescritos por padrão.
- Configurações podem ser controladas via variáveis de ambiente.
- Teste unitário de conversão cria PDF válido e verifica comportamento de pular quando já existe PDF.

## 6. Riscos e Mitigações
- **Falha de parsing de `.msg`**: isolar exceção por arquivo e continuar; logar em telemetria.
- **Dependências novas**: usar libs puras em Python (`extract-msg`, `fpdf2`) para facilitar empacotamento.
- **Tempo adicional em lotes grandes**: conversão roda apenas ao final; permitir desligar via flag.

## 7. Plano de Validação
- Executar `poetry run pytest tests/unit/test_msg_conversion.py`.
- Smoke curto `poetry run python -m src.main` com uma pasta contendo `.msg` e verificar prompt/conversão.

