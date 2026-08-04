# Relatório de Implementação: Onboarding SSO nos Perfis Dedicados do Edge e Chrome

## 1. Resumo
O primeiro acesso dos perfis dedicados do Edge e Chrome agora prioriza a conexão da conta do navegador. Em seguida, o app abre o Coupa automaticamente para tentar a conclusão por SSO. No Edge, o Coupa não é aberto enquanto o perfil dedicado estiver sem conta; no Chrome, o login direto permanece como fallback.

## 2. Entregas Realizadas
- Detecção booleana de conta corporativa no `Default/Preferences` do perfil dedicado.
- Abertura de uma Nova Guia em processo nativo e separado do Edge ou Chrome quando o perfil está sem conta.
- Configuração da conta corporativa antes da criação do WebDriver e antes de qualquer navegação ao Coupa.
- Instrução para entrar pelo ícone do perfil, evitando a janela branca do broker de identidade no macOS.
- Abertura automática do mesmo perfil pelo WebDriver após a autorização.
- Recuperação automática, no macOS, de árvores EdgeDriver/Edge órfãs que ainda estejam bloqueando exclusivamente o perfil dedicado do aplicativo.
- Navegação automática ao Coupa após o registro da conta.
- Prazo de onboarding reduzido para 90 segundos.
- Bloqueio do fallback direto no Edge enquanto o perfil estiver desconectado; fallback mantido apenas no Chrome.
- Mensagens de progresso integradas ao estado de autenticação existente.

## 3. Segurança e Limites
- O app não preenche credenciais, não interage com MFA e não ativa sincronização.
- Nenhuma informação da conta é incluída em logs.
- Os perfis normais do Edge e Chrome não são abertos, copiados ou inspecionados.
- Políticas corporativas continuam soberanas; se impedirem login no Edge, a tentativa termina sem abrir o Coupa.
- No Chrome, o SSO depende da integração corporativa disponível no dispositivo; o app não instala extensões nem altera políticas.

## 4. Testes Executados
- `46 passed` na suíte focada de navegador, autenticação, cache, validação e crawler após as correções do onboarding nativo e da recuperação de processo órfão.
- Suíte completa: `194 passed`; 19 E2E bloqueados pelo sandbox ao abrir porta local e 1 falha preexistente fora do escopo em reparo de CSV.
- `py_compile` dos módulos de autenticação e execução sem erros.
- `git diff --check` sem erros.

## 5. Build macOS
- Build recriado com `uv run --group build python build.py --macos`.
- Aplicativo sincronizado em `ContractDownloader/ContractDownloader.app` e `ContractDownloader/dist/ContractDownloader.app`.
- Assinatura ad-hoc validada com `codesign --verify --deep --strict`.
- Executável validado como Mach-O `arm64`.
- Módulos `src.auth.browser`, `src.auth.cookie_store`, `src.auth.service` e `src.auth.session_validator` confirmados no pacote gerado.
