# Documento de Design: Renovação do Cache de Login do Coupa

## 1. Contexto
Os clientes `httpx` recebiam cookies como um dicionário sem domínio. Quando o Coupa renovava `_coupa_session`, o cookie novo era adicionado com domínio e o antigo permanecia no jar. Além disso, o estado atualizado do jar não era gravado pelo serviço de autenticação nem pelo crawler.

## 2. Decisão Técnica
- Criar o jar inicial com domínio e path correspondentes ao host do Coupa, permitindo substituição correta por `Set-Cookie`.
- Fazer `SessionValidator` devolver o jar resultante da requisição.
- Fazer `AuthService.check()` persistir uma sessão validada.
- Injetar o `CookieStore` existente no `CoupaCrawler` e salvar o jar no encerramento.
- Preservar o isolamento do perfil do navegador; nenhuma leitura do perfil pessoal será adicionada.

## 3. Limites
A aplicação conserva a renovação concedida pelo servidor, mas não aumenta artificialmente a validade da sessão. Depois de inatividade superior à política corporativa, o Coupa ou o SSO ainda pode exigir autenticação. Conectar voluntariamente o perfil exclusivo do aplicativo à conta corporativa pode reduzir essa recorrência sem expor o perfil pessoal.

## 4. ADR
Não foi criado ADR: a correção mantém a arquitetura de autenticação e persistência já aprovada, apenas completa o ciclo de renovação do cookie.

## 5. Validação
- Teste da substituição e devolução do cookie renovado pelo validador.
- Teste da persistência da sessão validada pelo serviço.
- Teste da persistência da sessão renovada ao fechar o crawler.
- Regressão dos testes existentes de autenticação, cache e crawler.
