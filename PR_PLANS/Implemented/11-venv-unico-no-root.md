# PR 11 — Venv único no root com Poetry (fix Python 3.12.x)

## Objetivo
Consolidar o ambiente Python em um único virtualenv no root do repositório gerenciado pelo Poetry (`.venv`), removendo o `venv` local do subprojeto `embeddinggemma_feasibility`. Fixar a versão do Python na série 3.12 (3.12.latest). Sem alterações de código de aplicação — apenas configuração de ambiente.

## Escopo
- Remover o diretório `embeddinggemma_feasibility/venv` (venv por‑subprojeto).
- Usar Poetry no root para gerenciar o ambiente e dependências, com venv do projeto em `./.venv`.
- Fixar o Python em 3.12.x no `pyproject.toml` do root: `">=3.12,<3.13"`.
- Adicionar arquivo `poetry.toml` no root para garantir venv dentro do projeto (`virtualenvs.in-project = true`).
- Adicionar grupo `ml` ao `pyproject.toml` com dependências de ML do subprojeto `embeddinggemma_feasibility` (runtime), mantendo testes fora do grupo neste PR.

Contexto: há `.python-version` no root. O Poetry usará o Python definido aí quando disponível. Caso necessário, ajustar com pyenv para apontar para 3.12.x.

## Arquivos/Diretórios afetados
- Removido: `embeddinggemma_feasibility/venv/`
- Alterado: `pyproject.toml` (root) — restringir Python para `>=3.12,<3.13` e incluir `[tool.poetry.group.ml.dependencies]`.
- Adicionado: `poetry.toml` (root) — configurar `virtualenvs.in-project = true` para criar `.venv/` no root (já ignorado por `.gitignore`).
- Sem mudanças em arquivos de código de aplicação.

## Pseudodiff
Representação do que será feito (sem aplicar ainda):

```
~ embeddinggemma_feasibility/venv/                 # deletar pasta inteira
~ pyproject.toml                                   # ajustar constraint do Python + grupo ml
  [tool.poetry.dependencies]
- python = ">=3.12"
+ python = ">=3.12,<3.13"

+ [tool.poetry.group.ml.dependencies]              # novo grupo (runtime ML)
+ sentence-transformers = ">=2.2.2"
+ transformers = ">=4.35.0"
+ torch = ">=2.0.0"
+ numpy = ">=1.24.0"
+ scikit-learn = ">=1.3.0"
+ huggingface-hub = ">=0.17.0"
+ datasets = ">=2.14.0"
+ accelerate = ">=0.24.0"
+ memory-profiler = ">=0.61.0"
+ matplotlib = ">=3.7.0"
+ seaborn = ">=0.12.0"
+ plotly = ">=5.15.0"
+ pytesseract = ">=0.3.10"
+ pillow = ">=10.0.0"
+ pymupdf = ">=1.23.0"

+ poetry.toml                                      # novo (garantir venv no projeto)
+ [virtualenvs]
+ in-project = true
```

## Aceitação
- `embeddinggemma_feasibility/venv` não existe mais.
- `pyproject.toml` no root fixa Python em `>=3.12,<3.13` e contém o grupo `ml` com as deps listadas.
- `poetry.toml` presente no root com `virtualenvs.in-project = true`.
- O venv fica em `./.venv` e o Poetry reconhece: `poetry env info` aponta para `.venv`.
- `poetry env use 3.12` seleciona o Python correto e `poetry run python --version` retorna `3.12.x`.
- `poetry install --with ml` instala as dependências principais e do grupo `ml`.
- Execução básica funciona: `poetry run python MyScript/gui_main.py --help`; e libs do grupo `ml` importam (`poetry run python -c "import torch, transformers; print('ok')"`).

## Testes manuais mínimos
1) Garantir Python 3.12.x disponível com pyenv (se necessário):
   - `pyenv install 3.12.11` (ou mais recente 3.12.x)
   - `pyenv local 3.12.11`
2) Poetry venv local no projeto:
   - `poetry --version` (>=1.7 recomendado)
   - `poetry env use 3.12`
   - `poetry install`
   - `poetry env info` deve apontar para `.venv`
   - `poetry run python --version` retorna `3.12.x`
3) Execução básica:
   - `poetry run python MyScript/gui_main.py --help`
   - `poetry run python -c "import selenium; print('ok')"`
4) Instalação com grupo ML e verificação:
   - `poetry install --with ml`
   - `poetry run python -c "import torch, transformers, sentence_transformers; print('ml ok')"`

## Observações
- Este PR altera apenas configuração de ambiente (Poetry + versão do Python) e remove venv local. Não altera código.
- Unificação de dependências por grupos (`gui`, `ml`) pode ser proposta em um PR subsequente para manter o escopo enxuto aqui.
- `.gitignore` já cobre `.venv/` e `venv/`.

## Mensagem de commit sugerida
`docs(pr-plan): PR 11 — venv único no root com Poetry (Python 3.12.x)`

## Nome de branch sugerido
`plan/11-venv-unico-no-root-poetry`
