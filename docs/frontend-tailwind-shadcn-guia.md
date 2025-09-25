# Guia rápido — Tailwind CSS + shadcn/ui

Este guia resume como trabalhar com a nova base visual da SPA instalada no diretório `src/spa`. Todas as instruções estão em português, conforme política do projeto.

## Fluxo de desenvolvimento

1. **Instalação de dependências**
   ```bash
   cd src/spa
   npm install
   ```
2. **Servidor de desenvolvimento**
   ```bash
   npm run dev
   ```
   O Vite aplica Tailwind e os componentes shadcn/ui automaticamente.
3. **Build de produção**
   ```bash
   npm run build
   ```
4. **Lint do front-end**
   ```bash
   npm run lint
   ```

## Estrutura de estilos

- A folha de estilos de entrada é `src/spa/src/index.css` contendo apenas os layers do Tailwind e variáveis de tema.
- As cores principais são definidas via CSS custom properties (`--primary`, `--background`, etc.). Ajustes globais devem ser feitos neste arquivo, dentro dos blocos `@layer` apropriados.
- O Tailwind foi configurado no arquivo `tailwind.config.ts`, com `darkMode` baseado em classe e plugin `tailwindcss-animate` habilitado.

## Componentes shadcn/ui

- Os componentes básicos vivem em `src/spa/src/components/ui`. Cada arquivo segue a estrutura oficial da CLI, mas com imports relativos (`../../lib/utils`).
- Para criar novos componentes utilize os existentes como referência. Caso execute a CLI no futuro, mantenha `components.json` apontando para `tailwind.config.ts` e `src/index.css`.
- O utilitário `cn` (merge de classes) está em `src/spa/src/lib/utils.ts`.

## Boas práticas

- Prefira **composições utilitárias do Tailwind** em vez de CSS manual. Regras globais só devem ser adicionadas nos layers `@base`, `@components` ou `@utilities`.
- Centralize feedbacks visuais usando o sistema de toast (`useToast`, `Toaster`) criado em `components/ui`. Isso mantém uma experiência consistente.
- Componentes de layout (Cards, Table, Dialog) devem receber classes via `cn` quando houver lógica condicional.
- Mensagens exibidas na interface continuam em inglês; este guia e demais documentos seguem em pt-BR.

## Próximos passos sugeridos

- Avaliar se a aplicação precisa de tema escuro automático. A troca pode ser habilitada adicionando um toggler que altere a classe `dark` na `html` ou `body`.
- Mapear componentes recorrentes (ex: badges de status) e promovê-los para `components/ui` para reaproveitamento futuro.
