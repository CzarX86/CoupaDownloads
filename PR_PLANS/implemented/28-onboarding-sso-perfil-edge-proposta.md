# Proposta de Mudança: Onboarding SSO nos Perfis Dedicados do Edge e Chrome

## 1. Identificação
- **Número da Proposta**: 28
- **Título**: Onboarding SSO nos Perfis Dedicados do Edge e Chrome
- **Data de Criação**: 4 de agosto de 2026
- **Autor**: Codex (a pedido do usuário)
- **Status**: Aprovado (execução solicitada pelo usuário)
- **Dependências**: 27-renovacao-cache-login-coupa

## 2. Contexto e Problema
O navegador normal possui uma conta corporativa ou integração de SSO e conclui o acesso ao Coupa com pouca intervenção. Os perfis exclusivos do Contract Downloader preservam cookies, mas ainda não possuem essa identidade; após a expiração definida pelo Coupa, o usuário precisa repetir o login direto no site.

## 3. Objetivo
- Fazer o primeiro acesso priorizar a conexão da conta ao perfil dedicado do Edge ou Chrome.
- Navegar automaticamente ao Coupa após o Edge registrar a conta.
- No Edge, impedir o login direto do Coupa enquanto o perfil dedicado ainda não estiver conectado.
- No Chrome, preservar login direto no Coupa como fallback quando não houver uma identidade de perfil compatível.

## 4. Escopo
### In Scope
- Detectar apenas a presença de `account_info` no perfil dedicado.
- Abrir a tela nativa do perfil no Edge ou Chrome quando não houver conta.
- Retornar automaticamente ao Coupa para SSO.
- Limitar o onboarding a 90 segundos; no Edge, encerrar a tentativa sem abrir o Coupa quando o perfil não for conectado.

### Out of Scope
- Ler ou copiar o perfil normal do Edge.
- Preencher credenciais, responder MFA ou aceitar consentimentos.
- Ativar sincronização de favoritos, senhas, histórico ou outros dados.
- Contornar políticas corporativas de login/SSO.

## 5. Critérios de Aceitação
- Perfil Edge ou Chrome sem conta recebe a tela nativa de login do navegador.
- Depois da conexão da conta, o Coupa é aberto automaticamente.
- Perfil já conectado continua direto para o Coupa.
- Onboarding Edge não concluído retorna erro sem abrir o Coupa; no Chrome, retorna ao fluxo de login do Coupa.
- Modo headless mantém o comportamento anterior.
