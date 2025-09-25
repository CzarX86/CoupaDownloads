# Relatório de Implementação: PR 47 — Frontend - Exibir Entidades Pré-processadas no PDF

**Proposta Original**: [PR 47 — Frontend - Exibir Entidades Pré-processadas no PDF](./47-frontend-display-preprocessed-entities-proposta.md)
**Documento de Design**: [Arquitetura 47 — Frontend - Exibir Entidades Pré-processadas no PDF](./47-frontend-display-preprocessed-entities-design-doc.md)

## Resumo da Entrega

Implementamos a camada de visualização das entidades pré-processadas diretamente no `PdfViewer`. O componente passou a buscar os dados pelo cliente `fetchEntities`, mapear as coordenadas retornadas pelo backend e desenhar overlays clicáveis sobre o PDF, atendendo aos critérios do design aprovado.

## Artefatos Produzidos ou Modificados

- **Código Fonte**:
  - `src/spa/src/api/pdfTraining.ts`
  - `src/spa/src/components/PdfViewer.tsx`
  - `src/spa/src/models.ts`
- **Documentação**:
  - `PR_PLANS/Implemented/47-frontend-display-preprocessed-entities-proposta.md`
  - `PR_PLANS/Implemented/47-frontend-display-preprocessed-entities-design-doc.md`
- **Testes**:
  - `tests/server/pdf_training_app/test_api.py`
  - `tests/server/pdf_training_app/test_services.py`

## Evidências de Execução

- `poetry run pytest tests/server/pdf_training_app/test_api.py tests/server/pdf_training_app/test_services.py`

## Decisões Técnicas Finais

- Normalizamos a conversão de bounding boxes aceitando coordenadas absolutas ou percentuais, garantindo compatibilidade com diferentes saídas do backend.
- Os overlays são renderizados como divs posicionados acima do canvas do PDF para facilitar tooltips e interações futuras.

## Pendências e Próximos Passos

- Avaliar, em iterações futuras, a inclusão de tooltips ricos ou painel lateral para listar entidades de forma complementar.
