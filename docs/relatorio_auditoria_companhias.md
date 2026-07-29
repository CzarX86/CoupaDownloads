# Relatório Final de Auditoria e Preenchimento de Acesso a Companhias (Coupa Access Request)

Este relatório consolida a auditoria final e o preenchimento de todos os **131 códigos de companhia** fornecidos pelo usuário no formulário de solicitação de acesso do Coupa.

---

## 📊 Resumo Executivo

*   **Total de Códigos Analisados:** 131
*   **Códigos Ativados com Sucesso (em ambos os campos):** 113
*   **Códigos Inexistentes no Banco de Dados Unilever:** 18
*   **Campos de Controle Atualizados:**
    *   **Tipo de usuário:** *Usuarios que requieren acceso a las requisiciones fuera de su codigo de compania* (Confirmado e Ativo)
    *   **Comentário (Justificativa em Inglês):** Preenchido com sucesso

---

## 🟢 1. Companhias Totalmente Ativas e Preenchidas (113)

Estes códigos foram adicionados tanto em **Content Groups** quanto em **Account Groups** no formulário. A lista abaixo foi integralmente preenchida e está pronta para submissão:

`5064`, `5103`, `1295`, `4457`, `5262`, `4216`, `6236`, `9691`, `4707`, `5281`, `4180`, `5730`, `5572`, `5455`, `5336`, `6237`, `5496`, `2491`, `2622`, `5055`, `9532`, `3144`, `5401`, `5400`, `5435`, `5707`, `4418`, `6271`, `2530`, `9695`, `6049`, `9540`, `6255`, `5111`, `6272`, `4337`, `6047`, `6230`, `6254`, `5487`, `6286`, `6270`, `6268`, `6114`, `6043`, `6274`, `6229`, `5810`, `6269`, `5222`, `6228`, `6251`, `2540`, `5802`, `6225`, `6267`, `9424`, `6288`, `6226`, `6266`, `5568`, `6221`, `6072`, `7122`, `6082`, `6252`, `4052`, `2488`, `2247`, `2259`, `3006`, `2465`, `5551`, `4544`, `5117`, `2862`, `2200`, `2611`, `3009`, `1926`, `2236`, `4450`, `1747`, `1682`, `9311`, `1714`, `2441`, `4274`, `2248`, `1890`, `5069`, `4340`, `1728`, `2432`, `2539`, `2640`, `1525`, `1524`, `6194`, `5312`, `2646`, `5322`, `2687`, `2307`, `9370`, `2378`, `5061`, `2406`, `5495`, `1388`, `4137`, `2258`, `1889`

*(Nenhuma opção MRP foi injetada em conformidade com as restrições).*

---

## 🔴 2. Códigos Inexistentes no Sistema Unilever (18)

Estes 18 códigos não retornaram nenhuma correspondência ao serem pesquisados diretamente na API de autocompletar do Coupa da Unilever, indicando que não existem na base ativa ou estão temporariamente inoperantes para este tipo de requisição:

```text
1609, 1610, 1794, 1796, 2555, 2592, 3128, 4649, 5090, 5353, 5364, 5394, 5395, 5396, 5176, 6006, 6298, 9708
```

---

## 📝 3. Justificativa Preenchida no Campo Comentário

O seguinte texto padrão e altamente profissional foi preenchido no campo de comentário obrigatório (em inglês):

> *"Please grant standard access to the requested company codes in both Content Groups and Account Groups. This access is required to support standard procurement operations, requisition creation, and order/receipt processing across these business units to ensure transaction continuity and efficiency."*

---

## 🏁 4. Estado de Conclusão do Formulário

*   **Campos de Autocomplete:** Todos os 113 códigos válidos adicionados.
*   **Seleção de Tipo de Usuário:** Atualizado para *"Usuarios que requieren acceso a las requisiciones fuera de su codigo de compania"*.
*   **Comentário Obrigatório:** Preenchido.
*   **Anexos / Outros Campos:** Sem necessidade de alteração ou preenchimento de checkboxes adicionais detectados.

O formulário está **pronto para ser enviado**! O usuário pode realizar a verificação final na tela e clicar no botão **"Review"** na parte inferior da página para concluir a operação.
