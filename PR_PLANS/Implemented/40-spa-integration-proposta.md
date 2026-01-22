# PR 40 — Integração de SPA para o Pipeline de Treinamento (spa-integration)

- Status: Concluído
- Implementação: PR #40
- Data: 2025-09-20 (Data de referência da implementação)
- Responsáveis: Gemini (Developer)
- Observações: Proposta para a criação de uma interface web local (SPA) para gerenciar o ciclo de vida do treinamento de modelos de PDF.

## Objetivo

Criar uma interface de usuário web local (Single Page Application) que abstrai a complexidade da linha de comando e guia o usuário através do fluxo de trabalho de treinamento de modelos de extração de dados de PDF. A meta é fornecer uma experiência visual e intuitiva, similar a ferramentas "AI Builder", para as etapas de upload, análise, revisão e retreinamento.

## Escopo

- **Frontend**: Desenvolver uma SPA em React + Vite.
- **Backend**: Implementar um gateway de API com FastAPI para servir a SPA e orquestrar as operações.
- **Fluxo de Trabalho**: A UI deve suportar as seguintes etapas:
    1.  **Upload**: Permitir o upload de novos documentos PDF.
    2.  **Análise**: Disparar a extração automática de dados dos PDFs.
    3.  **Revisão**: Facilitar a revisão das extrações, gerando os artefatos necessários para o Label Studio e ingerindo as anotações corrigidas.
    4.  **Treinamento**: Iniciar um novo ciclo de treinamento do modelo com base nos dados revisados.
- **Persistência**: Utilizar o banco de dados da aplicação para gerenciar o estado dos documentos, execuções de treinamento, métricas e versões de modelos.

**Fora do escopo:**

- Implantação pública da aplicação.
- Sistemas de filas de jobs complexos (a versão inicial pode usar execuções síncronas ou polling simples).
- Autenticação de múltiplos usuários (a ferramenta é de uso local).

## Critérios de aceitação

1.  O usuário consegue fazer o upload de um ou mais arquivos PDF através da interface.
2.  A interface exibe uma lista de documentos e seus status (ex: "Novo", "Analisado", "Em Revisão").
3.  A partir da UI, o usuário pode iniciar a análise automática de um documento e acompanhar seu progresso.
4.  A UI gera os arquivos `config.xml` e `tasks.json` para o Label Studio e permite a ingestão do JSON exportado com as anotações.
5.  O usuário pode disparar uma nova execução de treinamento a partir da interface.
6.  A UI exibe um histórico de execuções de treinamento, incluindo status e métricas de performance.
7.  A documentação (`USER_GUIDE.md`) é atualizada com instruções sobre como iniciar e usar a nova SPA.