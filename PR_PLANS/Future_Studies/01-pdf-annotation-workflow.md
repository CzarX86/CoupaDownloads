# Future Study — PDF Annotation Workflow

## Objective
Investigar uma solução robusta para anotação de PDFs que permita revisão humana de entidades pré-rotuladas, visando acelerar correções e alimentar o auto-treino.

## Questions to Validate
- Qual biblioteca ou plataforma oferece melhor equilíbrio entre facilidade de uso, performance local (MacBook Air M3) e capacidade de exportar os dados para nosso pipeline?
- Precisamos de uma UI web dedicada (ex.: Label Studio, Argilla) ou um fluxo CLI enriquecido é suficiente?
- Como manter a rastreabilidade das edições (histórico, autores, versões) sem adicionar muita complexidade?

## Initial Options
- `PyMuPDF`/`fitz` + UI customizada (leve, mas demanda desenvolvimento próprio).
- `pdfplumber` para extração + `doccano` ou `label-studio` para revisão visual.
- Integração com Argilla para gerenciamento de datasets e auditoria.

## Next Steps
1. Prototipar carregamento de PDFs e pré-anotações com `PyMuPDF` ou `pdfplumber` e medir performance.
2. Avaliar a experiência de uso do Label Studio rodando localmente (Docker) no MacBook Air M3.
3. Decidir se vale um PR dedicado para implantação incremental (ex.: export/import com nosso pipeline).

## Notes
- Este estudo não faz parte do escopo da PR 22; abrir plano dedicado antes de implementar.
