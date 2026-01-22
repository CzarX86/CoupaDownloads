# Future Study — Prompt Evolution Flow

## Objective
Explorar uma rotina dedicada para avaliação automática de prompts via LLM, gerando sugestões e diffs lado a lado antes da aprovação humana.

## Questions to Validate
- Qual provedor (DeepSeek, OpenAI, outros) entrega o melhor equilíbrio entre custo e qualidade para reescrita de prompts?
- Como exibir diffs de maneira clara no terminal ou em UI leve, reduzindo risco de aplicar mudanças ruins?
- Histórico e versionamento: precisamos armazenar cada iteração dos prompts? Em qual formato?

## Initial Ideas
- Script `tools/prompt_refiner.py` chamando LLMs, salvando sugestões e diffs (ex.: `difflib`, `rich`).
- Integração com o CLI gamificado para aceitar/rejeitar mudanças rapidamente.
- Documentar guidelines de escrita de prompts e critérios de aprovação humana.

## Next Steps
1. Levantar prompts existentes e categorizar por uso (treinamento, inferência, automações).
2. Prototipar avaliação usando DeepSeek por padrão e fallback para OpenAI.
3. Testar visualização de diffs (terminal vs. HTML/Markdown) e medir a experiência.

## Notes
- Abrir plano/PR separado antes de implementar; não faz parte do escopo da PR 22 atual.
