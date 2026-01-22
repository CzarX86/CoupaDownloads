# PR 12 — Auto‑select EdgeDriver + seamless fallback

## Objetivo
Tornar a seleção do EdgeDriver automática no fluxo do `Core_main.py`, sem prompt quando a detecção funcionar. Caso falhe, tentar download automático. Como último recurso, informar claramente o erro e orientar qual driver é necessário e onde obtê‑lo.

## Escopo
- Atualizar apenas o assistente interativo em `src/Core_main.py` (função `_interactive_setup`).
- Remover o prompt de seleção manual por lista quando houver detecção automática bem‑sucedida.
- Fallback: se a seleção automática falhar, tentar download (respeitando `DRIVER_AUTO_DOWNLOAD`).
- Último recurso: imprimir orientação (versão do Edge instalada, major requerido, link oficial) e instruções para colocar o driver em `drivers/` ou definir `EDGE_DRIVER_PATH`.
- Manter `EDGE_DRIVER_PATH` como override manual, e `DRIVER_AUTO_DOWNLOAD` (default: true) como controle para o fallback.
- Sem mudanças em `DriverManager` ou no comportamento do navegador além do fluxo do assistente.

## Arquivos afetados
- `src/Core_main.py` (apenas `_interactive_setup`):
  - Auto‑pick com `DriverManager().get_driver_path()`
  - Pular prompt de lista quando sucesso
  - Tentar download se necessário
  - Mensagens de orientação quando falhar

## Pseudodiff (representativo)

Ver commit de implementação (trecho aplicado conforme o plano).

## Critérios de aceitação
- Quando `drivers/` possui um driver compatível, o assistente NÃO solicita a lista; mostra “Auto‑selected EdgeDriver: <path>”.
- Se não há driver local compatível e `DRIVER_AUTO_DOWNLOAD=true` (default), tenta baixar; em sucesso, segue sem prompt.
- Se download falha (sem rede ou erro), imprime orientação com:
  - versão do Edge instalada, major requerido, link de download oficial,
  - instruções para colocar o binário em `drivers/` ou usar `EDGE_DRIVER_PATH`.
- `EDGE_DRIVER_PATH` continua funcionando como override manual quando definido.
- Sem regressões: fluxo restante do `_interactive_setup` permanece igual.

## Testes manuais
1) Com driver compatível em `drivers/`: rodar `poetry run python src/Core_main.py` → sem prompt de lista, mensagem de auto‑seleção.
2) Sem driver local e com rede: ensure `DRIVER_AUTO_DOWNLOAD=true` → efetua download, segue sem prompt de lista.
3) Sem driver local e sem rede: `DRIVER_AUTO_DOWNLOAD=true` → mostra orientação com versão do Edge/major e link. Se informar caminho manual válido, segue; caso contrário, abortará adiante quando o Browser tentar iniciar.
4) `DRIVER_AUTO_DOWNLOAD=false`, com driver local incompatível: mostra orientação (não tenta baixar).

## Mensagem de commit sugerida
`feat(setup): PR 12 — auto-select EdgeDriver with download fallback and clear guidance`

## Branch sugerido
`feat/12-auto-driver-selection`
