# Contract Downloader — instruções rápidas

## 1. Baixar e extrair

1. Baixe o arquivo ZIP enviado pela equipe.
2. Extraia **todo o conteúdo** do ZIP. Não execute o aplicativo de dentro do ZIP.
3. Se o Windows informar **Erro 0x80010135: caminho muito longo**, extraia em uma pasta curta, por exemplo:

   `C:\ContractDownloader`

Não renomeie nem remova as pastas `runtime` e `app`.

## 2. Iniciar o aplicativo

Abra duas vezes o arquivo:

`Start-ContractDownloader.cmd`

Não é necessário instalar Python, instalar bibliotecas ou executar como administrador.

Na primeira abertura, o Windows pode demorar alguns segundos para preparar o aplicativo.

## 3. Fazer o login

Quando solicitado:

1. Conclua o login do Coupa na janela do Edge.
2. Retorne ao Contract Downloader.
3. Aguarde a confirmação da sessão.

## 4. Executar uma lista de POs

1. Escolha o arquivo Excel ou CSV de input.
2. Valide o arquivo.
3. Escolha a estrutura de pastas.
4. Escolha a pasta de destino.
5. Revise as informações e clique em **Start download**.

O arquivo original de input é preservado durante a execução.

## 5. Corrigir uma PO com erro

1. Abra **Run History**.
2. Abra os detalhes da execução.
3. Clique em **Retry** na PO com erro.
4. Corrija o número da PO e confirme.
5. Se o retry funcionar, escolha **Save correction** para atualizar o input e o relatório.
6. Escolha **Discard retry** somente se não quiser manter os arquivos baixados nem a correção.

## 6. Se o aplicativo não abrir

1. Verifique o arquivo `startup.log` na pasta do aplicativo.
2. Execute `ContractDownloader-Diagnostics.cmd`.
3. Envie o conteúdo de `startup.log` e o relatório de diagnóstico para a equipe de suporte.

Não apague `runtime`, `app` ou os arquivos `.cmd`.

## 7. Arquivos importantes

- `Start-ContractDownloader.cmd`: inicia o aplicativo.
- `ContractDownloader-Diagnostics.cmd`: gera um diagnóstico do ambiente.
- `startup.log`: registra problemas de inicialização.
- `runtime`: Python portátil usado pelo aplicativo.
- `app`: arquivos do Contract Downloader.

Downloads, autenticação, histórico e configurações são armazenados fora da pasta do aplicativo.
