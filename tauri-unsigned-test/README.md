# Tauri unsigned test — assinatura com Azure Trusted Signing

O exe Tauri não assinado é bloqueado por política em máquinas corporativas
(assim como o bundle Python atual só roda porque o `pythonw.exe` é assinado
pela Python Software Foundation). A solução é assinar o exe no GitHub Actions
com **Azure Trusted Signing** (Microsoft): certificado emitido por CA pública,
sem HSM, assinatura dentro do pipeline.

## 1. Criar o recurso no Azure (admin da empresa ou você, se tiver acesso)

1. Portal Azure → criar recurso → **Trusted Signing** (Code Signing)
2. Escolher região (define o endpoint; ex.: East US → `https://eus.codesigning.azure.net`,
   West US → `https://wus.codesigning.azure.net`, UK South → `https://uks.codesigning.azure.net`)
3. Criar uma **Certificate Profile** do tipo *Public Trust* (a que o AppLocker/SmartScreen
   reconhece como publisher confiável)
4. Anotar: nome da conta, nome do profile, endpoint da região

## 2. Autorizar o GitHub Actions (OIDC — sem segredos de longa duração)

No recurso Trusted Signing → Identity → criar identidade gerenciada, e no
Enterprise App / service principal do GitHub:
- Federated credential apontando para `repo:CzarX86/CoupaPilot`
- Papel *Trusted Signing Certificate Profile Signer* na certificate profile

## 3. Segredos no GitHub (Settings → Secrets and variables → Actions)

| Secret/Var | Valor |
|---|---|
| `AZURE_CLIENT_ID` | Client ID do service principal / app registration |
| `AZURE_TENANT_ID` | Tenant da empresa |
| `AZURE_SUBSCRIPTION_ID` | Subscription do recurso |
| `TRUSTED_SIGNING_ACCOUNT` (var) | Nome da conta Trusted Signing |
| `TRUSTED_SIGNING_CERT_PROFILE` (var) | Nome da certificate profile |
| `TRUSTED_SIGNING_ENDPOINT` (var) | Endpoint regional (ex.: `https://eus.codesigning.azure.net`) |

Enquanto `AZURE_CLIENT_ID` não existir, o workflow **não assina** e mantém o
comportamento atual (verifica que o exe está sem assinatura). Quando o segredo
for adicionado, o próximo run assina e a verificação exige `Valid`.

## 4. Observação sobre AppLocker

Se a empresa usa AppLocker com regras por *publisher*, o exe assinado pode
precisar que o TI adicione o publisher ao catálogo permitido (o pythonw da PSF
já está no catálogo — por isso roda). O SmartScreen/Defender ASR, por outro
lado, libera automaticamente qualquer binário com assinatura válida e reputação
via timestamp.
