# Proposta de Mudança: Renovação do Cache de Login do Coupa

## 1. Identificação
- **Número da Proposta**: 27
- **Título**: Renovação do Cache de Login do Coupa
- **Data de Criação**: 4 de agosto de 2026
- **Autor**: Codex (a pedido do usuário)
- **Status**: Aprovado (correção solicitada pelo usuário)
- **Dependências**: 17-contract-downloader

## 2. Contexto e Problema
O Contract Downloader persistia o cookie capturado no login, mas descartava as renovações devolvidas pelo Coupa durante a validação e os downloads. Como a sessão do Coupa possui validade deslizante curta, uma execução posterior podia reutilizar uma versão antiga e solicitar novo login mesmo após atividade recente.

O perfil exclusivo do aplicativo também não está conectado à conta corporativa do Edge. Portanto, ele não herda o SSO contínuo do perfil normal do usuário; esta correção não acessará nem copiará o perfil pessoal.

## 3. Objetivo
- Persistir a versão mais recente da sessão devolvida pelo Coupa.
- Impedir que o cliente HTTP envie simultaneamente cookies antigo e renovado.
- Manter o perfil de autenticação isolado do perfil pessoal do navegador.

## 4. Escopo
### In Scope
- Escopo de domínio correto para cookies HTTP.
- Renovação do cache após validação bem-sucedida.
- Renovação do cache ao encerrar o crawler.
- Testes unitários para os dois pontos de renovação.

### Out of Scope
- Alterar o prazo de expiração definido pelo Coupa ou pelo provedor corporativo.
- Abrir, copiar ou controlar o perfil pessoal do Edge/Chrome.
- Automatizar credenciais, MFA ou login corporativo.

## 5. Critérios de Aceitação
- Um `Set-Cookie` válido substitui o `_coupa_session` anterior sem duplicá-lo.
- A sessão renovada pela validação é persistida em JSON e SQLite.
- A sessão renovada durante uma run é persistida ao fechar o crawler.
- Falha ao atualizar o cache no encerramento não invalida downloads concluídos.
