# Documento de Design: Onboarding SSO nos Perfis Dedicados do Edge e Chrome

## 1. Contexto
Os perfis dedicados já são persistentes. O arquivo `Default/Preferences` registra contas conectadas em `account_info`; basta observar a presença dessa estrutura, sem ler ou expor seus valores. No Edge, a identidade Microsoft Entra oferece SSO diretamente. No Chrome, o perfil é associado a uma Conta Google e o SSO corporativo depende da configuração da organização.

## 2. Decisão Técnica
- Se o modo for visível e `account_info` estiver vazio, abrir primeiro uma Nova Guia em um processo nativo e separado do Edge ou Chrome, sem iniciar o WebDriver nem navegar ao Coupa. O usuário entra pelo ícone do perfil, permitindo que o broker de identidade do sistema renderize a autorização corporativa.
- Aguardar no máximo 90 segundos pela presença de uma conta no perfil dedicado.
- Ao detectar a conta, encerrar apenas o processo nativo do perfil dedicado, abrir o mesmo perfil pelo WebDriver e navegar pela primeira vez para `/order_headers`; o SSO corporativo decide se o acesso pode ser concluído.
- Se `account_info` já existir, pular o onboarding e abrir diretamente o Coupa pelo perfil dedicado.
- Se o prazo acabar no Edge, encerrar a tentativa sem abrir o Coupa. No Chrome, manter o login direto existente como fallback porque o perfil exige uma Conta Google que pode não representar a identidade Microsoft corporativa.

## 3. Segurança
- A automação não interage com campos de credenciais nem com MFA.
- A detecção retorna apenas um booleano e não registra e-mail, identificador ou token.
- O perfil pessoal permanece inacessível.
- Sincronização não é exigida para o onboarding.

## 4. ADR
Não foi criado ADR separado: a mudança estende o fluxo do perfil app-owned definido na arquitetura de autenticação, sem alterar seus limites de privacidade.

## 5. Validação
- Teste do onboarding Edge seguido de navegação automática ao Coupa.
- Teste do onboarding Chrome seguido de navegação automática ao Coupa.
- Teste de que a configuração de conta é aberta fora do WebDriver nos dois navegadores.
- Teste de ordem garantindo que o processo nativo do perfil é iniciado antes do WebDriver.
- Teste de bloqueio do fallback direto no Edge e teste de manutenção do fallback no Chrome.
- Teste de conclusão silenciosa por SSO sem abrir a configuração do perfil.
- Regressão completa de autenticação, cache e crawler.
