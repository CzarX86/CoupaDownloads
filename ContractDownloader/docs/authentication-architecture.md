# Arquitetura de autenticação

## Objetivo

A autenticação do Contract Downloader usa Edge ou Chrome em um perfil persistente exclusivo do aplicativo. O usuário faz o login manualmente apenas quando a sessão ainda não existe ou quando o Coupa a invalida. Depois disso, o pipeline HTTP reutiliza os cookies de sessão localmente.

## Workflow

1. O app detecta Edge e Chrome instalados.
2. Em **Automatic**, escolhe o navegador padrão do sistema quando ele for Edge ou Chrome. Se o padrão for outro navegador, usa um fallback suportado sem alterar a configuração do sistema.
3. Em **Settings**, o usuário pode escolher Edge ou Chrome especificamente para o Contract Downloader. Essa preferência não altera o navegador padrão do macOS/Windows.
4. O app cria um perfil exclusivo para cada navegador usado e registra o caminho em `~/.contract_downloader/browser_profiles.json`.
5. Na primeira autenticação, se ainda não houver conta conectada ao perfil dedicado, o app abre primeiro uma Nova Guia em uma instância nativa e separada do Edge ou Chrome, sem criar o WebDriver e sem acessar o Coupa. O usuário entra pelo ícone do perfil; assim que o navegador registra a conta, o app fecha essa janela, abre o mesmo perfil pelo WebDriver e somente então navega ao Coupa para tentar concluir o acesso por SSO.
   - Senha, MFA e consentimentos permanecem sob controle do usuário; o app apenas detecta localmente que uma conta foi registrada no perfil.
   - No Edge, a conta Microsoft Entra do perfil oferece SSO sem exigir sincronização.
   - No Chrome, o login do perfil usa uma Conta Google; o SSO corporativo só será automático quando a organização também tiver configurado a extensão, Platform SSO ou integração equivalente. Caso contrário, o fallback do Coupa será usado.
   - Se a política corporativa impedir o login do Edge ou o onboarding não for concluído em 90 segundos, a tentativa termina sem abrir o Coupa. No Chrome, o login direto do Coupa permanece como fallback porque a identidade do perfil é uma Conta Google.
6. O app captura os cookies da sessão, valida o acesso no Coupa e salva somente a sessão necessária no cache local.
7. Nas próximas execuções, o cache é validado primeiro. Se estiver válido, o navegador não é aberto. Cookies renovados pelo Coupa durante a validação e os downloads substituem a versão anterior no cache. Quando for necessário renovar a sessão, o mesmo perfil dedicado é reaberto; se a sessão ou o SSO ainda estiver disponível nele, os cookies são recapturados sem exigir login.

O perfil pessoal do usuário nunca é descoberto, aberto, copiado, bloqueado ou removido. O app também não copia senhas, histórico, extensões ou o banco de cookies pessoal.

## Regras

- Edge e Chrome são suportados para autenticação.
- Cada navegador possui um perfil app-owned persistente.
- O navegador configurado em Settings é usado apenas para autenticação do Contract Downloader.
- Links externos continuam sendo abertos pelo launcher/navegador padrão do sistema operacional.
- O cache existente em `~/.contract_downloader/cookies.json` e `~/.contract_downloader/auth_cache.db` continua compatível.
- Não há TTL artificial: o Coupa decide se a sessão ainda é válida.
- A aplicação conserva renovações legítimas, mas não aumenta nem contorna o prazo definido pelo Coupa/SSO.
- O onboarding só é oferecido aos perfis dedicados do Edge e Chrome; os perfis normais do usuário continuam fora do escopo.
- Falha temporária de rede resulta em `unavailable`, não em logout automático.
- A GUI solicita o login na primeira inicialização sem sessão válida.
- O worker CLI iniciado pela GUI apenas valida o cache e não abre um segundo browser silenciosamente.
- A execução direta do CLI pode abrir o navegador configurado quando não existe uma sessão utilizável.

## Componentes

- `src/auth/models.py`: estados e resultados da sessão.
- `src/auth/cookie_store.py`: persistência e compatibilidade do cache.
- `src/auth/session_validator.py`: validação HTTP rápida contra o Coupa.
- `src/auth/browser.py`: detecção do navegador padrão, catálogo Edge/Chrome, manifesto de perfis e Selenium.
- `src/auth/service.py`: política única usada pelos fluxos GUI e CLI.
- `src/engine/authenticator.py`: facade de compatibilidade para imports antigos.

## Estados

| Estado | Significado |
|---|---|
| `valid` | O Coupa aceitou os cookies. |
| `missing` | Não existe `_coupa_session`. |
| `expired` | O Coupa redirecionou para login ou rejeitou a sessão. |
| `unavailable` | Não foi possível verificar por indisponibilidade temporária. |

A validação faz uma requisição para `/order_headers`, segue redirects e verifica o domínio final e os marcadores de autenticação. Cookies nunca são incluídos em logs ou diagnósticos.
