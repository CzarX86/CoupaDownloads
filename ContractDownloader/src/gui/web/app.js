document.addEventListener("DOMContentLoaded", () => {
    const $ = (selector) => document.querySelector(selector);
    const screens = { new: $("#screen-new"), progress: $("#screen-progress"), history: $("#screen-history"), learn: $("#screen-learn"), settings: $("#screen-settings") };
    const navButtons = { new: $("#btn-new"), progress: $("#btn-progress"), history: $("#btn-history"), learn: $("#btn-learn"), settings: $("#btn-settings") };

    let selectedFilePath = null;
    let generatedTemplatePath = null;
    let importedSessionId = null;
    let activePollInterval = null;
    let fileMonitorInterval = null;
    let validatedFingerprint = null;
    let selectedFileValidated = false;
    let hierarchyOrder = [];
    let disabledHierarchyColumns = [];
    let hierarchyColumnsLoaded = false;
    let mappingColumns = [];
    let mappingProbeToken = 0;
    let mappingDetected = null;
    let mappingSuggestions = { po: [], supplier: [] };
    let validationCopyValues = new Map();
    let validationCopyId = 0;
    let hierarchySorter = null;
    let runInProgress = false;
    let startRequestActive = false;
    let pendingUpdate = null;
    let appSettings = { download_root: "", concurrency: 4, retry_attempts: 1, msg_processing: "convert_extract", deduplicate_files: true, auto_updates: true, retention: "all", auth_browser: "auto", language: "en", font_scale: 1.1, python_portable: false };
    let journeyStep = 1;
    let journeyMaxStep = 1;
    const journeyContent = {
        en: {
            1: ["Choose your input", "Start with a completed CSV or Excel file, or create a new template."],
            2: ["Validate your input", "Check the file before configuring the download."],
            3: ["Arrange folder hierarchy", "Choose the order used to create destination folders."],
            4: ["Confirm structure and destination", "Review the folder tree, then choose where the run saves files."],
            5: ["Review and start", "Confirm the settings, then start the download."],
        },
        "pt-BR": {
            1: ["Escolha o input", "Comece com um arquivo CSV ou Excel preenchido, ou crie um novo template."],
            2: ["Valide o input", "Verifique o arquivo antes de configurar o download."],
            3: ["Organize a hierarquia", "Escolha a ordem usada para criar as pastas de destino."],
            4: ["Confirme a estrutura e o destino", "Revise a árvore de pastas e escolha onde a execução salvará os arquivos."],
            5: ["Revise e inicie", "Confirme as configurações e inicie o download."],
        },
    };

    function getJourneyCopy(step) {
        const numericStep = Number(step);
        const languageCopy = journeyContent[appSettings.language] || journeyContent.en;
        return languageCopy[numericStep] || journeyContent.en[numericStep] || journeyContent.en[1];
    }

    const api = () => window.pywebview && window.pywebview.api ? window.pywebview.api : null;
    const hasApi = (name) => Boolean(api() && typeof api()[name] === "function");

    function syncUpdateButton() {
        const button = $("#btn-download-update");
        if (!button) return;
        button.disabled = runInProgress || !pendingUpdate;
        button.title = runInProgress ? "Updates are disabled while a run is executing." : "Download and install update";
    }

    function escapeHtml(value) {
        return String(value ?? "").replace(/[&<>'"]/g, (char) => ({
            "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;"
        }[char]));
    }

    const uiCopy = {
        en: { newRun: "New run", activeRun: "Active run", history: "Run history", learn: "Learn", settings: "Settings", prepare: "Prepare a new run", validate: "Validate input", createTemplate: "Create template", chooseFile: "Choose input file", openInput: "Open",  continueValidation: "Continue to validation", continueFolders: "Continue to folders", continueDestination: "Continue to destination", reviewRun: "Review run", start: "Start download", back: "Back", chooseFolder: "Choose folder", saveSettings: "Save settings", resetDefaults: "Reset defaults" },
        "pt-BR": { newRun: "Nova execução", activeRun: "Execução ativa", history: "Histórico", learn: "Aprenda", settings: "Configurações", prepare: "Prepare uma nova execução", validate: "Validar input", createTemplate: "Criar template", chooseFile: "Escolher arquivo de input", openInput: "Abrir",  continueValidation: "Continuar para validação", continueFolders: "Continuar para pastas", continueDestination: "Continuar para destino", reviewRun: "Revisar execução", start: "Iniciar download", back: "Voltar", chooseFolder: "Escolher pasta", saveSettings: "Salvar configurações", resetDefaults: "Restaurar padrões" },
    };

    function t(key, fallback = key) {
        return (uiCopy[appSettings.language] || uiCopy.en)[key] || fallback;
    }

    function applyFontScale(value = appSettings.font_scale) {
        const scale = Math.max(1, Math.min(1.3, Number(value) || 1.1));
        appSettings.font_scale = scale;
        document.documentElement.style.setProperty("--font-scale", String(scale));
    }

    function applyLanguage() {
        const selectors = { "#btn-new": "newRun", "#btn-progress": "activeRun", "#btn-history": "history", "#btn-learn": "learn", "#btn-settings": "settings", "#btn-download-template": "createTemplate", "#btn-browse": "chooseFile", "#btn-open-selected-input": "openInput",  "#btn-next-input": "continueValidation", "#btn-next-hierarchy": "continueFolders", "#btn-next-destination": "continueDestination", "#btn-next-review": "reviewRun", "#btn-start-run": "start", "#btn-start-over": "startOver", "#btn-validate-file": "validate", "#btn-choose-dir": "chooseFolder", "#btn-save-settings": "saveSettings", "#btn-reset-settings": "resetDefaults" };
        Object.entries(selectors).forEach(([selector, key]) => { const element = $(selector); if (element) element.innerText = t(key); });
        const content = getJourneyCopy(journeyStep);
        $("#journey-title").innerText = content[0];
        $("#journey-subtitle").innerText = content[1];
        document.querySelectorAll("[data-journey-step] span").forEach((element, index) => { element.innerText = (appSettings.language === "pt-BR" ? ["Input", "Validar", "Pastas", "Destino", "Iniciar"] : ["Input", "Validate", "Folders", "Destination", "Start"])[index]; });
        document.querySelectorAll(".learn-card h3").forEach((element, index) => { element.innerText = (appSettings.language === "pt-BR" ? ["Prepare o input", "Siga a jornada", "O que acontece durante uma execução?", "Erros e retries", "Histórico e relatórios", "Autenticação e privacidade"] : ["Prepare the input", "Follow the journey", "What happens during a run?", "Errors and retries", "History and reports", "Authentication and privacy"])[index]; });
        const learnParagraphs = appSettings.language === "pt-BR" ? ["Use um arquivo Excel ou CSV com PO_NUMBER e SUPPLIER. O template inclui o separador <|>. Salve e feche o Excel antes de validar.", "A jornada possui cinco etapas: input, validação, pastas, destino e revisão. A execução só é criada após a confirmação final.", "O app usa requisições HTTP autenticadas para o Coupa, lê páginas de PO e PR, encontra anexos e os salva na pasta da execução.", "Abra Active Run para acompanhar o progresso e os logs. Retries automáticos podem ser configurados em Settings, e POs com erro também podem ser refeitos pelo histórico.", "O histórico armazena resultados por PO, retries, inputs preservados, relatórios e links para o Coupa. É possível excluir uma execução ou todo o histórico.", "A autenticação usa um perfil separado do aplicativo e reutiliza a sessão em cache até o Coupa invalidá-la. Links externos seguem o navegador padrão do sistema e o app não envia telemetria." ] : ["Use an Excel or CSV file with PO_NUMBER and SUPPLIER. The template includes the <|> separator. Save and close Excel before validating.", "The journey has five stages: input, validation, folders, destination, and review. A run is created only after final confirmation.", "The app uses authenticated HTTP requests to Coupa, reads PO and PR pages, discovers attachments, and saves them inside the run folder.", "Open Active Run to monitor progress and logs. Automatic retries can be configured in Settings, and failed POs can also be retried manually from History.", "History stores PO-level results, retry history, preserved inputs, reports, and Coupa links. You can delete one run or clear all history.", "Authentication uses a separate app profile and reuses the cached session until Coupa invalidates it. External links follow the operating system default browser and the app does not send telemetry."];
        document.querySelectorAll(".learn-card p").forEach((element, index) => { element.innerText = learnParagraphs[index]; });
        const learnNotes = appSettings.language === "pt-BR" ? ["Colunas após <|> viram níveis de pasta. Campos obrigatórios vazios são informados antes do download.", "Etapas concluídas continuam disponíveis; etapas futuras explicam o que ainda falta.", "Downloads simultâneos são limitados a 8, com backoff adaptativo quando o Coupa aplica rate limit.", "O retry usa a mesma pasta e preserva arquivos válidos existentes.", "Excluir uma execução remove sua pasta; inputs originais fora dela são preservados.", "Telemetria não é enviada. Cookies, credenciais e documentos permanecem na máquina local."] : ["Columns after <|> become folder levels. Blank required fields are reported before downloading.", "Completed steps remain available; future steps explain what is still missing.", "Downloads simultaneous is capped at 8, with adaptive backoff when Coupa rate-limits requests.", "A retry uses the same folder and preserves valid existing files.", "Deleting a run removes its folder; original inputs outside it are preserved.", "No telemetry is sent. Cookies, credentials, and documents remain on the local machine."];
        document.querySelectorAll(".learn-note").forEach((element, index) => { element.innerText = learnNotes[index]; });
        const settingsHeadings = appSettings.language === "pt-BR" ? ["Idioma", "Tamanho do texto", "Downloads", "Downloads simultâneos", "Política de retry", "Arquivos de e-mail (.msg)", "Arquivos duplicados", "Atualizações", "Navegador do Contract Downloader", "Login do Coupa", "Começar limpo", "Retenção do histórico"] : ["Language", "Text size", "Downloads", "Downloads simultaneous", "Retry policy", "Email files (.msg)", "Duplicate files", "Updates", "Contract Downloader browser", "Coupa sign-in", "Start clean", "History retention"];
        document.querySelectorAll(".settings-section h3").forEach((element, index) => { element.innerText = settingsHeadings[index]; });
        const panelHeadings = appSettings.language === "pt-BR" ? ["Escolha o input", "Valide o input", "Organize a hierarquia de pastas", "Escolha o local de salvamento", "Revise e inicie"] : ["Choose your input", "Validate your input", "Arrange folder hierarchy", "Choose the save location", "Review and start"];
        document.querySelectorAll("[data-journey-panel] .card-heading h3").forEach((element, index) => { element.innerText = panelHeadings[index]; });
        const settingsDescriptions = appSettings.language === "pt-BR" ? ["Altera o idioma da interface. A saída do CLI e os logs permanecem em inglês.", "Ajusta a escala da interface para facilitar a leitura. A prévia é aplicada imediatamente e salva neste computador.", "Escolha a pasta base. Cada execução recebe uma subpasta com timestamp.", "Quantos POs o app processa ao mesmo tempo. Valores maiores podem aumentar a carga no servidor.", "Tentativas automáticas para um PO antes de marcá-lo como erro. O retry manual continua disponível no histórico.", "Escolha se arquivos de e-mail baixados são convertidos para PDF e se seus anexos são extraídos.", "Compara arquivos com SHA-256. Arquivos idênticos usam hard link quando possível ou um arquivo de referência.", "A verificação ao iniciar é opcional. Você sempre pode verificar, baixar, validar e instalar uma atualização manualmente.", "Escolha o navegador usado pelo Contract Downloader para o login do Coupa. Links externos seguem o navegador padrão do sistema.", "Usa um perfil separado do aplicativo para o login; seus perfis pessoais não são alterados nem bloqueados.", "Esquece o histórico local e o login, preservando arquivos baixados, relatórios e inputs.", "A limpeza automática só se aplica a execuções concluídas e nunca remove uma execução ativa."] : ["Changes the application interface language. CLI output and logs remain in English.", "Adjusts the interface scale for readability. The preview is applied immediately and saved on this computer.", "Choose the base folder. Each run receives its own timestamped subfolder.", "How many POs the app processes at the same time. Higher values may increase server load.", "Automatic attempts for a PO before marking it as failed. Manual retry remains available from History.", "Choose whether downloaded email files are converted to PDF and whether their attachments are extracted.", "Compare files with SHA-256. Identical files use a hard link when possible or a reference sidecar.", "Startup checks are optional. You can always check, download, verify, and install an update manually.", "Choose the browser used by Contract Downloader for Coupa sign-in. External links follow the operating system default browser.", "Use a separate app-owned profile for sign-in; personal browser profiles are not changed or locked.", "Forget local run history and sign-in state while preserving downloaded files, reports, and original inputs.", "Automatic cleanup only applies to completed runs and never removes an active run."];
        document.querySelectorAll(".settings-section > div:first-child p").forEach((element, index) => { element.innerText = settingsDescriptions[index]; });
        const setMany = (selector, values) => document.querySelectorAll(selector).forEach((element, index) => { if (values[index] !== undefined) element.innerText = values[index]; });
        const pt = appSettings.language === "pt-BR";
        if (hierarchyOrder.length) renderHierarchy();
        setMany("#screen-new .template-actions strong", [pt ? "Começando do zero?" : "Starting from scratch?"]);
        setMany("#screen-new .template-actions span", [pt ? "Crie o template Excel, preencha, salve e feche o arquivo." : "Create the Excel template, fill it in, then save and close it."]);
        setMany("#screen-new .choice-divider span", [pt ? "OU" : "OR"]);
        setMany("#screen-new .dropzone h3", [pt ? "Arraste o arquivo preenchido aqui" : "Drop your completed file here"]);
        setMany("#screen-new .dropzone p", [pt ? "Excel ou CSV · o arquivo original será preservado" : "Excel or CSV · the original file is preserved"]);
        setMany("#screen-new .journey-hint", [pt ? "O próximo passo verifica se todas as colunas obrigatórias existem." : "The next step checks that all required columns are present."]);
        setMany("#btn-start-over", [pt ? "Começar de novo" : "Start over"]);
        setMany("[data-journey-panel] .card-heading p", pt ? ["Revise o arquivo antes de qualquer execução. Corrija o mesmo arquivo se necessário.", "Arraste os níveis para ordenar as pastas dos arquivos baixados.", "Selecione a pasta pai onde esta execução salvará seus anexos.", "Tudo está pronto. Confirme estas configurações para iniciar o download."] : ["Review the file before any run is created. Correct it in the same file if needed.", "Drag the levels into the order used for downloaded files.", "Select the parent folder where this run should store its attachments.", "Everything is ready. Confirm these settings to begin the download."]);
        setMany("[data-journey-panel] .journey-folder-guide small", [pt ? "Colunas após <|> viram pastas. Valores vazios viram Unknown." : "Columns after <|> become folders. Empty values become Unknown."]);
        setMany("[data-journey-panel='4'] .field-label", [pt ? "Pasta de download" : "Download folder"]);
        setMany("[data-journey-panel='4'] .destination-note span:last-child", [pt ? "Arquivos válidos existentes são preservados durante retries." : "Existing valid files are preserved during retries."]);
        setMany("#screen-progress .metric-card > span", pt ? ["Progresso", "Velocidade", "ETA", "Erros"] : ["Progress", "Speed", "ETA", "Errors"]);
        setMany("#screen-progress .section-header h3", [pt ? "Log de execução" : "Execution log"]);
        setMany("#screen-progress .section-header p", [pt ? "Progresso e eventos importantes de autenticação, alertas, erros e relatório." : "Key progress, authentication, warning, error, and report events."]);
        setMany("#speed-note, #eta-note", pt ? ["POs concluídas recentemente", "Atualizado pela velocidade recente"] : ["Recent completed POs", "Updates with recent speed"]);
        setMany("#btn-back-new, #btn-pause-resume, #btn-stop-session, #btn-clear-log", pt ? ["Nova execução", "Pausar", "Parar execução", "Limpar"] : ["New run", "Pause", "Stop run", "Clear"]);
        setMany("#screen-history .intro-block .eyebrow, #screen-history .intro-block h2", pt ? ["TRILHA DE AUDITORIA", "Histórico de execuções"] : ["AUDIT TRAIL", "Run history"]);
        setMany("#active-run-banner strong", [pt ? "Uma baixa já está em andamento." : "A download is already running."]);
        setMany("#active-run-banner span", [pt ? "Volte para Execução ativa para acompanhar." : "Return to Active run to monitor it."]);
        setMany("#btn-go-active-run", [pt ? "Ver execução ativa" : "View active run"]);
        setMany("#mapping-title, #mapping-subtitle", pt ? ["Mapeie as colunas do arquivo", "As colunas obrigatórias não foram encontradas automaticamente. Informe quais colunas contêm o número da PO e o fornecedor."] : ["Map the file columns", "The required columns were not found automatically. Tell the app which columns hold the PO number and the supplier."]);
        setMany("#btn-map-columns", [pt ? "Mapear colunas" : "Map columns"]);
        setMany("#mapping-notice-title", [pt ? "Este arquivo não tem as colunas padrão." : "This file does not have the standard columns."]);
        setMany("#mapping-notice-text", [pt ? "Mapeie as colunas de PO e fornecedor para continuar." : "Map the PO and supplier columns to continue."]);
        setMany("#btn-apply-mapping", [pt ? "Aplicar mapeamento e validar" : "Apply mapping and validate"]);
        setMany("#column-mapping-card .mapping-fields label span", pt ? ["Coluna de número da PO", "Coluna de fornecedor"] : ["PO number column", "Supplier column"]);
        setMany("#hierarchy-disabled h4", [pt ? "Colunas desativadas" : "Disabled columns"]);
        setMany("#hierarchy-disabled p", [pt ? "Estas colunas permanecem no input e no relatório final, mas não criam pastas." : "These columns stay in the input and in the final report, but do not create folders."]);
        setMany("#run-description-input", [pt ? "Por que esta execução foi feita? Para quem?" : "Why was this run made? For whom?"]);
        setMany("#btn-save-run-description", [pt ? "Salvar" : "Save"]);
        setMany(".description-hint", [pt ? "Texto livre que aparece no histórico para explicar o objetivo da execução (solicitação, análise, solicitante)." : "Free text shown in history to explain this run's purpose (request, analysis, requester)."]);
        setMany("#screen-history .intro-block p:not(.eyebrow)", [pt ? "Revise resultados, erros por PO e relatórios." : "Review results, inspect PO-level errors, and export reports."]);
        setMany("#btn-refresh-history, #btn-clear-history", pt ? ["Atualizar", "Excluir todo o histórico"] : ["Refresh", "Delete all history"]);
        setMany("#history-list ~ *", []);
        setMany(".history-table th", pt ? ["Execução", "Input", "Início", "POs", "Resultado", "Ações"] : ["Run", "Input", "Started", "POs", "Result", "Actions"]);
        setMany("#screen-learn .intro-block .eyebrow", [pt ? "APRENDA" : "LEARN"]);
        setMany("#screen-learn .intro-block p:not(.eyebrow)", [pt ? "Guia prático para preparar inputs, baixar anexos e recuperar erros com segurança." : "A practical guide to prepare inputs, download attachments, and recover safely from errors."]);
        setMany("#screen-settings .intro-block .eyebrow", [pt ? "CONFIGURAÇÕES" : "SETTINGS"]);
        setMany("#screen-settings .intro-block p:not(.eyebrow)", [pt ? "Controle downloads, retries, atualizações e o tempo de permanência no histórico." : "Control downloads, retries, updates, and how long runs remain in history."]);
        setMany("#settings-auth-browser-section h3", [pt ? "Navegador do Contract Downloader" : "Contract Downloader browser"]);
        setMany("#settings-auth-browser-section p", [pt ? "Escolha o navegador usado pelo Contract Downloader para o login do Coupa. Links externos continuam usando o navegador padrão do sistema." : "Choose the browser used by Contract Downloader for Coupa sign-in. External links continue to use your operating system default browser."]);
        setMany("#btn-check-updates", [pt ? "Verificar agora" : "Check now"]);
        setMany("#btn-reset-auth", [pt ? "Zerar estado do login" : "Reset sign-in state"]);
        setMany("#btn-reset-application", [pt ? "Zerar estado local" : "Reset local state"]);
        setMany("#settings-language option", pt ? ["English (padrão)", "Português (Brasil)"] : ["English (default)", "Português (Brasil)"]);
        setMany("#settings-font-scale option", pt ? ["Padrão — 100%", "Confortável — 110%", "Grande — 120%", "Extra grande — 130%"] : ["Standard — 100%", "Comfortable — 110%", "Large — 120%", "Extra large — 130%"]);
        setMany("#settings-concurrency option",  pt ? ["Conservador — 2 downloads", "Balanceado — 4 downloads", "Rápido — 6 downloads", "Máximo — 8 downloads"] : ["Conservative — 2 downloads", "Balanced — 4 downloads", "Fast — 6 downloads", "Custom maximum — 8 downloads"]);
        setMany("#settings-retry option", pt ? ["Sem retry automático", "Tentar novamente uma vez", "Tentar novamente duas vezes"] : ["No automatic retry", "Retry once", "Retry twice"]);
        setMany("#settings-retention option", pt ? ["Tudo", "Últimas 10 execuções", "Últimas 30 execuções", "Execuções dos últimos 90 dias"] : ["Everything", "Last 10 runs", "Last 30 runs", "Runs from the last 90 days"]);
        setMany("#settings-msg-processing option", pt ? ["Desabilitado", "Converter para PDF", "Converter para PDF e extrair anexos"] : ["Disabled", "Convert to PDF", "Convert to PDF and extract attachments"]);
        setMany("#settings-auth-browser option", pt ? ["Automático", "Microsoft Edge", "Google Chrome"] : ["Automatic", "Microsoft Edge", "Google Chrome"]);
        syncAuthBrowserOptions();
        setMany("#settings-field-does-not-exist", []);
        setMany("#screen-settings .settings-field label", pt ? ["Idioma da interface", "Tamanho do texto da interface", "Pasta padrão de download", "Perfil de velocidade", "Retry automático", "Processamento automático", "Navegador do Contract Downloader", "Manter"] : ["Interface language", "Interface text size", "Default download folder", "Speed profile", "Automatic retry", "Automatic processing", "Contract Downloader browser", "Keep"]);
        setMany("#folder-confirm-modal .modal-header .eyebrow, #folder-confirm-modal .modal-header h3, #folder-confirm-modal .modal-description", pt ? ["CONFIRMAR DESTINO", "Revise a estrutura de pastas", "Os anexos serão salvos usando esta estrutura:"] : ["CONFIRM DESTINATION", "Review folder structure", "Attachments will be saved using this structure:"]);
        setMany("#btn-cancel-folder-run, #btn-confirm-folder-run", pt ? ["Cancelar", "Confirmar e iniciar"] : ["Cancel", "Confirm and start"]);
        setMany("#details-modal .modal-header .eyebrow, #modal-title, #btn-open-input", pt ? ["DETALHES DA EXECUÇÃO", "Detalhes da sessão", "Abrir arquivo de input"] : ["RUN DETAILS", "Session details", "Open input file"]);
        setMany("#retry-history-list h4, .company-status-list h4, .po-details-list h4", pt ? ["Histórico de retries", "Verificações de fornecedores", "Pedidos de compra"] : ["Retry history", "Supplier checks", "Purchase orders"]);
        setMany("#status-filter legend, #status-filter label span", pt ? ["Exibir status", "Todos", "Sucesso", "Erro", "Pendente", "Ignorado"] : ["Show statuses", "All", "Success", "Error", "Pending", "Skipped"]);
        setMany(".modal-pos-table th", pt ? ["PO", "Fornecedor", "Status", "Retry", "Mensagem"] : ["PO", "Supplier", "Status", "Retry", "Message"]);
        setMany("#btn-retry-errors, #btn-export-modal-report", pt ? ["Refazer POs com erro", "Exportar relatório"] : ["Retry failed POs", "Export report"]);
        setMany("#diagnostics-modal .modal-header .eyebrow, #diagnostics-modal .modal-header h3, #btn-save-diagnostics, #btn-copy-diagnostics", pt ? ["FERRAMENTA DE SUPORTE", "Diagnóstico do computador", "Salvar relatório", "Copiar relatório"] : ["SUPPORT TOOL", "Host diagnostics", "Save report", "Copy report"]);
        setMany(".toggle-field span", pt ? ["Identificar arquivos idênticos", "Verificar automaticamente"] : ["Identify identical files", "Check automatically"]);
        setMany("#settings-status", [pt ? "As alterações são salvas localmente neste computador." : "Changes are saved locally on this computer."]);
        setMany("#sidebar-does-not-exist", []);
        setMany(".engine-status span:last-child", [pt ? "Motor pronto" : "Engine ready"]);
        setMany("#btn-diagnostics", [pt ? "Executar diagnóstico do computador" : "Run host diagnostics"]);
        setMany(".auth-action", [pt ? "Entrar" : "Sign in"]);
        $("#screen-learn h2").innerText = appSettings.language === "pt-BR" ? "Como o Contract Downloader funciona" : "How Contract Downloader works";
        $("#screen-settings h2").innerText = appSettings.language === "pt-BR" ? "Preferências" : "Preferences";
        const languageOption = $("#settings-language option[value='pt-BR']");
        if (languageOption) languageOption.innerText = "Português (Brasil)";
        const msgOptions = $("#settings-msg-processing").options;
        if (msgOptions) { msgOptions[0].innerText = appSettings.language === "pt-BR" ? "Desabilitado" : "Disabled"; msgOptions[1].innerText = appSettings.language === "pt-BR" ? "Converter para PDF" : "Convert to PDF"; msgOptions[2].innerText = appSettings.language === "pt-BR" ? "Converter para PDF e extrair anexos" : "Convert to PDF and extract attachments"; }
    }

    function journeyRequirement(step) {
        const requirements = appSettings.language === "pt-BR" ? {
            2: "Selecione e salve um arquivo de input primeiro.",
            3: "Valide o input com sucesso antes de organizar as pastas.",
            4: "Conclua a hierarquia de pastas antes de escolher o destino.",
            5: "Escolha uma pasta de destino antes de revisar a execução.",
        } : {
            2: "Select and save an input file first.",
            3: "Validate the input successfully before arranging folders.",
            4: "Complete the folder hierarchy step before choosing a destination.",
            5: "Choose a destination folder before reviewing the run.",
        };
        return requirements[step] || (appSettings.language === "pt-BR" ? "Conclua o passo anterior primeiro." : "Complete the previous step first.");
    }

    function showJourneyStep(step) {
        const target = Number(step);
        if (target < 1 || target > 5) return;
        const locked = target > journeyMaxStep;
        journeyStep = target;
        document.querySelectorAll("[data-journey-panel]").forEach((panel) => {
            const active = Number(panel.dataset.journeyPanel) === target;
            panel.hidden = !active;
            panel.classList.toggle("active", active);
            panel.classList.toggle("locked", active && locked);
            if (active) {
                panel.querySelectorAll("button:not([data-journey-back])").forEach((button) => {
                    if (locked) {
                        button.disabled = true;
                        button.dataset.journeyLocked = "true";
                    } else if (button.dataset.journeyLocked) {
                        button.disabled = false;
                        delete button.dataset.journeyLocked;
                    }
                });
                panel.querySelectorAll("input, select").forEach((field) => { field.disabled = locked; });
            }
        });
        document.querySelectorAll("[data-journey-step]").forEach((button) => {
            const value = Number(button.dataset.journeyStep);
            button.classList.toggle("active", value === target);
            button.classList.toggle("completed", value < journeyMaxStep);
            button.classList.toggle("locked", value > journeyMaxStep);
            button.disabled = false;
            button.title = value > journeyMaxStep ? journeyRequirement(value) : `Go to ${getJourneyCopy(value)[0]}`;
        });
        const content = getJourneyCopy(target);
        if (content) {
            $("#journey-title").innerText = locked ? (appSettings.language === "pt-BR" ? `Etapa ${target} bloqueada` : `Step ${target} is locked`) : content[0];
            $("#journey-subtitle").innerText = locked ? journeyRequirement(target) : content[1];
            $("#journey-subtitle").classList.toggle("journey-subtitle-warning", locked);
        }
        const lockMessage = $("#journey-lock-message");
        lockMessage.hidden = true;
        lockMessage.innerText = "";
        if (hierarchySorter) hierarchySorter.setDisabled(target !== 3 || locked);
        if (target === 2 && selectedFilePath) $("#validation-filename").innerText = $("#selected-filename").innerText;
        if (target === 4 && !locked) { renderDestinationPreview(); ensureDefaultDestination(); }
        if (target === 5 && !locked) renderJourneyReview();
    }

    function completeJourneyStep(nextStep) {
        journeyMaxStep = Math.max(journeyMaxStep, Number(nextStep));
        showJourneyStep(nextStep);
    }

    function renderJourneyReview() {
        const inputPath = selectedFilePath || $("#selected-filename").innerText || "—";
        const inputName = $("#selected-filename").innerText || inputPath.split(/[\\/]/).pop();
        $("#review-file").innerText = inputName;
        $("#review-file").title = inputPath;
        $("#review-hierarchy").innerText = hierarchyOrder.length ? hierarchyOrder.join(" / ") : "Default folder structure";
        const destination = $("#download-dir").value || "—";
        $("#review-destination").innerText = destination;
        $("#review-destination").title = destination;
        const folders = hierarchyOrder.length ? hierarchyOrder : ["Supplier"];
        const folderExpression = folders.map((column) => `<span class="review-variable">{${escapeHtml(column)}}</span>`).join('<span class="review-path-separator">/</span>');
        const poExpression = '<span class="review-variable">{PO}</span>';
        $("#review-destination-hierarchy").innerHTML = `${appSettings.language === "pt-BR" ? "Estrutura:" : "Folder structure:"} ${folderExpression}<span class="review-path-separator">/</span>${poExpression}`;
    }

    function showScreen(screenKey) {
        // While a download is running the New Run journey must stay locked:
        // the user can only watch Active run or browse history/settings.
        if (screenKey === "new" && runInProgress) {
            logToConsole("Warning", appSettings.language === "pt-BR" ? "A Nova Execução fica bloqueada enquanto uma baixa está ativa." : "New Run stays locked while a download is running.");
            screenKey = "progress";
        }
        Object.entries(screens).forEach(([key, screen]) => {
            const active = key === screenKey;
            screen.classList.toggle("active", active);
            screen.hidden = !active;
            navButtons[key].classList.toggle("active", active);
        });
        const titles = { new: t("prepare"), progress: t("activeRun"), history: t("history"), learn: t("learn"), settings: t("settings") };
        if ($("#page-title")) $("#page-title").innerText = titles[screenKey] || titles.new;
        navButtons.new.disabled = runInProgress;
        navButtons.new.title = runInProgress ? (appSettings.language === "pt-BR" ? "Bloqueado durante a execução" : "Locked while a run is active") : "";
        $("#active-run-banner").hidden = !(screenKey === "new" && runInProgress);
        if (screenKey === "new" && runInProgress) $("#btn-start-run").disabled = true;
        if (screenKey === "new" && !runInProgress) $("#btn-start-run").disabled = false;
        syncUpdateButton();
        if (screenKey === "history") loadHistory();
        if (screenKey === "settings") loadSettings();
    }

    Object.entries(navButtons).forEach(([key, button]) => button.addEventListener("click", () => showScreen(key)));
    $("#btn-back-new").addEventListener("click", () => showScreen("new"));
    $("#btn-go-active-run").addEventListener("click", () => showScreen("progress"));
    $("#btn-refresh-history").addEventListener("click", loadHistory);
    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;
        const detailsModal = $("#details-modal");
        const retryEditModalEl = $("#retry-edit-modal");
        if (retryEditModalEl && !retryEditModalEl.hidden) {
            closeRetryEditModal();
        } else if (detailsModal && !detailsModal.hidden) {
            detailsModal.hidden = true;
        }
    });

    function logToConsole(type, message) {
        const consoleLog = $("#console-log");
        if (!consoleLog || !String(message || "").trim()) return;
        const previous = consoleLog.lastElementChild;
        if (previous && previous.dataset.message === String(message)) return;
        const line = document.createElement("div");
        line.className = `log-line ${String(type || "system").toLowerCase()}`;
        line.dataset.message = String(message);
        line.innerText = `[${new Date().toLocaleTimeString()}] ${message}`;
        consoleLog.appendChild(line);
        while (consoleLog.children.length > 100) consoleLog.firstElementChild.remove();
        consoleLog.scrollTop = consoleLog.scrollHeight;
        // Keep browser probes and diagnostics observable without exposing internals in the UI.
        if (typeof console !== "undefined" && console.info) console.info(message);
    }

    function updateReadyState(state, title, detail) {
        const indicator = $("#ready-indicator");
        indicator.className = `status-dot ${state}`;
        $("#ready-title").innerText = title;
        $("#ready-detail").innerText = detail;
    }

    function updateAuthUI(state, detail) {
        const indicator = $("#auth-indicator");
        const text = $("#auth-status-text");
        const detailEl = $("#auth-detail");
        const topLabel = $("#topbar-auth-label");
        const visualState = state.startsWith("auth_") ? "authenticating" : state;
        indicator.className = `status-dot ${visualState}`;
        const pt = appSettings.language === "pt-BR";
        if (state === "authenticated") {
            text.innerText = pt ? "Autenticado" : "Authenticated";
            detailEl.innerText = detail || (pt ? "Sessão Coupa pronta" : "Coupa session ready");
            topLabel.innerText = pt ? "Sessão Coupa pronta" : "Coupa session ready";
        } else if (state === "auth_starting") {
            text.innerText = pt ? "Preparando login…" : "Preparing sign-in…";
            detailEl.innerText = pt ? "Abrindo o perfil dedicado do Contract Downloader" : "Opening the Contract Downloader profile";
            topLabel.innerText = pt ? "Abrindo o Coupa" : "Opening Coupa";
        } else if (state === "auth_browser_ready") {
            text.innerText = pt ? "Verificando o Coupa…" : "Checking Coupa…";
            detailEl.innerText = pt ? "A página foi carregada; verificando a sessão" : "Page loaded; checking the session";
            topLabel.innerText = pt ? "Verificando sessão" : "Checking session";
        } else if (state === "auth_user_action_required") {
            text.innerText = pt ? "Ação necessária" : "Action required";
            detailEl.innerText = pt ? "Conclua o login na janela do navegador do aplicativo" : "Complete sign-in in the app browser window";
            topLabel.innerText = pt ? "Aguardando sua ação" : "Waiting for your action";
        } else if (state === "auth_checking") {
            text.innerText = pt ? "Verificando sessão…" : "Checking session…";
            detailEl.innerText = pt ? "O Coupa está sendo consultado" : "Coupa is being checked";
            topLabel.innerText = pt ? "Verificando acesso" : "Checking access";
        } else if (state === "auth_validating") {
            text.innerText = pt ? "Validando login…" : "Validating sign-in…";
            detailEl.innerText = pt ? "Login detectado; confirmando acesso ao Coupa" : "Sign-in detected; confirming Coupa access";
            topLabel.innerText = pt ? "Validando sessão" : "Validating session";
        } else if (state === "authenticating") {
            text.innerText = pt ? "Entrando…" : "Signing in…";
            detailEl.innerText = pt ? "Preparando a autenticação" : "Preparing authentication";
            topLabel.innerText = pt ? "Preparando login" : "Preparing sign-in";
        } else if (state === "expired") {
            text.innerText = pt ? "Login necessário" : "Login required";
            detailEl.innerText = pt ? "A sessão em cache expirou" : "Cached session expired";
            topLabel.innerText = pt ? "Login necessário" : "Login required";
        } else if (state === "unavailable") {
            text.innerText = pt ? "Verificação indisponível" : "Session check unavailable";
            detailEl.innerText = detail || (pt ? "Não foi possível verificar a sessão agora" : "The cached session could not be verified right now");
            topLabel.innerText = pt ? "Verificação de sessão indisponível" : "Session check unavailable";
        } else {
            text.innerText = pt ? "Login necessário" : "Login required";
            detailEl.innerText = detail || (pt ? "Clique para autenticar" : "Click to authenticate");
            topLabel.innerText = pt ? "Login necessário" : "Login required";
        }
        const cachedSessionUnavailable = state === "unavailable" && /cached coupa session found/i.test(String(detail || ""));
        $("#btn-authenticate").classList.toggle("is-authenticated", state === "authenticated" || cachedSessionUnavailable);
        const action = $("#btn-authenticate .auth-action");
        if (action) {
            // A cached session must not turn a temporary network outage into a
            // repeated sign-in request. Explicit expiry/missing states still
            // expose the sign-in action.
            action.style.display = state === "authenticated" || cachedSessionUnavailable ? "none" : "";
            action.innerText = state === "authenticated" || cachedSessionUnavailable ? (pt ? "Sessão em cache" : "Cached session") : (state.startsWith("auth_") || state === "authenticating" ? (pt ? "Aguarde…" : "Please wait…") : (pt ? "Entrar" : "Sign in"));
        }
        $("#btn-authenticate").disabled = state.startsWith("auth_") || state === "authenticating" || cachedSessionUnavailable;
    }

    const authStateLabels = {
        starting: "auth_starting",
        browser_ready: "auth_browser_ready",
        user_action_required: "auth_user_action_required",
        checking: "auth_checking",
        validating: "auth_validating",
        success: "authenticated",
        error: "expired",
    };

    function normalizeAuthState(state) {
        return authStateLabels[state] || state || "authenticating";
    }

    async function authenticateWithProgress() {
        if (!hasApi("authenticate")) return { success: false, error: "Authentication API unavailable." };
        updateAuthUI("auth_starting");
        logToConsole("System", appSettings.language === "pt-BR" ? "Preparando o login do Coupa…" : "Preparing Coupa sign-in…");
        const started = await api().authenticate();
        if (!started || !started.success) return started || { success: false, error: "Authentication failed." };
        if (!hasApi("get_authentication_status")) return started;

        let lastMessage = "";
        while (true) {
            const status = await api().get_authentication_status();
            const uiState = normalizeAuthState(status.state);
            updateAuthUI(uiState, status.message);
            if (status.message && status.message !== lastMessage) {
                logToConsole(uiState === "auth_user_action_required" ? "Warning" : "System", status.message);
                lastMessage = status.message;
            }
            if (status.state === "success") return { success: true };
            if (status.state === "error") return { success: false, error: status.message || "Authentication failed." };
            await new Promise((resolve) => setTimeout(resolve, 250));
        }
    }

    function destroyHierarchySorter() {
        if (hierarchySorter) hierarchySorter.destroy();
        hierarchySorter = null;
    }

    function syncHierarchyLevels(sortableList) {
        sortableList.querySelectorAll(":scope > li[data-column]").forEach((item, index) => {
            item.dataset.level = String(index + 2);
            item.style.setProperty("--hierarchy-level", String(index + 1));
            const level = item.querySelector(".hierarchy-level");
            if (level) level.innerText = `${appSettings.language === "pt-BR" ? "Nível" : "Level"} ${index + 2}`;
        });
    }

    function applyHierarchyOrder(order, source) {
        hierarchyOrder = order;
        const sortableList = $("#hierarchy-sortable");
        if (sortableList) syncHierarchyLevels(sortableList);
        renderDestinationPreview();
        const status = $("#hierarchy-reorder-status");
        if (status) {
            const orderText = hierarchyOrder.join(" / ");
            status.innerText = appSettings.language === "pt-BR"
                ? `Hierarquia reordenada por ${source === "drag" ? "arraste" : "botão"}: ${orderText}.`
                : `Hierarchy reordered by ${source}: ${orderText}.`;
        }
    }

    function renderHierarchy() {
        const container = $("#folder-hierarchy");
        const levelLabel = appSettings.language === "pt-BR" ? "Nível" : "Level";
        const supplierLabel = appSettings.language === "pt-BR" ? "Fornecedor (sempre primeiro)" : "Supplier (always first)";
        const poLabel = appSettings.language === "pt-BR" ? "PO (sempre último)" : "PO (always last)";
        const disableLabel = appSettings.language === "pt-BR" ? "Desativar" : "Disable";
        const enableLabel = appSettings.language === "pt-BR" ? "Ativar" : "Enable";
        const dragLabel = appSettings.language === "pt-BR" ? "Arrastar para reordenar" : "Drag to reorder";
        const moveUpLabel = appSettings.language === "pt-BR" ? "Mover para cima" : "Move up";
        const moveDownLabel = appSettings.language === "pt-BR" ? "Mover para baixo" : "Move down";
        const noLevelsLabel = appSettings.language === "pt-BR" ? "Nenhum nível opcional está ativo." : "No optional folder levels are enabled.";
        const disabledBox = $("#hierarchy-disabled");
        const disabledList = $("#hierarchy-disabled-list");

        destroyHierarchySorter();
        if (!hierarchyColumnsLoaded) {
            container.innerHTML = `<div class="hierarchy-empty">${appSettings.language === "pt-BR" ? "Valide o input para carregar os níveis de pasta." : "Validate the input to load its folder levels."}</div>`;
            disabledBox.hidden = true;
            disabledList.innerHTML = "";
            return;
        }

        const sortableItems = hierarchyOrder.length
            ? hierarchyOrder.map((column, index) => `<li class="hierarchy-row hierarchy-item" data-column="${escapeHtml(column)}" data-level="${index + 2}" style="--hierarchy-level:${index + 1}"><span class="hierarchy-branch" aria-hidden="true">└</span><span class="hierarchy-level">${levelLabel} ${index + 2}</span><span class="hierarchy-column-name">${escapeHtml(column)}</span><div class="hierarchy-actions"><button class="drag-handle" type="button" title="${dragLabel}" aria-label="${dragLabel}: ${escapeHtml(column)}">☷</button><button class="hierarchy-move" data-move-direction="up" type="button" title="${moveUpLabel}" aria-label="${moveUpLabel}: ${escapeHtml(column)}">↑</button><button class="hierarchy-move" data-move-direction="down" type="button" title="${moveDownLabel}" aria-label="${moveDownLabel}: ${escapeHtml(column)}">↓</button><button class="hierarchy-toggle" data-toggle-column="${escapeHtml(column)}" title="${disableLabel}" aria-label="${disableLabel}: ${escapeHtml(column)}" type="button">×</button></div></li>`).join("")
            : `<li class="hierarchy-empty hierarchy-sortable-empty">${noLevelsLabel}</li>`;

        container.innerHTML = [
            `<div class="hierarchy-row hierarchy-fixed" data-fixed="supplier"><span class="hierarchy-branch" aria-hidden="true">└</span><span class="hierarchy-level">${levelLabel} 1</span><span class="hierarchy-lock" aria-hidden="true">🔒</span><strong>${supplierLabel}</strong></div>`,
            `<ol class="hierarchy-sortable" id="hierarchy-sortable" aria-label="${appSettings.language === "pt-BR" ? "Níveis de pasta reordenáveis" : "Reorderable folder levels"}">${sortableItems}</ol>`,
            `<div class="hierarchy-row hierarchy-fixed" data-fixed="po" style="--hierarchy-level:${hierarchyOrder.length + 1}"><span class="hierarchy-branch" aria-hidden="true">└</span><span class="hierarchy-level">${levelLabel} ${hierarchyOrder.length + 2}</span><span class="hierarchy-lock" aria-hidden="true">🔒</span><strong>${poLabel}</strong></div>`,
        ].join("");

        container.querySelectorAll(".hierarchy-toggle[data-toggle-column]").forEach((button) => {
            button.addEventListener("click", () => {
                const column = button.dataset.toggleColumn;
                hierarchyOrder = hierarchyOrder.filter((value) => value !== column);
                disabledHierarchyColumns.push(column);
                renderHierarchy();
                renderDestinationPreview();
            });
        });

        disabledBox.hidden = disabledHierarchyColumns.length === 0;
        disabledList.innerHTML = disabledHierarchyColumns.map((column) => `<li><span>${escapeHtml(column)}</span><button class="hierarchy-toggle" data-reenable-column="${escapeHtml(column)}" title="${enableLabel}" type="button">+</button></li>`).join("");
        disabledList.querySelectorAll(".hierarchy-toggle[data-reenable-column]").forEach((button) => {
            button.addEventListener("click", () => {
                const column = button.dataset.reenableColumn;
                disabledHierarchyColumns = disabledHierarchyColumns.filter((value) => value !== column);
                hierarchyOrder.push(column);
                renderHierarchy();
                renderDestinationPreview();
            });
        });

        const sortableList = $("#hierarchy-sortable");
        if (window.HierarchySorter) {
            hierarchySorter = new window.HierarchySorter(sortableList, {
                disabled: journeyStep !== 3 || journeyStep > journeyMaxStep,
                onChange: applyHierarchyOrder,
            });
        } else {
            logToConsole("Error", "The folder reordering component could not be loaded.");
        }
    }

    function renderDestinationPreview() {
        const preview = $("#destination-preview");
        if (!preview) return;
        const directory = $("#download-dir").value || "Downloads/CoupaAttachments";
        const parts = hierarchyOrder.length ? hierarchyOrder : [];
        const lines = [`${directory}/`, "└── {Supplier}"];
        parts.forEach((part) => { lines.push(`    └── {${escapeHtml(part)}}`); });
        lines.push("        └── {PO}/");
        preview.innerText = lines.join("\n");
    }

    function renderHierarchyWarnings(emptyColumns) {
        const box = $("#hierarchy-warnings");
        const columns = Array.isArray(emptyColumns) ? emptyColumns : [];
        if (!columns.length) { box.hidden = true; box.innerHTML = ""; return; }
        box.hidden = false;
        box.innerHTML = columns.map((column) => `<div class="validation-warning">${appSettings.language === "pt-BR"
            ? `A coluna “${escapeHtml(column)}” está 100% vazia no input e não será usada para criar pastas.`
            : `The column “${escapeHtml(column)}” is completely empty in the input and will not be used to create folders.`}</div>`).join("");
    }

    function setHierarchyColumns(columns, emptyColumns = []) {
        const empty = new Set((emptyColumns || []).map(String));
        const available = (columns || []).map(String).filter((column) => !empty.has(column));
        hierarchyColumnsLoaded = true;
        disabledHierarchyColumns = disabledHierarchyColumns.filter((column) => available.includes(column));
        const disabled = new Set(disabledHierarchyColumns);
        const kept = hierarchyOrder.filter((column) => available.includes(column) && !disabled.has(column));
        hierarchyOrder = kept.concat(available.filter((column) => !disabled.has(column) && !kept.includes(column)));
        renderHierarchy();
        renderDestinationPreview();
    }

    function setFile(filePath, fileName, fileSize) {
        if (generatedTemplatePath && String(filePath || "") !== String(generatedTemplatePath)) generatedTemplatePath = null;
        selectedFilePath = filePath || null;
        selectedFileValidated = false;
        validatedFingerprint = null;
        mappingDetected = null;
        mappingSuggestions = { po: [], supplier: [] };
        hierarchyOrder = [];
        disabledHierarchyColumns = [];
        hierarchyColumnsLoaded = false;
        hideMappingNotice();
        $("#validation-feedback").hidden = true;
        $("#destination-feedback").hidden = true;
        renderHierarchy();
        if (!selectedFilePath) {
            updateReadyState("unauthenticated", "Choose an input file", "Use the native picker so the full path is available.");
            return;
        }
        $("#selected-filename").innerText = fileName || String(filePath).split(/[\\/]/).pop();
        $("#validation-filename").innerText = fileName || String(filePath).split(/[\\/]/).pop();
        $("#selected-filesize").innerText = fileSize ? `${(fileSize / 1024).toFixed(1)} KB` : "Path selected";
        const extension = String(fileName || filePath).split(".").pop().toUpperCase();
        $(".file-type").innerText = extension || "FILE";
        $("#dropzone").hidden = true;
        $("#file-details").hidden = false;
        $("#file-state").hidden = false;
        $("#btn-validate-file").disabled = false;
        $("#btn-next-input").disabled = Boolean(hasApi("inspect_input_file"));
        updateReadyState("unauthenticated", "File selected", "Validate the file before starting.");
        startFileMonitor();
        // Detect non-standard files immediately so the user can map the
        // columns without waiting for the validation step.
        probeColumnsForMapping();
    }

    function showMappingNotice() {
        const notice = $("#mapping-notice");
        if (notice) notice.hidden = false;
    }

    function hideMappingNotice() {
        const notice = $("#mapping-notice");
        if (notice) notice.hidden = true;
    }

    async function probeColumnsForMapping() {
        if (!selectedFilePath || !hasApi("get_input_columns")) return;
        const requestedPath = selectedFilePath;
        const probeToken = ++mappingProbeToken;
        try {
            const info = await api().get_input_columns(requestedPath);
            if (requestedPath !== selectedFilePath || probeToken !== mappingProbeToken || !info || !info.success) return;
            mappingColumns = info.columns || [];
            mappingDetected = info.detected || {};
            mappingSuggestions = info.suggestions || { po: [], supplier: [] };
            const missingPo = !mappingDetected.po;
            const missingSupplier = !mappingDetected.supplier;
            if (missingPo || missingSupplier) {
                $("#mapping-notice-title").innerText = appSettings.language === "pt-BR"
                    ? (missingPo && missingSupplier
                        ? "Este arquivo não tem as colunas padrão."
                        : missingPo
                            ? "A coluna de PO não foi encontrada."
                            : "A coluna de fornecedor não foi encontrada.")
                    : (missingPo && missingSupplier
                        ? "This file does not have the standard columns."
                        : missingPo
                            ? "The PO column was not found."
                            : "The supplier column was not found.");
                $("#mapping-notice-text").innerText = appSettings.language === "pt-BR"
                    ? "Mapeie as colunas de PO e fornecedor para continuar."
                    : "Map the PO and supplier columns to continue.";
                showMappingNotice();
            } else {
                hideMappingNotice();
            }
        } catch (_) { /* best effort */ }
    }

    $("#btn-map-columns").addEventListener("click", async () => {
        if (!selectedFilePath) return;
        // Refresh the column list, then open the mapping card in step 2.
        if (hasApi("get_input_columns")) {
            const info = await api().get_input_columns(selectedFilePath);
            if (info && info.success) {
                mappingColumns = info.columns || [];
                mappingDetected = info.detected || {};
                mappingSuggestions = info.suggestions || { po: [], supplier: [] };
            }
        }
        completeJourneyStep(2);
        renderMappingCard(mappingColumns, mappingDetected, mappingSuggestions);
    });

    function clearFile() {
        selectedFilePath = null;
        selectedFileValidated = false;
        validatedFingerprint = null;
        mappingDetected = null;
        mappingSuggestions = { po: [], supplier: [] };
        mappingColumns = [];
        hierarchyOrder = [];
        disabledHierarchyColumns = [];
        hierarchyColumnsLoaded = false;
        mappingProbeToken += 1;
        hideMappingNotice();
        if (fileMonitorInterval) clearInterval(fileMonitorInterval);
        $("#file-input").value = "";
        $("#dropzone").hidden = false;
        $("#file-details").hidden = true;
        $("#validation-feedback").hidden = true;
        $("#destination-feedback").hidden = true;
        $("#file-state").hidden = true;
        $("#btn-next-input").disabled = true;
        $("#btn-next-hierarchy").disabled = true;
        journeyMaxStep = 1;
        showJourneyStep(1);
        updateReadyState("unauthenticated", "Choose an input file", "Validation is required before starting.");
    }

    async function chooseInputFile() {
        if (hasApi("select_file")) {
            const result = await api().select_file();
            if (result && result.success) setFile(result.path, result.path.split(/[\\/]/).pop());
            else if (result && result.error) logToConsole("Error", result.error);
            return;
        }
        $("#file-input").click();
    }

    $("#btn-browse").addEventListener("click", chooseInputFile);
    $("#btn-open-selected-input").addEventListener("click", async () => {
        if (!selectedFilePath) return;
        if (!hasApi("open_input_path")) {
            logToConsole("Warning", "Opening the selected input is available in the desktop app.");
            return;
        }
        const result = await api().open_input_path(selectedFilePath);
        if (!result.success) logToConsole("Error", result.error || "Could not open the input file.");
    });
    $("#file-input").addEventListener("change", (event) => {
        const file = event.target.files && event.target.files[0];
        if (file) setFile(file.path || file.name, file.name, file.size);
    });
    $("#dropzone").addEventListener("dragover", (event) => { event.preventDefault(); $("#dropzone").classList.add("dragover"); });
    $("#dropzone").addEventListener("dragleave", () => $("#dropzone").classList.remove("dragover"));
    $("#dropzone").addEventListener("drop", (event) => {
        event.preventDefault();
        $("#dropzone").classList.remove("dragover");
        const file = event.dataTransfer.files && event.dataTransfer.files[0];
        if (file) setFile(file.path || file.name, file.name, file.size);
    });
    $("#btn-clear-file").addEventListener("click", clearFile);

    async function startOver() {
        const pt = appSettings.language === "pt-BR";
        if (runInProgress) return;
        const hasJourneyState = Boolean(selectedFilePath || generatedTemplatePath || journeyMaxStep > 1);
        if (!hasJourneyState) {
            clearFile();
            return;
        }
        const confirmed = confirm(pt
            ? "Começar de novo? O estado desta preparação será apagado e uma nova execução será iniciada do zero. O histórico e os resultados de execuções concluídas serão preservados. Um template criado pelo aplicativo será excluído; arquivos de input escolhidos por você serão preservados."
            : "Start over? This preparation state will be cleared and a new run will begin from scratch. History and results of completed runs are preserved. A template created by the app will be deleted; input files you chose are preserved.");
        if (!confirmed) return;
        if (hasApi("reset_new_run")) {
            const result = await api().reset_new_run(generatedTemplatePath || selectedFilePath || "");
            if (!result.success) {
                logToConsole("Error", result.error || "Could not reset the new-run journey.");
                return;
            }
        }
        generatedTemplatePath = null;
        hierarchyOrder = [];
        disabledHierarchyColumns = [];
        clearFile();
        $("#download-dir").value = "";
        await ensureDefaultDestination();
        logToConsole("System", pt ? "Nova jornada iniciada do zero." : "New journey started from zero.");
    }

    $("#btn-start-over").addEventListener("click", startOver);

    function showDestinationFeedback(message) {
        const box = $("#destination-feedback");
        if (!box) return;
        box.innerText = message || "";
        box.hidden = !message;
    }

    async function validateDestinationPath() {
        const value = $("#download-dir").value.trim();
        if (!value) {
            showDestinationFeedback(appSettings.language === "pt-BR" ? "Escolha uma pasta de destino." : "Choose a download folder.");
            return false;
        }
        if (!hasApi("validate_download_directory")) return true;
        try {
            const result = await api().validate_download_directory(value);
            if (!result || !result.success) {
                showDestinationFeedback(result?.error || (appSettings.language === "pt-BR" ? "A pasta de destino não está disponível." : "The download destination is not available."));
                return false;
            }
            showDestinationFeedback("");
            if (result.path) $("#download-dir").value = result.path;
            return true;
        } catch (error) {
            showDestinationFeedback(error?.message || String(error));
            return false;
        }
    }

    async function ensureDefaultDestination() {
        if ($("#download-dir").value) {
            $("#btn-next-review").disabled = false;
            return;
        }
        if (hasApi("get_default_download_directory")) {
            const path = await api().get_default_download_directory();
            if (path) $("#download-dir").value = path;
        } else {
            const stamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 15);
            $("#download-dir").value = `Downloads/CoupaAttachments/run_${stamp}`;
        }
        $("#btn-next-review").disabled = !$("#download-dir").value;
    }

    $("#btn-choose-dir").addEventListener("click", async () => {
        if (hasApi("select_directory")) {
            const path = await api().select_directory();
            if (path) {
                $("#download-dir").value = path;
                showDestinationFeedback("");
            }
        } else {
            $("#download-dir").value = "Downloads/CoupaAttachments";
            showDestinationFeedback("");
        }
        $("#btn-next-review").disabled = !$("#download-dir").value;
    });
    $("#download-dir").addEventListener("input", () => {
        showDestinationFeedback("");
        $("#btn-next-review").disabled = !$("#download-dir").value.trim();
    });
    $("#download-dir").addEventListener("change", async () => {
        if (hasApi("set_default_download_directory") && $("#download-dir").value.trim()) {
            await api().set_default_download_directory($("#download-dir").value.trim());
        }
    });

    $("#btn-download-template").addEventListener("click", async () => {
        if (!hasApi("generate_input_template")) {
            logToConsole("Warning", "Template creation is available in the desktop app.");
            return;
        }
        const result = await api().generate_input_template();
        if (result.success) {
            setFile(result.path, result.path.split(/[\\/]/).pop());
            generatedTemplatePath = result.path;
            // The generated template already defines these levels, even before
            // the user adds the first PO row and validates the workbook.
            setHierarchyColumns(["Company", "Year", "Quarter", "Business Unit"]);
            logToConsole("Success", "Input template created and selected automatically.");
            alert(`Template opened at:\n${result.path}\n\nFill it in, save it, and close it. The application will keep monitoring this file automatically.`);
        } else {
            logToConsole("Error", result.message || "Could not create the template.");
        }
    });

    function updateFileState(state) {
        const panel = $("#file-state");
        const dot = $("#file-state-dot");
        const label = $("#file-state-text");
        const pt = appSettings.language === "pt-BR";
        panel.hidden = false;
        panel.classList.remove("ready", "blocked");
        if (state.open_detected) {
            panel.classList.add("blocked");
            dot.className = "status-dot unauthenticated";
            label.innerText = pt ? "O Excel parece estar aberto — salve e feche o arquivo" : "Excel appears to be open — save and close it";
            selectedFileValidated = false;
            $("#btn-next-input").disabled = true;
        } else if (state.ready) {
            panel.classList.add("ready");
            dot.className = "status-dot authenticated";
            label.innerText = pt ? "Arquivo salvo e pronto para validar" : "File saved and ready to validate";
            $("#btn-next-input").disabled = false;
        } else {
            dot.className = "status-dot authenticating";
            label.innerText = pt ? "Aguardando o arquivo terminar de salvar…" : "Waiting for the file to finish saving…";
            $("#btn-next-input").disabled = true;
        }
    }

    async function pollFileState() {
        if (!selectedFilePath || !hasApi("inspect_input_file")) return;
        try {
            const state = await api().inspect_input_file(selectedFilePath);
            updateFileState(state);
            const fingerprint = state.mtime_ns && state.size ? `${state.mtime_ns}:${state.size}` : null;
            if (validatedFingerprint && fingerprint && fingerprint !== validatedFingerprint) {
                selectedFileValidated = false;
                $("#validation-feedback").hidden = true;
                updateReadyState("unauthenticated", "File changed", "Validate the updated file again before starting.");
            }
        } catch (error) {
            updateFileState({ ready: false, open_detected: true });
        }
    }

    function startFileMonitor() {
        if (fileMonitorInterval) clearInterval(fileMonitorInterval);
        pollFileState();
        fileMonitorInterval = setInterval(pollFileState, 800);
    }

    function renderMappingCard(columns, detected, suggestions = mappingSuggestions) {
        const card = $("#column-mapping-card");
        if (!card) return;
        if (!Array.isArray(columns) || !columns.length) { card.hidden = true; return; }
        const poSelect = $("#mapping-po-select");
        const supplierSelect = $("#mapping-supplier-select");
        if (!poSelect || !supplierSelect) return;
        const options = (placeholder) => `<option value="">${placeholder}</option>` + columns.map((column) => `<option value="${escapeHtml(column)}">${escapeHtml(column)}</option>`).join("");
        poSelect.innerHTML = options(appSettings.language === "pt-BR" ? "— selecione a coluna de PO —" : "— select the PO column —");
        supplierSelect.innerHTML = options(appSettings.language === "pt-BR" ? "— selecione a coluna de fornecedor —" : "— select the supplier column —");
        const best = (role) => (suggestions?.[role] || [])[0];
        if (detected && detected.po) poSelect.value = detected.po;
        else if (best("po")) poSelect.value = best("po").column;
        if (detected && detected.supplier) supplierSelect.value = detected.supplier;
        else if (best("supplier")) supplierSelect.value = best("supplier").column;
        const hint = (role) => {
            const item = best(role);
            if (!item) return "";
            const examples = (item.examples || []).slice(0, 3).join(", ");
            return `${item.confidence}% confidence${examples ? ` · e.g. ${examples}` : ""}`;
        };
        $("#mapping-po-hint").innerText = hint("po");
        $("#mapping-supplier-hint").innerText = hint("supplier");
        mappingColumns = columns;
        card.hidden = false;
    }

    function hideMappingCard() {
        const card = $("#column-mapping-card");
        if (card) card.hidden = true;
    }

    async function applyColumnMapping() {
        if (!selectedFilePath || !hasApi("map_input_columns")) return;
        const mapping = {
            po: $("#mapping-po-select").value,
            supplier: $("#mapping-supplier-select").value,
        };
        if (!mapping.po || !mapping.supplier) {
            logToConsole("Error", appSettings.language === "pt-BR" ? "Selecione as colunas de PO e fornecedor." : "Select the PO and supplier columns first.");
            return;
        }
        if (mapping.po === mapping.supplier) {
            const message = appSettings.language === "pt-BR" ? "PO e fornecedor precisam estar em colunas diferentes." : "PO Number and Supplier must use different columns.";
            logToConsole("Error", message);
            $("#validation-feedback").innerHTML = `<div class="validation-error">${escapeHtml(message)}</div>`;
            $("#validation-feedback").hidden = false;
            return;
        }
        const button = $("#btn-apply-mapping");
        button.disabled = true;
        try {
            const result = await api().map_input_columns(selectedFilePath, mapping);
            if (!result || !result.success) throw new Error(result?.error || (appSettings.language === "pt-BR" ? "Não foi possível aplicar o mapeamento." : "Could not apply the column mapping."));
            logToConsole("Success", appSettings.language === "pt-BR" ? `Mapeamento aplicado: PO → ${result.mapping.po}, Fornecedor → ${result.mapping.supplier}.` : `Mapping applied: PO → ${result.mapping.po}, Supplier → ${result.mapping.supplier}.`);
            await renderValidation(result);
        } catch (error) {
            const message = error?.message || String(error);
            logToConsole("Error", message);
            const feedback = $("#validation-feedback");
            feedback.innerHTML = `<div class="validation-error">${escapeHtml(message)}</div>`;
            feedback.hidden = false;
        } finally {
            button.disabled = false;
        }
    }

    function renderAffectedValues(group, pt) {
        const details = Array.isArray(group.row_details) ? group.row_details : [];
        const isRows = ["blank_rows", "partial_rows", "excel_cell_errors", "required_value_whitespace", "placeholder_supplier", "multiple_pos_in_cell", "ambiguous_po_value", "folder_value_safety"].includes(group.id) || group.rows_are_excel_rows;
        const rowPrefix = pt ? "Linha" : "Row";
        const values = details.length
            ? details.map((detail) => `${rowPrefix} ${detail.row}: ${(detail.parts || []).join(" · ")}`)
            : (Array.isArray(group.rows) ? group.rows.map(String) : []);
        if (!values.length) return "";
        const maxVisible = 200;
        const visible = values.slice(0, maxVisible).map((value) => escapeHtml(value)).join("\n");
        const remaining = values.length - Math.min(values.length, maxVisible);
        const label = isRows ? (pt ? "linhas afetadas" : "affected rows") : "POs";
        const copyLabel = isRows ? (pt ? "Copiar detalhes" : "Copy details") : (pt ? "Copiar POs" : "Copy POs");
        const more = remaining > 0
            ? (pt ? ` · mais ${remaining} não exibidos` : ` · ${remaining} more not shown`)
            : "";
        const copyId = `validation-values-${++validationCopyId}`;
        validationCopyValues.set(copyId, values.join("\n"));
        return `<details class="validation-affected"><summary>${pt ? "Ver" : "View"} ${values.length} ${label}${more}</summary><div class="validation-affected-values"><div class="validation-affected-toolbar"><button class="btn btn-quiet btn-copy-affected" data-copy-id="${copyId}" type="button">${copyLabel}</button></div><code>${visible}</code></div></details>`;
    }

    function validationGroupCopy(group, pt) {
        const copy = {
            blank_rows: ["Blank rows", "Row(s) completely empty.", "Linhas vazias", "Há linhas completamente vazias."],
            partial_rows: ["Rows with missing PO or Supplier", "Rows without PO Number or Supplier.", "Linhas sem PO ou fornecedor", "Há linhas sem PO ou fornecedor."],
            required_value_whitespace: ["Whitespace around PO or Supplier values", "Leading and trailing whitespace is ignored, but can be removed from the source file.", "Espaços em PO ou fornecedor", "Espaços no início e no fim são ignorados, mas podem ser removidos do arquivo."],
            multiple_pos_in_cell: ["Multiple POs in one cell", "Each row must contain one PO. Review the proposed split before applying it.", "Múltiplas POs na mesma célula", "Cada linha deve conter uma PO. Revise a divisão proposta antes de aplicar."],
            ambiguous_po_value: ["Ambiguous PO value", "The value contains a separator but cannot be split safely.", "PO ambígua", "O valor contém um separador, mas não pode ser dividido com segurança."],
            duplicate_pos: ["Duplicate PO numbers", "PO(s) repeated with the same Supplier.", "POs duplicadas", "Há POs repetidas com o mesmo fornecedor."],
            po_supplier_conflict: ["POs linked to multiple Suppliers", "Review these POs manually; automatic deduplication could discard a supplier relationship.", "POs ligadas a vários fornecedores", "Revise manualmente; a correção automática pode descartar um fornecedor."],
            invalid_chars: ["PO numbers with unusual characters", "PO values contain unsupported characters.", "POs com caracteres inválidos", "Há caracteres não permitidos nos valores de PO."],
            unusual_format: ["PO numbers with an invalid format", "PO values must start with PO/PM and contain digits only after the prefix.", "POs com formato inválido", "As POs devem começar com PO/PM e conter apenas números depois do prefixo."],
            unusual_po_length: ["PO numbers with an unusual length", "Most PO numbers contain 8 digits after PO or PM. Confirm values with another length.", "POs com quantidade de dígitos incomum", "A maioria das POs contém 8 dígitos depois de PO ou PM. Confirme valores com outro tamanho."],
            placeholder_pos: ["Placeholder PO values", "Replace placeholders such as UNK, N/A or TBD with real PO numbers.", "POs de preenchimento", "Substitua valores como UNK, N/A ou TBD por POs reais."],
            placeholder_supplier: ["Placeholder Supplier values", "Replace placeholder Supplier values such as Unknown, N/A or TBD.", "Fornecedor de preenchimento", "Substitua valores de fornecedor como Unknown, N/A ou TBD."],
            excel_cell_errors: ["Excel error values", "Replace formula errors such as #REF!, #VALUE! or #N/A.", "Erros nas células do Excel", "Substitua erros de fórmula como #REF!, #VALUE! ou #N/A."],
            excel_numeric_coercion: ["PO values may have been converted by Excel", "Format the PO column as text and restore lost leading zeros.", "POs convertidas pelo Excel", "Formate a coluna como texto e restaure zeros à esquerda perdidos."],
            empty_headers: ["Empty or unnamed headers", "Rename empty or unnamed columns before continuing.", "Cabeçalhos vazios ou sem nome", "Renomeie as colunas vazias ou sem nome."],
            duplicate_required_headers: ["Duplicate required headers", "The PO or Supplier column appears more than once.", "Cabeçalhos obrigatórios duplicados", "A coluna de PO ou fornecedor aparece mais de uma vez."],
            duplicate_headers: ["Similar column headers", "Review columns with the same base name before choosing folder levels.", "Cabeçalhos semelhantes", "Revise colunas com o mesmo nome-base antes de escolher as pastas."],
            folder_value_safety: ["Folder names will be sanitized", "Warning only: the download can continue. Unsafe characters such as '/' or backslash become '_' in folder names; reserved names, long values and collisions are also normalized.", "Nomes de pasta serão normalizados", "Aviso apenas: o download pode continuar. Caracteres inseguros como '/' ou barra invertida viram '_' nos nomes de pasta; nomes reservados, valores longos e colisões também são normalizados."],
            empty_hierarchy_columns: ["Empty hierarchy columns", "These columns contain no values and will not create folder levels.", "Colunas de hierarquia vazias", "Estas colunas não têm valores e não criarão níveis de pasta."],
            missing_po_column: ["Missing PO Number column", "Map the column that contains the PO Number.", "Coluna de PO ausente", "Mapeie a coluna que contém o número da PO."],
            missing_supplier_column: ["Missing Supplier/Company column", "Map the column that contains the Supplier.", "Coluna de fornecedor ausente", "Mapeie a coluna que contém o fornecedor."],
            mapping_same_column: ["PO and Supplier use the same column", "Choose two different columns for PO Number and Supplier.", "PO e fornecedor usam a mesma coluna", "Escolha colunas diferentes para PO e fornecedor."],
        }[group.id];
        if (!copy) return { title: group.title || group.id, message: group.message || "" };
        return { title: pt ? copy[2] : copy[0], message: pt ? copy[3] : copy[1] };
    }

    async function copyValidationValues(button, pt) {
        const values = validationCopyValues.get(button.dataset.copyId);
        if (!values) return;
        let copied = false;
        if (navigator.clipboard && navigator.clipboard.writeText) {
            try {
                await navigator.clipboard.writeText(values);
                copied = true;
            } catch (_) { copied = false; }
        }
        if (!copied) {
            const area = document.createElement("textarea");
            area.value = values;
            area.setAttribute("readonly", "true");
            area.style.position = "fixed";
            area.style.opacity = "0";
            document.body.appendChild(area);
            area.select();
            copied = document.execCommand("copy");
            area.remove();
        }
        const original = button.innerText;
        button.innerText = copied ? (pt ? "Copiado" : "Copied") : (pt ? "Falhou" : "Copy failed");
        setTimeout(() => { button.innerText = original; }, 1800);
    }

    async function renderValidation(result) {
        const feedback = $("#validation-feedback");
        const errors = Array.isArray(result.errors) ? result.errors : [];
        const warnings = Array.isArray(result.warnings) ? result.warnings : [];
        const fixes = Array.isArray(result.fixes) ? result.fixes : [];
        const groups = Array.isArray(result.groups) ? result.groups : [];
        const mapping = result.mapping || {};
        validationCopyValues.clear();
        mappingDetected = mapping.po || mapping.supplier ? mapping : (mappingDetected || {});
        mappingSuggestions = result.mapping_suggestions || mappingSuggestions;
        const pt = appSettings.language === "pt-BR";
        let html = "";
        setHierarchyColumns(result.hierarchy_columns || [], result.empty_hierarchy_columns || []);
        renderHierarchyWarnings(result.empty_hierarchy_columns || []);
        const needsMapping = groups.some((group) => group.mapping);
        if (needsMapping) {
            renderMappingCard(mappingColumns.length ? mappingColumns : (await getInputColumnsForMapping()));
        } else {
            hideMappingCard();
        }
        const issueCount = groups.length || errors.length || warnings.length;
        if (result.valid) html += `<div class="validation-success">${pt ? `Arquivo válido — ${result.valid_po_count || 0} PO(s) prontos.` : `File is valid — ${result.valid_po_count || 0} PO(s) ready.`}</div>`;
        else html += `<div class="validation-error-header">${pt ? `O arquivo precisa de correção (${issueCount} grupo(s) de problema)` : `File needs correction (${issueCount} issue group(s))`}</div>`;
        if ((groups.length || (result.empty_hierarchy_columns || []).length) && hasApi("open_filtered_input_view")) {
            const csvInput = /\.csv$/i.test(String(selectedFilePath || ""));
            const actionLabel = csvInput
                ? (pt ? "Converter e abrir no Excel" : "Convert and open in Excel")
                : (pt ? "Abrir input filtrado no Excel" : "Open filtered input in Excel");
            const actionNote = csvInput
                ? (pt ? "O CSV original será preservado; uma cópia XLSX anotada será criada para edição." : "The original CSV stays unchanged; an annotated XLSX working copy will be created for editing.")
                : (pt ? "O arquivo original será anotado; um backup será criado antes." : "The original input will be annotated; a backup is created first.");
            html += `<div class="validation-excel-actions"><button class="btn btn-primary btn-small btn-open-filtered-view" type="button">${actionLabel}</button><small>${actionNote}</small></div>`;
        }
        if (groups.length) {
            html += `<div class="validation-dashboard">`;
            groups.forEach((group) => {
                const severityClass = group.severity === "warning" ? "validation-warning" : "validation-error";
                const groupCopy = validationGroupCopy(group, pt);
                html += `<div class="validation-group"><div class="validation-group-head ${severityClass}"><strong>${escapeHtml(groupCopy.title)}</strong><span>${group.count || 0}</span></div><p>${escapeHtml(groupCopy.message)}</p>${renderAffectedValues(group, pt)}`;
                if (group.fixable && hasApi("repair_input_file")) {
                    html += `<button class="btn btn-secondary btn-small btn-fix-group" data-fix="${escapeHtml(group.fix_action)}" type="button">${pt ? "Corrigir" : "Fix"}</button>`;
                } else if (group.fixable === false && group.id !== "missing_po_column" && group.id !== "missing_supplier_column") {
                    html += `<button class="btn btn-secondary btn-small btn-open-fix" type="button">${pt ? "Abrir arquivo para corrigir" : "Open file to fix"}</button>`;
                }
                html += `</div>`;
            });
            html += `</div>`;
        }
        const standaloneErrors = groups.length ? errors.filter((error) => String(error).toLowerCase().includes("no valid po")) : errors;
        const standaloneWarnings = groups.length ? [] : warnings;
        standaloneErrors.forEach((error) => { html += `<div class="validation-error">${escapeHtml(error)}</div>`; });
        standaloneWarnings.forEach((warning) => { html += `<div class="validation-warning">${escapeHtml(warning)}</div>`; });
        fixes.forEach((fix) => { html += `<div class="validation-info">${pt ? "Correção sugerida:" : "Suggested fix:"} ${escapeHtml(fix.description || fix.action)}</div>`; });
        feedback.innerHTML = html;
        feedback.querySelectorAll(".btn-copy-affected").forEach((button) => {
            button.addEventListener("click", () => copyValidationValues(button, pt));
        });
        const filteredViewButton = feedback.querySelector(".btn-open-filtered-view");
        if (filteredViewButton) {
            filteredViewButton.addEventListener("click", async () => {
                filteredViewButton.disabled = true;
                filteredViewButton.innerText = pt ? "Preparando input…" : "Preparing input…";
                try {
                    const opened = await api().open_filtered_input_view(selectedFilePath);
                    if (!opened || !opened.success) throw new Error(opened?.error || (pt ? "Não foi possível preparar o input para correção." : "Could not prepare the input for correction."));
                    if (opened.path && opened.path !== selectedFilePath) {
                        selectedFilePath = opened.path;
                        selectedFileValidated = false;
                        validatedFingerprint = null;
                        const workingName = String(opened.path).split(/[\\/]/).pop();
                        $("#selected-filename").innerText = workingName;
                        $("#validation-filename").innerText = workingName;
                        $("#selected-filesize").innerText = pt ? "Cópia de trabalho XLSX" : "XLSX working copy";
                        $(".file-type").innerText = "XLSX";
                        $("#btn-next-hierarchy").disabled = true;
                        startFileMonitor();
                        probeColumnsForMapping();
                        updateReadyState("unauthenticated", pt ? "Cópia XLSX criada" : "XLSX working copy created", pt ? "Edite o arquivo no Excel, salve, feche e valide novamente." : "Edit the Excel file, save, close it, and validate again.");
                    }
                    logToConsole("Success", `${opened.message} ${opened.filtered_rows || 0} row(s) filtered.`);
                    filteredViewButton.innerText = pt ? "Input aberto" : "Input opened";
                } catch (error) {
                    const message = error?.message || String(error);
                    logToConsole("Error", message);
                    filteredViewButton.innerText = pt ? "Falha ao abrir" : "Open failed";
                    filteredViewButton.disabled = false;
                }
            });
        }
        feedback.querySelectorAll(".btn-fix-group").forEach((button) => {
            button.addEventListener("click", async () => {
                const action = button.dataset.fix || button.getAttribute("data-fix");
                if (!action || !selectedFilePath || !hasApi("repair_input_file")) {
                    const message = pt ? "Não foi possível identificar esta correção." : "This repair action could not be identified.";
                    logToConsole("Error", message);
                    feedback.insertAdjacentHTML("afterbegin", `<div class="validation-error">${escapeHtml(message)}</div>`);
                    return;
                }
                button.disabled = true;
                button.innerText = pt ? "Corrigindo…" : "Applying…";
                try {
                    const preview = hasApi("preview_repair_input_file")
                        ? await api().preview_repair_input_file(selectedFilePath, action)
                        : { success: true, changes: [], total_changes: 0 };
                    if (!preview || !preview.success) {
                        throw new Error(preview?.error || (pt ? "Não foi possível preparar a correção." : "Could not prepare the repair preview."));
                    }
                    const changes = Array.isArray(preview.changes) ? preview.changes : [];
                    const previewLines = changes.slice(0, 30).map((change) => `Row ${change.row} · ${change.column}: ${JSON.stringify(change.old)} → ${JSON.stringify(change.new)}`).join("\n");
                    const more = Number(preview.total_changes || changes.length) > changes.length ? `\n… and ${Number(preview.total_changes) - changes.length} more` : "";
                    const confirmation = pt
                        ? `Alterações propostas:\n${previewLines || "Nenhuma alteração de valor."}${more}\n\nSalvar estas alterações no input?`
                        : `Proposed changes:\n${previewLines || "No value changes."}${more}\n\nSave these changes to the input?`;
                    if (!window.confirm(confirmation)) {
                        button.disabled = false;
                        button.innerText = pt ? "Corrigir" : "Fix";
                        return;
                    }
                    const repaired = await api().repair_input_file(selectedFilePath, [action], preview.expected_fingerprint);
                    if (!repaired || !repaired.success) {
                        throw new Error(repaired?.error || (pt ? "Não foi possível corrigir o arquivo." : "Could not repair the file."));
                    }
                    selectedFileValidated = false;
                    validatedFingerprint = null;
                    logToConsole("Success", `${repaired.message} Backup: ${repaired.backup_path}`);
                    feedback.innerHTML = `<div class="validation-success">${escapeHtml(repaired.message)} ${pt ? "Revalidando…" : "Revalidating…"}</div>`;
                    await validateCurrentFile();
                } catch (error) {
                    const message = error?.message || String(error);
                    logToConsole("Error", message);
                    feedback.insertAdjacentHTML("afterbegin", `<div class="validation-error">${escapeHtml(message)}</div>`);
                    button.disabled = false;
                    button.innerText = pt ? "Corrigir" : "Fix";
                }
            });
        });
        feedback.querySelectorAll(".btn-open-fix").forEach((button) => {
            button.addEventListener("click", async () => {
                if (hasApi("open_input_path")) {
                    const opened = await api().open_input_path(selectedFilePath);
                    if (!opened.success) logToConsole("Error", opened.error || "Could not open the input file.");
                }
            });
        });
        feedback.hidden = false;
        selectedFileValidated = Boolean(result.valid);
        const state = result.file_state || {};
        validatedFingerprint = state.mtime_ns && state.size ? `${state.mtime_ns}:${state.size}` : null;
        $("#btn-next-hierarchy").disabled = !selectedFileValidated;
        updateReadyState(result.valid ? "authenticated" : "unauthenticated", result.valid ? (pt ? "Input validado" : "Input validated") : (pt ? "Input precisa de correção" : "Input needs correction"), result.valid ? (pt ? "Pronto para configurar o download." : "Ready to configure the download.") : (pt ? "Corrija o arquivo e valide novamente." : "Edit the same file and validate again."));
        return result;
    }

    async function getInputColumnsForMapping() {
        if (!selectedFilePath || !hasApi("get_input_columns")) return [];
        try {
            const info = await api().get_input_columns(selectedFilePath);
            if (info && info.success) {
                mappingColumns = info.columns || [];
                mappingSuggestions = info.suggestions || { po: [], supplier: [] };
                renderMappingCard(mappingColumns, info.detected, mappingSuggestions);
                return mappingColumns;
            }
        } catch (_) { /* best effort */ }
        return [];
    }

    async function validateCurrentFile() {
        if (!selectedFilePath) return { valid: false, errors: ["Please select an input file first."], warnings: [] };
        $("#btn-validate-file").disabled = true;
        $("#btn-validate-file").innerText = "Validating…";
        try {
            let result;
            if (hasApi("validate_input_file")) result = await api().validate_input_file(selectedFilePath);
            else result = { valid: true, errors: [], warnings: [], valid_po_count: 15, total_rows: 15 };
            if (result.file_state) updateFileState(result.file_state);
            return renderValidation(result);
        } catch (error) {
            const result = { valid: false, errors: [error.message || String(error)], warnings: [] };
            return renderValidation(result);
        } finally {
            $("#btn-validate-file").disabled = false;
            $("#btn-validate-file").innerText = t("validate");
        }
    }

    $("#btn-validate-file").addEventListener("click", validateCurrentFile);
    $("#btn-apply-mapping").addEventListener("click", applyColumnMapping);
    $("#btn-next-input").addEventListener("click", () => {
        if (!selectedFilePath || $("#btn-next-input").disabled) return;
        completeJourneyStep(2);
        validateCurrentFile();
    });
    $("#btn-next-hierarchy").addEventListener("click", () => completeJourneyStep(3));
    $("#btn-next-destination").addEventListener("click", () => {
        renderDestinationPreview();
        completeJourneyStep(4);
    });
    $("#btn-next-review").addEventListener("click", async () => {
        const button = $("#btn-next-review");
        if (button.disabled) return;
        button.disabled = true;
        button.innerText = appSettings.language === "pt-BR" ? "Verificando…" : "Checking…";
        const valid = await validateDestinationPath();
        button.innerText = t("reviewRun");
        button.disabled = !valid;
        if (!valid) return;
        completeJourneyStep(5);
    });
    document.querySelectorAll("[data-journey-back]").forEach((button) => button.addEventListener("click", () => showJourneyStep(Math.min(Number(button.dataset.journeyBack), journeyMaxStep))));
    document.querySelectorAll("[data-journey-step]").forEach((button) => button.addEventListener("click", () => showJourneyStep(button.dataset.journeyStep)));
    showJourneyStep(1);
    ensureDefaultDestination();

    // The folder structure is confirmed between steps 3 and 4 (preview in the
    // destination panel). The old modal no longer interrupts the start action.
    async function startRunFlow() {
        if (!selectedFilePath) {
            logToConsole("Error", "Please select an input file before starting.");
            alert("Please select an input file before starting.");
            return;
        }
        const validation = await validateCurrentFile();
        if (!validation.valid) {
            logToConsole("Error", "Fix the validation errors and validate the file again.");
            return;
        }
        if (!(await validateDestinationPath())) {
            logToConsole("Error", appSettings.language === "pt-BR" ? "Corrija a pasta de destino antes de iniciar." : "Fix the download destination before starting.");
            return;
        }

        if (!hasApi("import_file")) {
            importedSessionId = 777;
            runInProgress = true;
            showScreen("progress");
            startTelemetryPolling(importedSessionId);
            return;
        }

        $("#btn-start-run").disabled = true;
        logToConsole("System", "Checking Coupa session…");
        let authCheck = { authenticated: true };
        if (hasApi("check_auth")) authCheck = await api().check_auth();
        if (!authCheck.authenticated && authCheck.state === "unavailable" && !authCheck.has_cached_session) {
            updateAuthUI("unavailable", authCheck.message);
            logToConsole("Warning", "Coupa could not be reached to verify the session. Check connectivity and try again.");
            $("#btn-start-run").disabled = false;
            return;
        }
        if (!authCheck.authenticated && authCheck.state === "unavailable") {
            updateAuthUI("unavailable", authCheck.message);
            logToConsole("Warning", "Session verification is unavailable; the CLI will try the cached Coupa session.");
        } else if (!authCheck.authenticated) {
            const authResult = await authenticateWithProgress();
            if (!authResult.success) {
                updateAuthUI("expired", authResult.error);
                logToConsole("Error", authResult.error || "Authentication failed.");
                $("#btn-start-run").disabled = false;
                return;
            }
            updateAuthUI("authenticated");
        } else {
            updateAuthUI("authenticated", authCheck.message);
        }

        logToConsole("System", `Importing ${$("#selected-filename").innerText}…`);
        const imported = await api().import_file(selectedFilePath);
        if (!imported.success) {
            logToConsole("Error", imported.error || "Import failed.");
            $("#btn-start-run").disabled = false;
            return;
        }
        importedSessionId = imported.session_id;
        const directory = $("#download-dir").value;
        const started = await api().start_download(importedSessionId, directory, Number(appSettings.concurrency || 4), hierarchyOrder, Number(appSettings.retry_attempts || 1));
        if (!started.success) {
            logToConsole("Error", started.error || "Could not start the run.");
            $("#btn-start-run").disabled = false;
            return;
        }
        runInProgress = true;
        logToConsole("Success", `Run ${importedSessionId} started with ${imported.total_pos} PO(s).`);
        showScreen("progress");
        startTelemetryPolling(importedSessionId);
    }

    $("#btn-start-run").addEventListener("click", async () => {
        if (startRequestActive || runInProgress) return;
        startRequestActive = true;
        $("#btn-start-run").disabled = true;
        try {
            await startRunFlow();
        } catch (error) {
            logToConsole("Error", error?.message || String(error));
        } finally {
            startRequestActive = false;
            if (!runInProgress) $("#btn-start-run").disabled = false;
        }
    });

    let lastStatus = "PENDING";
    function startTelemetryPolling(sessionId) {
        runInProgress = true;
        syncUpdateButton();
        lastStatus = "PENDING";
        importedSessionId = sessionId;
        $("#active-session-title").innerText = sessionId ? `Run #${sessionId}` : "Starting CLI run…";
        $("#progress-subtitle").innerText = "Downloading attachments from Coupa.";
        $("#btn-pause-resume").disabled = false;
        $("#btn-stop-session").disabled = false;
        $("#btn-pause-resume").innerText = "Pause";
        $("#btn-pause-resume").dataset.state = "running";
        if (activePollInterval) clearInterval(activePollInterval);
        const poll = async () => {
            if (!hasApi("get_active_session_status")) return;
            try {
                const stats = await api().get_active_session_status(sessionId);
                updateProgressUI(stats);
                if (stats.session_id && stats.session_id !== importedSessionId) {
                    importedSessionId = stats.session_id;
                    $("#active-session-title").innerText = `Run #${stats.session_id}`;
                }
                if (["SUCCESS", "FAILED", "PARTIAL", "ERROR", "STOPPED", "CANCELLED"].includes(stats.status)) {
                    runInProgress = false;
                    syncUpdateButton();
                    clearInterval(activePollInterval);
                    $("#btn-stop-session").disabled = true;
                    if (stats.status === "STOPPED") {
                        $("#btn-pause-resume").disabled = false;
                        $("#btn-pause-resume").dataset.state = "paused";
                        $("#btn-pause-resume").innerText = "Resume with reconciliation";
                    } else {
                        $("#btn-pause-resume").disabled = true;
                    }
                }
            } catch (error) { logToConsole("Error", `Telemetry failed: ${error.message || error}`); }
        };
        poll();
        activePollInterval = setInterval(poll, 1000);
    }

    function updateProgressUI(stats) {
        const total = Number(stats.total || 0);
        const processed = Number(stats.processed || 0);
        const percent = total ? Math.min(100, Math.round((processed / total) * 100)) : 0;
        $("#progress-bar").style.width = `${percent}%`;
        $("#progress-text").innerText = `${percent}% (${processed}/${total})`;
        const speed = Number(stats.speed || 0);
        const stalledSeconds = Number(stats.stalled_seconds || 0);
        $("#speed-val").innerHTML = `${speed.toFixed(1)} <small>PO/min</small>`;
        $("#eta-val").innerText = stats.eta || "--:--";
        const pt = appSettings.language === "pt-BR";
        if (processed >= total && total > 0) {
            $("#speed-note").innerText = pt ? "Execução concluída" : "Run complete";
            $("#eta-note").innerText = pt ? "Sem trabalho restante" : "No work remaining";
        } else if (stalledSeconds >= 45) {
            $("#speed-note").innerText = pt ? `Nenhuma PO concluída há ${stalledSeconds}s` : `No PO completed for ${stalledSeconds}s`;
            $("#eta-note").innerText = pt ? "Aguardando novo progresso" : "Waiting for new progress";
        } else {
            $("#speed-note").innerText = pt ? "Taxa de conclusão dos últimos 60s" : "Completion rate over the last 60s";
            $("#eta-note").innerText = speed > 0 ? (pt ? "Estimado pela velocidade recente" : "Estimated from recent speed") : (pt ? "Coletando progresso recente" : "Collecting recent progress");
        }
        $("#errors-val").innerText = String(stats.errors || 0);
        $("#run-state").innerText = String(stats.status || "RUNNING");
        if (stats.status !== lastStatus) { lastStatus = stats.status; logToConsole("System", `Run status: ${stats.status}`); }
        (stats.latest_logs || []).forEach((entry) => logToConsole(entry.type, entry.message));
    }

    $("#btn-pause-resume").addEventListener("click", async () => {
        if (importedSessionId === null || !hasApi("pause_download")) return;
        const paused = $("#btn-pause-resume").dataset.state === "paused";
        if (paused && !hasApi("resume_download")) return;
        const result = paused ? await api().resume_download(importedSessionId) : await api().pause_download(importedSessionId);
        if (!result.success) { logToConsole("Error", result.error || "Could not update run state."); return; }
        if (paused) {
            const reconciled = result.reconciliation ? result.reconciliation.count : 0;
            logToConsole("System", `Reconciliation complete: ${reconciled} PO(s) reset for verification. Resuming pending and failed POs…`);
            $("#btn-pause-resume").disabled = true;
            startTelemetryPolling(result.session_id || 0);
        } else {
            $("#btn-pause-resume").dataset.state = "paused";
            $("#btn-pause-resume").innerText = "Stopping safely…";
            $("#btn-pause-resume").disabled = true;
            logToConsole("System", "Pause requested. Waiting for the current operation to finish safely…");
        }
    });

    $("#btn-stop-session").addEventListener("click", async () => {
        if (importedSessionId === null || !hasApi("stop_download")) return;
        if (!confirm("Stop this run? Active requests will finish before the queue stops.")) return;
        const result = await api().stop_download(importedSessionId);
        if (!result.success) { logToConsole("Error", result.error || "Could not stop run."); return; }
        logToConsole("System", "Stop requested. Waiting current operation to end...");
    });
    $("#btn-clear-log").addEventListener("click", () => { $("#console-log").innerHTML = ""; });

    async function deleteRun(button) {
        if (!hasApi("delete_session")) {
            alert("Run deletion is available in the desktop app.");
            return;
        }
        const sessionId = button.dataset.id;
        const inputName = button.dataset.input || "this run";
        const confirmed = confirm(`Delete run #${sessionId} (${inputName}) and all files in its run folder?\n\nThis cannot be undone. The original input file outside the run folder will be preserved.`);
        if (!confirmed) return;
        button.disabled = true;
        const result = await api().delete_session(Number(sessionId));
        if (!result.success) {
            button.disabled = false;
            alert(result.error || "Could not delete the run.");
            return;
        }
        if (currentDetails && String(currentDetails.session?.id) === String(sessionId)) {
            $("#details-modal").hidden = true;
            currentDetails = null;
        }
        logToConsole("Success", `Run #${sessionId} and its run files were deleted.`);
        await loadHistory();
    }

    let concurrencyEstimates = {};
    function renderConcurrencyEstimate() {
        const selected = String($("#settings-concurrency").value || "4");
        const estimate = concurrencyEstimates[selected];
        $("#settings-concurrency-estimate").innerText = estimate && estimate.minutes_100
            ? `Estimated time for 100 POs: about ${estimate.minutes_100} minutes (${estimate.samples} completed run${estimate.samples === 1 ? "" : "s"}).`
            : "Estimated time for 100 POs will be calculated after a completed run with this setting.";
    }

    async function loadConcurrencyEstimates() {
        if (!hasApi("get_concurrency_estimates")) {
            renderConcurrencyEstimate();
            return;
        }
        concurrencyEstimates = await api().get_concurrency_estimates();
        renderConcurrencyEstimate();
    }

    function syncAuthBrowserOptions() {
        const option = $("#settings-auth-browser option[value='auto']");
        if (!option) return;
        const defaultName = appSettings.auth_browsers?.system_default_name;
        const pt = appSettings.language === "pt-BR";
        option.innerText = defaultName
            ? (pt ? `Automático — padrão do sistema: ${defaultName}` : `Automatic — system default: ${defaultName}`)
            : (pt ? "Automático — navegador suportado disponível" : "Automatic — available supported browser");
    }

    async function loadSettings() {
        if (!hasApi("get_app_settings")) {
            renderConcurrencyEstimate();
            return;
        }
        const result = await api().get_app_settings();
        if (!result) return;
        appSettings = { ...appSettings, ...result };
        $("#settings-language").value = appSettings.language || "en";
        $("#settings-font-scale").value = String(appSettings.font_scale || 1.1);
        applyFontScale();
        applyLanguage();
        $("#settings-download-root").value = appSettings.download_root || "";
        $("#settings-concurrency").value = String(appSettings.concurrency || 4);
        $("#settings-retry").value = String(appSettings.retry_attempts || 1);
        $("#settings-auth-browser").value = String(appSettings.auth_browser || "auto");
        const availableBrowsers = new Set((appSettings.auth_browsers?.available || []).map((item) => item.id));
        $("#settings-auth-browser").querySelectorAll("option[value='edge'], option[value='chrome']").forEach((option) => {
            option.disabled = availableBrowsers.size > 0 && !availableBrowsers.has(option.value);
        });
        $("#settings-msg-processing").value = String(appSettings.msg_processing || "convert_extract");
        $("#settings-deduplicate").checked = Boolean(appSettings.deduplicate_files);
        $("#settings-auto-updates").checked = Boolean(appSettings.auto_updates);
        $("#settings-retention").value = String(appSettings.retention || "all");
        await loadConcurrencyEstimates();
    }

    async function saveSettings() {
        const values = {
            download_root: $("#settings-download-root").value.trim(),
            concurrency: Number($("#settings-concurrency").value),
            retry_attempts: Number($("#settings-retry").value),
            auth_browser: $("#settings-auth-browser").value,
            msg_processing: $("#settings-msg-processing").value,
            deduplicate_files: $("#settings-deduplicate").checked,
            auto_updates: $("#settings-auto-updates").checked,
            retention: $("#settings-retention").value,
            language: $("#settings-language").value,
            font_scale: Number($("#settings-font-scale").value),
        };
        if (!values.download_root) {
            $("#settings-status").innerText = "Choose a default download folder first.";
            return;
        }
        if (!hasApi("set_app_settings")) {
            appSettings = { ...appSettings, ...values };
            applyFontScale();
            $("#settings-status").innerText = "Settings updated for this session.";
            return;
        }
        const result = await api().set_app_settings(values);
        if (!result.success) {
            $("#settings-status").innerText = result.error || "Could not save settings.";
            return;
        }
        appSettings = { ...appSettings, ...result.settings };
        applyFontScale();
        applyLanguage();
        $("#settings-language").value = appSettings.language;
        $("#settings-status").innerText = appSettings.language === "pt-BR" ? "Configurações salvas neste computador." : "Settings saved on this computer.";
        if (appSettings.auto_updates) checkForUpdates();
    }

    $("#settings-concurrency").addEventListener("change", renderConcurrencyEstimate);
    $("#settings-language").addEventListener("change", () => { appSettings.language = $("#settings-language").value; applyLanguage(); });
    $("#settings-font-scale").addEventListener("change", () => applyFontScale($("#settings-font-scale").value));
    $("#btn-save-settings").addEventListener("click", saveSettings);
    $("#btn-check-updates").addEventListener("click", () => checkForUpdates(true));
    $("#btn-reset-auth").addEventListener("click", async () => {
        if (!hasApi("reset_authentication")) return;
        const pt = appSettings.language === "pt-BR";
        const confirmed = confirm(pt
            ? "Zerar o login do Coupa? O cache e o perfil exclusivo do aplicativo serão removidos. Seus perfis pessoais, downloads, inputs e relatórios serão preservados. Feche uma janela de login do aplicativo se ela ainda estiver aberta."
            : "Reset Coupa sign-in? The cache and the app-owned sign-in profile will be removed. Your personal browser profiles, downloads, inputs, and reports will be preserved. Close an app sign-in window if it is still open.");
        if (!confirmed) return;
        const button = $("#btn-reset-auth");
        button.disabled = true;
        const result = await api().reset_authentication();
        button.disabled = false;
        if (!result.success) {
            $("#settings-status").innerText = result.error || (pt ? "Não foi possível zerar o login." : "Could not reset sign-in state.");
            return;
        }
        updateAuthUI("unauthenticated");
        $("#settings-status").innerText = pt ? "Estado do login zerado. Clique em Sign in para autenticar novamente." : "Sign-in state reset. Click Sign in to authenticate again.";
        logToConsole("System", pt ? "Coupa sign-in state reset." : "Coupa sign-in state reset.");
    });
    $("#btn-reset-settings").addEventListener("click", async () => {
        $("#settings-download-root").value = "";
        $("#settings-concurrency").value = "4";
        $("#settings-retry").value = "1";
        $("#settings-auth-browser").value = "auto";
        $("#settings-font-scale").value = "1.1";
        applyFontScale(1.1);
        $("#settings-msg-processing").value = "convert_extract";
        $("#settings-deduplicate").checked = true;
        $("#settings-auto-updates").checked = !appSettings.python_portable;
        $("#settings-retention").value = "all";
        await ensureDefaultDestination();
        $("#settings-download-root").value = $("#download-dir").value.replace(/[\\/]run_[^\\/]+$/, "");
        await saveSettings();
    });
    $("#btn-reset-application").addEventListener("click", async () => {
        if (!hasApi("reset_application_state")) return;
        const pt = appSettings.language === "pt-BR";
        const confirmed = confirm(pt
            ? "Começar limpo? O histórico local, sessões e login serão apagados. Downloads, relatórios e inputs serão preservados. Feche uma janela de login do aplicativo e pare qualquer execução antes de continuar."
            : "Start clean? Local history, sessions, and sign-in state will be cleared. Downloads, reports, and inputs will be preserved. Close an app sign-in window and stop any active run before continuing.");
        if (!confirmed) return;
        const button = $("#btn-reset-application");
        button.disabled = true;
        const result = await api().reset_application_state();
        button.disabled = false;
        if (!result.success) {
            $("#settings-status").innerText = result.error || (pt ? "Não foi possível zerar o estado local." : "Could not reset local state.");
            return;
        }
        updateAuthUI("unauthenticated");
        pendingUpdate = null;
        syncUpdateButton();
        $("#settings-status").innerText = pt ? "Estado local zerado. Arquivos do usuário foram preservados." : "Local state reset. User files were preserved.";
        logToConsole("System", pt ? "Local application state reset." : "Local application state reset.");
        await loadHistory();
    });
    $("#btn-settings-choose-dir").addEventListener("click", async () => {
        if (!hasApi("select_directory")) return;
        const path = await api().select_directory();
        if (path) $("#settings-download-root").value = path.replace(/[\\/]run_[^\\/]+$/, "");
    });

    async function clearAllHistory() {
        if (!hasApi("clear_all_sessions")) {
            alert("History cleanup is available in the desktop app.");
            return;
        }
        const confirmed = confirm("Delete every run, all run folders, reports, attachments, and archived inputs?\n\nThis cannot be undone. Original input files outside run folders will be preserved. Run numbering will restart at #1.");
        if (!confirmed) return;
        const button = $("#btn-clear-history");
        button.disabled = true;
        const result = await api().clear_all_sessions();
        button.disabled = false;
        if (!result.success) {
            alert(result.error || "Could not clear run history.");
            return;
        }
        $("#details-modal").hidden = true;
        currentDetails = null;
        logToConsole("Success", "All run history and run folders were deleted. The next run will be #1.");
        await loadHistory();
    }

    $("#btn-clear-history").addEventListener("click", clearAllHistory);

    async function loadHistory() {
        const body = $("#history-list");
        body.innerHTML = '<tr><td colspan="7" class="empty-state">Loading runs…</td></tr>';
        if (!hasApi("get_session_history")) {
            body.innerHTML = '<tr><td colspan="7" class="empty-state">History is available in the desktop app.</td></tr>';
            return;
        }
        try {
            const history = await api().get_session_history();
            if (!history.length) { body.innerHTML = '<tr><td colspan="7" class="empty-state">No runs yet.</td></tr>'; return; }
            const pt = appSettings.language === "pt-BR";
            body.innerHTML = history.map((session) => {
                const status = String(session.status || "PENDING").toUpperCase();
                const description = String(session.description || "").trim();
                const descriptionCell = description
                    ? `<td class="run-description-cell" title="${escapeHtml(description)}">${escapeHtml(description.length > 60 ? description.slice(0, 60) + "…" : description)}</td>`
                    : '<td class="run-description-cell empty">—</td>';
                return `<tr><td>#${session.id}</td><td><button class="coupa-link history-input-link" data-session="${session.id}" title="${pt ? "Abrir o input preservado desta execução" : "Open this run's preserved input"}" type="button">${escapeHtml(session.input_file)}</button></td>${descriptionCell}<td>${escapeHtml(new Date(session.created_at).toLocaleString())}</td><td>${session.total_pos || 0}</td><td><span class="status-badge status-${status.toLowerCase()}">${status}</span></td><td class="history-actions"><button class="btn btn-secondary btn-small btn-view-details" data-id="${session.id}" type="button">${pt ? "Detalhes" : "Details"}</button><button class="btn btn-danger btn-small btn-delete-run" data-id="${session.id}" data-input="${escapeHtml(session.input_file || "")}" type="button">${pt ? "Excluir" : "Delete"}</button></td></tr>`;
            }).join("");
            body.querySelectorAll(".btn-view-details").forEach((button) => button.addEventListener("click", () => openDetailsModal(button.dataset.id)));
            body.querySelectorAll(".btn-delete-run").forEach((button) => button.addEventListener("click", () => deleteRun(button)));
            body.querySelectorAll(".history-input-link").forEach((button) => button.addEventListener("click", async () => {
                if (!hasApi("open_input_file")) {
                    logToConsole("Warning", "Input opening is available in the desktop app.");
                    return;
                }
                const result = await api().open_input_file(Number(button.dataset.session));
                if (!result.success) logToConsole("Error", result.error || "Could not open the preserved input file.");
            }));
        } catch (error) { body.innerHTML = `<tr><td colspan="7" class="empty-state">Could not load history: ${escapeHtml(error.message || error)}</td></tr>`; }
    }

    const modal = $("#details-modal");
    const retryEditModal = $("#retry-edit-modal");
    const retryResultModal = $("#retry-result-modal");
    let currentDetails = null;
    let pendingRetryPo = null;
    let retryDecisionResolver = null;
    $("#btn-close-modal").addEventListener("click", () => { modal.hidden = true; });

    function selectedStatusFilters() {
        return [...document.querySelectorAll("#status-filter input[data-status]:checked")].map((input) => input.dataset.status);
    }

    function syncStatusFilterControls() {
        const options = [...document.querySelectorAll("#status-filter input[data-status]")];
        const selected = options.filter((input) => input.checked).length;
        const all = $("#status-filter input[data-status-all]");
        all.checked = selected === options.length;
        all.indeterminate = selected > 0 && selected < options.length;
    }

    function coupaUrl(po) {
        if (po.coupa_url) return String(po.coupa_url);
        const value = String(po.po_number || "").trim();
        const orderNumber = /^(PO|PM)/i.test(value) ? value.slice(2) : value;
        return `https://unilever.coupahost.com/order_headers/${encodeURIComponent(orderNumber)}`;
    }

    function renderDetailsRows() {
        if (!currentDetails) return;
        const filters = selectedStatusFilters();
        const rows = currentDetails.pos.filter((po) => filters.includes(String(po.status).toUpperCase()));
        $("#modal-pos-tbody").innerHTML = rows.map((po) => `<tr><td><button class="coupa-link po-number-link" data-po="${escapeHtml(po.po_number)}" title="Open ${escapeHtml(po.po_number)} in the default browser" type="button">${escapeHtml(po.po_number)}</button></td><td>${escapeHtml(po.company_code)}</td><td><span class="status-badge status-${String(po.status).toLowerCase()}">${escapeHtml(po.status)}</span></td><td><button class="btn btn-secondary btn-small btn-po-retry" data-po="${escapeHtml(po.po_number)}" type="button">Retry</button></td><td class="message-cell">${escapeHtml(po.remarks || po.error_message || "No error message recorded")}</td></tr>`).join("") || '<tr><td colspan="5" class="empty-state">No POs match this filter.</td></tr>';
        $("#modal-pos-tbody").querySelectorAll(".btn-po-retry").forEach((button) => {
            button.addEventListener("click", () => retrySinglePo(button));
        });
        syncStatusFilterControls();
    }

    async function openPoInBrowser(button) {
        const poNumber = button.dataset.po || "";
        if (!hasApi("open_coupa_po") && !hasApi("open_external_url")) {
            alert("Browser integration is unavailable in this build.");
            return;
        }
        button.disabled = true;
        button.classList.add("opening");
        try {
            const result = hasApi("open_coupa_po")
                ? await api().open_coupa_po(poNumber)
                : await api().open_external_url(coupaUrl({ po_number: poNumber }));
            if (!result.success) {
                const message = result.error || `Could not open PO ${poNumber} in the browser.`;
                logToConsole("Error", message);
                alert(message);
            }
        } catch (error) {
            const message = `Could not open PO ${poNumber}: ${error.message || error}`;
            logToConsole("Error", message);
            alert(message);
        } finally {
            button.disabled = false;
            button.classList.remove("opening");
        }
    }

    // Delegation survives every table refresh/filter operation and avoids
    // losing click handlers when the PO rows are rebuilt with innerHTML.
    $("#modal-pos-tbody").addEventListener("click", (event) => {
        const button = event.target.closest(".po-number-link");
        if (button) openPoInBrowser(button);
    });

    function openRetryEditModal(poNumber) {
        pendingRetryPo = { sessionId: currentDetails.session.id, original: poNumber };
        $("#retry-po-input").value = poNumber;
        retryEditModal.hidden = false;
        $("#retry-po-input").focus();
        $("#retry-po-input").select();
    }

    function closeRetryEditModal() {
        pendingRetryPo = null;
        retryEditModal.hidden = true;
    }

    async function beginRetryAttempt() {
        if (!pendingRetryPo || !hasApi("retry_po_with_edit")) return;
        const edited = $("#retry-po-input").value.trim();
        if (!edited) {
            alert("Enter a PO number before retrying.");
            return;
        }
        const confirmButton = $("#btn-confirm-retry-edit");
        confirmButton.disabled = true;
        const request = pendingRetryPo;
        const result = await api().retry_po_with_edit(request.sessionId, request.original, edited);
        confirmButton.disabled = false;
        if (!result.success) {
            alert(result.error || "PO retry could not be started.");
            return;
        }
        closeRetryEditModal();
        modal.hidden = true;
        if (result.attempt_id) {
            startProvisionalRetryPolling(result.session_id || request.sessionId, result.attempt_id);
        } else {
            importedSessionId = result.session_id || request.sessionId;
            showScreen("progress");
            startTelemetryPolling(importedSessionId);
        }
    }

    function requestRetryResultDecision(status) {
        $("#retry-result-title").innerText = "Retry succeeded";
        $("#retry-result-message").innerText = `The corrected PO ${status.edited_po} was found and ${status.attachment_count || 0} attachment(s) were downloaded.`;
        retryResultModal.hidden = false;
        return new Promise((resolve) => { retryDecisionResolver = resolve; });
    }

    function resolveRetryResultDecision(decision) {
        retryResultModal.hidden = true;
        if (retryDecisionResolver) {
            const resolve = retryDecisionResolver;
            retryDecisionResolver = null;
            resolve(decision);
        }
    }

    async function finishProvisionalRetry(sessionId, attemptId, status) {
        runInProgress = false;
        syncUpdateButton();
        $("#btn-stop-session").disabled = true;
        $("#btn-pause-resume").disabled = true;
        if (status.status === "SUCCESS") {
            const decision = await requestRetryResultDecision(status);
            const keep = decision === "save";
            const result = keep
                ? await api().save_retry_attempt(attemptId)
                : await api().discard_retry_attempt(attemptId);
            if (!result.success) {
                alert(result.error || "Could not finalize the retry result.");
                return;
            }
            logToConsole(keep ? "Success" : "System", keep ? "PO correction saved to the input and report." : "Successful retry discarded; the run was left unchanged.");
        } else {
            await api().discard_retry_attempt(attemptId);
            alert(status.error_message || `Retry failed for ${status.edited_po}. The original error was preserved.`);
        }
        await openDetailsModal(sessionId);
    }

    function startProvisionalRetryPolling(sessionId, attemptId) {
        runInProgress = true;
        syncUpdateButton();
        importedSessionId = sessionId;
        showScreen("progress");
        $("#active-session-title").innerText = `Run #${sessionId}`;
        $("#progress-subtitle").innerText = "Testing the corrected PO before saving it.";
        $("#btn-pause-resume").disabled = true;
        $("#btn-stop-session").disabled = true;
        if (activePollInterval) clearInterval(activePollInterval);
        const poll = async () => {
            try {
                const status = await api().get_retry_attempt_status(attemptId);
                if (!status.success) throw new Error(status.error || "Retry status unavailable.");
                const finished = ["SUCCESS", "FAILED"].includes(status.status);
                updateProgressUI({
                    status: status.status,
                    total: 1,
                    processed: finished ? 1 : 0,
                    success: status.status === "SUCCESS" ? 1 : 0,
                    errors: status.status === "FAILED" ? 1 : 0,
                    latest_logs: [],
                });
                if (finished) {
                    clearInterval(activePollInterval);
                    await finishProvisionalRetry(sessionId, attemptId, status);
                }
            } catch (error) {
                logToConsole("Error", `Retry status failed: ${error.message || error}`);
            }
        };
        poll();
        activePollInterval = setInterval(poll, 700);
    }

    async function retrySinglePo(button) {
        if (!currentDetails || !hasApi("retry_po_with_edit")) return;
        openRetryEditModal(button.dataset.po || "");
    }

    $("#btn-close-retry-edit").addEventListener("click", closeRetryEditModal);
    $("#btn-cancel-retry-edit").addEventListener("click", closeRetryEditModal);
    $("#btn-confirm-retry-edit").addEventListener("click", beginRetryAttempt);
    $("#btn-save-retry-result").addEventListener("click", () => resolveRetryResultDecision("save"));
    $("#btn-discard-retry-result").addEventListener("click", () => resolveRetryResultDecision("discard"));
    $("#retry-po-input").addEventListener("keydown", (event) => {
        if (event.key === "Enter") beginRetryAttempt();
        if (event.key === "Escape") closeRetryEditModal();
    });

    $("#status-filter").addEventListener("change", (event) => {
        if (event.target.matches("input[data-status-all]")) {
            document.querySelectorAll("#status-filter input[data-status]").forEach((input) => { input.checked = event.target.checked; });
        }
        renderDetailsRows();
    });
    async function openDetailsModal(sessionId) {
        if (!hasApi("get_session_details")) return;
        currentDetails = await api().get_session_details(sessionId);
        if (!currentDetails || !currentDetails.session) {
            currentDetails = null;
            alert(`Run #${sessionId} could not be found.`);
            return;
        }
        currentDetails.pos = Array.isArray(currentDetails.pos) ? currentDetails.pos : [];
        modal.hidden = false;
        $("#modal-title").innerText = `Run #${sessionId}`;
        $("#modal-file").innerText = currentDetails.session.input_file;
        $("#modal-status").innerText = currentDetails.session.status;
        const descriptionInput = $("#run-description-input");
        descriptionInput.value = currentDetails.session.description || "";
        $("#btn-save-run-description").onclick = async () => {
            if (!hasApi("set_run_description")) {
                alert("Run description saving is available in the desktop app.");
                return;
            }
            const button = $("#btn-save-run-description");
            button.disabled = true;
            const result = await api().set_run_description(sessionId, descriptionInput.value.trim());
            button.disabled = false;
            if (!result.success) {
                logToConsole("Error", result.error || "Could not save the run description.");
                return;
            }
            currentDetails.session.description = descriptionInput.value.trim();
            logToConsole("Success", appSettings.language === "pt-BR" ? "Descrição da execução salva." : "Run description saved.");
            loadHistory();
        };
        descriptionInput.addEventListener("keydown", (event) => {
            if (event.key === "Enter") $("#btn-save-run-description").click();
        });
        const retryEvents = currentDetails.retry_events || [];
        $("#retry-history-list").hidden = !retryEvents.length;
        $("#retry-history-items").innerHTML = retryEvents.map((event) => `<li>${escapeHtml(event.po_number || "All errors")} · ${escapeHtml(event.status_before || "—")} → ${escapeHtml(event.status_after || "PENDING")} · ${escapeHtml(event.completed_at || event.requested_at || "")}</li>`).join("");
        $("#btn-open-input").onclick = async () => {
            if (!hasApi("open_input_file")) {
                alert("Input file opening is available in the desktop app.");
                return;
            }
            const result = await api().open_input_file(sessionId);
            if (!result.success) alert(result.error || "Could not open the preserved input file.");
        };
        document.querySelectorAll("#status-filter input[data-status]").forEach((input) => { input.checked = true; });
        syncStatusFilterControls();
        const companies = [...new Set(currentDetails.pos.map((po) => po.company_code))];
        $("#company-status-items").innerHTML = companies.map((company) => {
            const rows = currentDetails.pos.filter((po) => po.company_code === company);
            const success = rows.filter((po) => po.status === "SUCCESS").length;
            const errors = rows.filter((po) => ["ERROR", "SKIPPED_VERIFICATION_REQUIRED"].includes(po.status)).length;
            const pending = rows.filter((po) => po.status === "PENDING").length;
            const suspended = rows.some((po) => po.status === "SKIPPED_VERIFICATION_REQUIRED");
            const explanation = suspended ? "verification required / circuit breaker" : "normal processing";
            return `<li class="company-badge ${suspended ? "suspended" : ""}"><strong>${escapeHtml(company)}</strong><span>${rows.length} POs · ${success} success · ${errors} errors · ${pending} pending</span><small>${explanation}</small></li>`;
        }).join("");
        renderDetailsRows();
        $("#btn-export-modal-report").onclick = async () => {
            const result = await api().export_session_report(sessionId, `report_session_${sessionId}.xlsx`);
            alert(result.success ? `Report exported to ${result.filepath || "the selected location"}.` : `Export failed: ${result.error}`);
        };
        $("#btn-retry-errors").onclick = async () => {
            if (!hasApi("retry_errors")) return;
            const errorCount = currentDetails.pos.filter((po) => ["ERROR", "SKIPPED_VERIFICATION_REQUIRED"].includes(po.status)).length;
            if (!errorCount || !confirm(`Retry ${errorCount} failed PO(s) in the same run folder?`)) return;
            const result = await api().retry_errors(sessionId);
            if (result.success) {
                modal.hidden = true;
                importedSessionId = result.session_id || 0;
                showScreen("progress");
                startTelemetryPolling(importedSessionId);
            } else alert(result.error || "Retry could not be started.");
        };
    }

    let diagnosticsReport = "";
    let diagnosticsReady = false;
    const setDiagnosticsActions = (enabled) => {
        diagnosticsReady = enabled;
        $("#btn-save-diagnostics").disabled = !enabled;
        $("#btn-copy-diagnostics").disabled = !enabled;
    };
    $("#btn-diagnostics").addEventListener("click", async () => {
        const modal = $("#diagnostics-modal");
        const reportBox = $("#diagnostics-report");
        modal.hidden = false;
        setDiagnosticsActions(false);
        diagnosticsReport = "";
        reportBox.innerText = "Running diagnostics…";
        try {
            if (!hasApi("run_diagnostics")) {
                diagnosticsReport = "Diagnostics are available in the desktop app.";
            } else {
                const result = await api().run_diagnostics(selectedFilePath || "");
                diagnosticsReport = result.success
                    ? result.report
                    : `Diagnostic failed: ${result.error || "Unknown error"}`;
            }
        } catch (error) {
            diagnosticsReport = `Diagnostic failed: ${error.message || "Unknown error"}`;
        } finally {
            reportBox.innerText = diagnosticsReport;
            setDiagnosticsActions(true);
        }
    });
    $("#btn-close-diagnostics").addEventListener("click", () => { $("#diagnostics-modal").hidden = true; });
    $("#btn-copy-diagnostics").addEventListener("click", async () => {
        if (!diagnosticsReady) return;
        let copied = false;
        if (hasApi("copy_diagnostics_report")) {
            const result = await api().copy_diagnostics_report(diagnosticsReport);
            copied = Boolean(result.success);
        }
        if (!copied && navigator.clipboard) {
            try { await navigator.clipboard.writeText(diagnosticsReport); copied = true; } catch (_) { copied = false; }
        }
        if (!copied) {
            const area = document.createElement("textarea");
            area.value = diagnosticsReport;
            document.body.appendChild(area);
            area.select();
            copied = document.execCommand("copy");
            area.remove();
        }
        $("#btn-copy-diagnostics").innerText = copied ? "Copied" : "Copy failed";
        setTimeout(() => { $("#btn-copy-diagnostics").innerText = "Copy report"; }, 1800);
    });
    $("#btn-save-diagnostics").addEventListener("click", async () => {
        if (!diagnosticsReady || !hasApi("save_diagnostics_report")) return;
        const result = await api().save_diagnostics_report(diagnosticsReport);
        if (result.success) alert(`Report saved to:\n${result.path}`);
    });

    $("#btn-authenticate").addEventListener("click", async () => {
        const result = await authenticateWithProgress();
        if (result.success) {
            updateAuthUI("authenticated");
            logToConsole("Success", "Coupa authentication successful.");
        } else {
            updateAuthUI("expired", result.error);
            logToConsole("Error", result.error || "Authentication failed.");
        }
    });

    async function initializeAuth() {
        if (!hasApi("check_auth")) { updateAuthUI("authenticated", "Browser preview"); return; }
        try {
            const result = await api().check_auth();
            if (result.authenticated || result.state === "unavailable") {
                updateAuthUI(result.authenticated ? "authenticated" : "unavailable", result.message);
                return;
            }

            // First launch and an expired Coupa session both require one
            // explicit, visible sign-in in the app-owned browser profile.
            const authResult = await authenticateWithProgress();
            if (authResult.success) {
                updateAuthUI("authenticated");
                logToConsole("Success", appSettings.language === "pt-BR" ? "Login do Coupa concluído." : "Coupa sign-in completed.");
            } else {
                updateAuthUI("expired", authResult.error);
                logToConsole("Error", authResult.error || "Authentication failed.");
            }
        } catch (error) {
            updateAuthUI("unavailable", error.message);
            logToConsole("Warning", error.message || "Could not check the Coupa session.");
        }
    }

    async function checkForUpdates(manual = false) {
        if ((!manual && !appSettings.auto_updates) || !hasApi("check_updates")) return;
        const manualButton = $("#btn-check-updates");
        if (manual) {
            manualButton.disabled = true;
            manualButton.innerText = appSettings.language === "pt-BR" ? "Verificando…" : "Checking…";
            $("#settings-status").innerText = appSettings.language === "pt-BR" ? "Verificando atualizações…" : "Checking for updates…";
        }
        try {
            const result = await api().check_updates();
            if (!result.success || !result.update_available) {
                pendingUpdate = null;
                syncUpdateButton();
                if (manual) {
                    $("#settings-status").innerText = result.success
                        ? (appSettings.language === "pt-BR" ? "Você já está usando a versão mais recente." : "You are already using the latest version.")
                        : (result.error || "Update check failed.");
                }
                return;
            }
            pendingUpdate = result;
            const banner = $("#update-banner");
            banner.hidden = false;
            $("#update-text").innerText = `Version ${result.version} available`;
            syncUpdateButton();
            if (manual) {
                $("#settings-status").innerText = appSettings.language === "pt-BR"
                    ? `Versão ${result.version} disponível. Use o botão de download acima.`
                    : `Version ${result.version} is available. Use the download button above.`;
                $(".main-content").scrollTop = 0;
            }
            $("#btn-download-update").onclick = async () => {
                if (runInProgress || !pendingUpdate) return;
                const button = $("#btn-download-update");
                button.disabled = true;
                button.innerText = "Downloading…";
                const downloaded = await api().download_update(result.download_url, result.asset_name, result.checksum_url);
                if (!downloaded.success) {
                    button.innerText = "Download update";
                    syncUpdateButton();
                    logToConsole("Error", downloaded.error || "Update download failed.");
                    return;
                }
                button.innerText = "Installing…";
                logToConsole("Success", `Update downloaded and verified. Installing version ${result.version}…`);
                if (!hasApi("install_update")) {
                    button.innerText = "Downloaded";
                    logToConsole("Warning", `Automatic installation is unavailable. Package saved at ${downloaded.path}`);
                    syncUpdateButton();
                    return;
                }
                const installed = await api().install_update(downloaded.path);
                if (!installed.success) {
                    button.innerText = "Install update";
                    syncUpdateButton();
                    logToConsole("Error", installed.error || "Update installation failed.");
                    return;
                }
                button.innerText = "Restarting…";
                logToConsole("Success", "The application will restart with the new version.");
            };
        } catch (error) {
            // Update checks are best-effort and never block normal usage.
            console.debug("Update check skipped", error);
            if (manual) $("#settings-status").innerText = error.message || "Update check failed.";
        } finally {
            if (manual) {
                manualButton.disabled = false;
                manualButton.innerText = appSettings.language === "pt-BR" ? "Verificar agora" : "Check now";
            }
        }
    }

    let startupChecksDone = false;
    let startupChecksStarted = false;
    async function runStartupChecks() {
        // pywebviewready and the fallback timer can fire close together. Set
        // the guard before awaiting the bridge so startup cannot start two
        // authentication flows and two browser windows.
        if (startupChecksDone || startupChecksStarted) return;
        startupChecksStarted = true;
        // The pywebview bridge may not be exposed yet when the fallback timer
        // fires; retry until the API is actually available so the saved
        // language/font settings are applied on the first render.
        let attempts = 0;
        while (!hasApi("get_app_settings") && attempts < 40) {
            await new Promise((resolve) => setTimeout(resolve, 250));
            attempts += 1;
        }        startupChecksDone = true;
        await loadSettings();
        await initializeAuth();
        checkForUpdates();
    }
    window.addEventListener("pywebviewready", runStartupChecks);
    setTimeout(runStartupChecks, 150);
});
