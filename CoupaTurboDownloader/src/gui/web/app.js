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
    let draggedHierarchyItem = null;
    let runInProgress = false;
    let pendingUpdate = null;
    let appSettings = { download_root: "", concurrency: 4, retry_attempts: 1, msg_processing: "convert_extract", deduplicate_files: true, auto_updates: true, retention: "all", language: "en", font_scale: 1.1, python_portable: false };
    let journeyStep = 1;
    let journeyMaxStep = 1;
    const journeyContent = {
        en: {
            1: ["Choose your input", "Start with a completed CSV or Excel file, or create a new template."],
            2: ["Validate your input", "Check the file before configuring the download."],
            3: ["Arrange folder hierarchy", "Choose the order used to create destination folders."],
            4: ["Choose the save location", "Select where this run should store its attachments."],
            5: ["Review and start", "Confirm the settings, then start the download."],
        },
        "pt-BR": {
            1: ["Escolha o input", "Comece com um arquivo CSV ou Excel preenchido, ou crie um novo template."],
            2: ["Valide o input", "Verifique o arquivo antes de configurar o download."],
            3: ["Organize a hierarquia", "Escolha a ordem usada para criar as pastas de destino."],
            4: ["Escolha o local de salvamento", "Selecione onde esta execução deve salvar os anexos."],
            5: ["Revise e inicie", "Confirme as configurações e inicie o download."],
        },
    };

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
        const content = journeyContent[appSettings.language] || journeyContent.en;
        $("#journey-title").innerText = content[journeyStep][0];
        $("#journey-subtitle").innerText = content[journeyStep][1];
        document.querySelectorAll("[data-journey-step] span").forEach((element, index) => { element.innerText = (appSettings.language === "pt-BR" ? ["Input", "Validar", "Pastas", "Destino", "Iniciar"] : ["Input", "Validate", "Folders", "Destination", "Start"])[index]; });
        document.querySelectorAll(".learn-card h3").forEach((element, index) => { element.innerText = (appSettings.language === "pt-BR" ? ["Prepare o input", "Siga a jornada", "O que acontece durante uma execução?", "Erros e retries", "Histórico e relatórios", "Autenticação e privacidade"] : ["Prepare the input", "Follow the journey", "What happens during a run?", "Errors and retries", "History and reports", "Authentication and privacy"])[index]; });
        const learnParagraphs = appSettings.language === "pt-BR" ? ["Use um arquivo Excel ou CSV com PO_NUMBER e SUPPLIER. O template inclui o separador <|>. Salve e feche o Excel antes de validar.", "A jornada possui cinco etapas: input, validação, pastas, destino e revisão. A execução só é criada após a confirmação final.", "O app usa requisições HTTP autenticadas para o Coupa, lê páginas de PO e PR, encontra anexos e os salva na pasta da execução.", "Abra Active Run para acompanhar o progresso e os logs. Retries automáticos podem ser configurados em Settings, e POs com erro também podem ser refeitos pelo histórico.", "O histórico armazena resultados por PO, retries, inputs preservados, relatórios e links para o Coupa. É possível excluir uma execução ou todo o histórico.", "A autenticação reutiliza o perfil do Edge e a sessão em cache até o Coupa invalidá-la. O app não envia telemetria." ] : ["Use an Excel or CSV file with PO_NUMBER and SUPPLIER. The template includes the <|> separator. Save and close Excel before validating.", "The journey has five stages: input, validation, folders, destination, and review. A run is created only after final confirmation.", "The app uses authenticated HTTP requests to Coupa, reads PO and PR pages, discovers attachments, and saves them inside the run folder.", "Open Active Run to monitor progress and logs. Automatic retries can be configured in Settings, and failed POs can also be retried manually from History.", "History stores PO-level results, retry history, preserved inputs, reports, and Coupa links. You can delete one run or clear all history.", "Authentication reuses the Edge profile and cached session until Coupa invalidates it. The app does not send telemetry."];
        document.querySelectorAll(".learn-card p").forEach((element, index) => { element.innerText = learnParagraphs[index]; });
        const learnNotes = appSettings.language === "pt-BR" ? ["Colunas após <|> viram níveis de pasta. Campos obrigatórios vazios são informados antes do download.", "Etapas concluídas continuam disponíveis; etapas futuras explicam o que ainda falta.", "Downloads simultâneos são limitados a 8, com backoff adaptativo quando o Coupa aplica rate limit.", "O retry usa a mesma pasta e preserva arquivos válidos existentes.", "Excluir uma execução remove sua pasta; inputs originais fora dela são preservados.", "Telemetria não é enviada. Cookies, credenciais e documentos permanecem na máquina local."] : ["Columns after <|> become folder levels. Blank required fields are reported before downloading.", "Completed steps remain available; future steps explain what is still missing.", "Downloads simultaneous is capped at 8, with adaptive backoff when Coupa rate-limits requests.", "A retry uses the same folder and preserves valid existing files.", "Deleting a run removes its folder; original inputs outside it are preserved.", "No telemetry is sent. Cookies, credentials, and documents remain on the local machine."];
        document.querySelectorAll(".learn-note").forEach((element, index) => { element.innerText = learnNotes[index]; });
        const settingsHeadings = appSettings.language === "pt-BR" ? ["Idioma", "Tamanho do texto", "Downloads", "Downloads simultâneos", "Política de retry", "Arquivos de e-mail (.msg)", "Arquivos duplicados", "Atualizações", "Login do Coupa", "Começar limpo", "Retenção do histórico"] : ["Language", "Text size", "Downloads", "Downloads simultaneous", "Retry policy", "Email files (.msg)", "Duplicate files", "Updates", "Coupa sign-in", "Start clean", "History retention"];
        document.querySelectorAll(".settings-section h3").forEach((element, index) => { element.innerText = settingsHeadings[index]; });
        const panelHeadings = appSettings.language === "pt-BR" ? ["Escolha o input", "Valide o input", "Organize a hierarquia de pastas", "Escolha o local de salvamento", "Revise e inicie"] : ["Choose your input", "Validate your input", "Arrange folder hierarchy", "Choose the save location", "Review and start"];
        document.querySelectorAll("[data-journey-panel] .card-heading h3").forEach((element, index) => { element.innerText = panelHeadings[index]; });
        const settingsDescriptions = appSettings.language === "pt-BR" ? ["Altera o idioma da interface. A saída do CLI e os logs permanecem em inglês.", "Ajusta a escala da interface para facilitar a leitura. A prévia é aplicada imediatamente e salva neste computador.", "Escolha a pasta base. Cada execução recebe uma subpasta com timestamp.", "Quantos POs o app processa ao mesmo tempo. Valores maiores podem aumentar a carga no servidor.", "Tentativas automáticas para um PO antes de marcá-lo como erro. O retry manual continua disponível no histórico.", "Escolha se arquivos de e-mail baixados são convertidos para PDF e se seus anexos são extraídos.", "Compara arquivos com SHA-256. Arquivos idênticos usam hard link quando possível ou um arquivo de referência.", "A verificação ao iniciar é opcional. Você sempre pode verificar, baixar, validar e instalar uma atualização manualmente.", "Usa o perfil existente do Edge quando possível. Se o Edge estiver aberto, usa um perfil Coupa separado para não interromper o usuário.", "Esquece o histórico local e o login, preservando arquivos baixados, relatórios e inputs.", "A limpeza automática só se aplica a execuções concluídas e nunca remove uma execução ativa."] : ["Changes the application interface language. CLI output and logs remain in English.", "Adjusts the interface scale for readability. The preview is applied immediately and saved on this computer.", "Choose the base folder. Each run receives its own timestamped subfolder.", "How many POs the app processes at the same time. Higher values may increase server load.", "Automatic attempts for a PO before marking it as failed. Manual retry remains available from History.", "Choose whether downloaded email files are converted to PDF and whether their attachments are extracted.", "Compare files with SHA-256. Identical files use a hard link when possible or a reference sidecar.", "Startup checks are optional. You can always check, download, verify, and install an update manually.", "Use the existing Edge profile when possible. If Edge is open, use a separate persistent Coupa profile so the user does not need to close Edge.", "Forget local run history and sign-in state while preserving downloaded files, reports, and original inputs.", "Automatic cleanup only applies to completed runs and never removes an active run."];
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
        setMany("#screen-history .intro-block p:not(.eyebrow)", [pt ? "Revise resultados, erros por PO e relatórios." : "Review results, inspect PO-level errors, and export reports."]);
        setMany("#btn-refresh-history, #btn-clear-history", pt ? ["Atualizar", "Excluir todo o histórico"] : ["Refresh", "Delete all history"]);
        setMany("#history-list ~ *", []);
        setMany(".history-table th", pt ? ["Execução", "Input", "Início", "POs", "Resultado", "Ações"] : ["Run", "Input", "Started", "POs", "Result", "Actions"]);
        setMany("#screen-learn .intro-block .eyebrow", [pt ? "APRENDA" : "LEARN"]);
        setMany("#screen-learn .intro-block p:not(.eyebrow)", [pt ? "Guia prático para preparar inputs, baixar anexos e recuperar erros com segurança." : "A practical guide to prepare inputs, download attachments, and recover safely from errors."]);
        setMany("#screen-settings .intro-block .eyebrow", [pt ? "CONFIGURAÇÕES" : "SETTINGS"]);
        setMany("#screen-settings .intro-block p:not(.eyebrow)", [pt ? "Controle downloads, retries, atualizações e o tempo de permanência no histórico." : "Control downloads, retries, updates, and how long runs remain in history."]);
        setMany("#btn-check-updates", [pt ? "Verificar agora" : "Check now"]);
        setMany("#btn-reset-auth", [pt ? "Zerar estado do login" : "Reset sign-in state"]);
        setMany("#btn-reset-application", [pt ? "Zerar estado local" : "Reset local state"]);
        setMany("#settings-language option", pt ? ["English (padrão)", "Português (Brasil)"] : ["English (default)", "Português (Brasil)"]);
        setMany("#settings-font-scale option", pt ? ["Padrão — 100%", "Confortável — 110%", "Grande — 120%", "Extra grande — 130%"] : ["Standard — 100%", "Comfortable — 110%", "Large — 120%", "Extra large — 130%"]);
        setMany("#settings-concurrency option",  pt ? ["Conservador — 2 downloads", "Balanceado — 4 downloads", "Rápido — 6 downloads", "Máximo — 8 downloads"] : ["Conservative — 2 downloads", "Balanced — 4 downloads", "Fast — 6 downloads", "Custom maximum — 8 downloads"]);
        setMany("#settings-retry option", pt ? ["Sem retry automático", "Tentar novamente uma vez", "Tentar novamente duas vezes"] : ["No automatic retry", "Retry once", "Retry twice"]);
        setMany("#settings-retention option", pt ? ["Tudo", "Últimas 10 execuções", "Últimas 30 execuções", "Execuções dos últimos 90 dias"] : ["Everything", "Last 10 runs", "Last 30 runs", "Runs from the last 90 days"]);
        setMany("#settings-msg-processing option", pt ? ["Desabilitado", "Converter para PDF", "Converter para PDF e extrair anexos"] : ["Disabled", "Convert to PDF", "Convert to PDF and extract attachments"]);
        setMany("#settings-field-does-not-exist", []);
        setMany("#screen-settings .settings-field label", pt ? ["Idioma da interface", "Tamanho do texto da interface", "Pasta padrão de download", "Perfil de velocidade", "Retry automático", "Processamento automático", "Manter"] : ["Interface language", "Interface text size", "Default download folder", "Speed profile", "Automatic retry", "Automatic processing", "Keep"]);
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
        $("#screen-learn h2").innerText = appSettings.language === "pt-BR" ? "Como o Coupa Turbo funciona" : "How Coupa Turbo works";
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
                panel.querySelectorAll("[draggable='true']").forEach((item) => { item.draggable = !locked; });
            }
        });
        document.querySelectorAll("[data-journey-step]").forEach((button) => {
            const value = Number(button.dataset.journeyStep);
            button.classList.toggle("active", value === target);
            button.classList.toggle("completed", value < journeyMaxStep);
            button.classList.toggle("locked", value > journeyMaxStep);
            button.disabled = false;
            button.title = value > journeyMaxStep ? journeyRequirement(value) : `Go to ${(journeyContent[appSettings.language] || journeyContent.en)[value]?.[0] || "step"}`;
        });
        const content = (journeyContent[appSettings.language] || journeyContent.en)[target];
        if (content) {
            $("#journey-title").innerText = locked ? (appSettings.language === "pt-BR" ? `Etapa ${target} bloqueada` : `Step ${target} is locked`) : content[0];
            $("#journey-subtitle").innerText = locked ? journeyRequirement(target) : content[1];
            $("#journey-subtitle").classList.toggle("journey-subtitle-warning", locked);
        }
        const lockMessage = $("#journey-lock-message");
        lockMessage.hidden = true;
        lockMessage.innerText = "";
        if (target === 2 && selectedFilePath) $("#validation-filename").innerText = $("#selected-filename").innerText;
        if (target === 4 && !locked) ensureDefaultDestination();
        if (target === 5 && !locked) renderJourneyReview();
    }

    function completeJourneyStep(nextStep) {
        journeyMaxStep = Math.max(journeyMaxStep, Number(nextStep));
        showJourneyStep(nextStep);
    }

    function renderJourneyReview() {
        const inputPath = selectedFilePath || $("#selected-filename").innerText || "—";
        $("#review-file").innerText = inputPath;
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
        Object.entries(screens).forEach(([key, screen]) => {
            const active = key === screenKey;
            screen.classList.toggle("active", active);
            screen.hidden = !active;
            navButtons[key].classList.toggle("active", active);
        });
        const titles = { new: t("prepare"), progress: t("activeRun"), history: t("history"), learn: t("learn"), settings: t("settings") };
        if ($("#page-title")) $("#page-title").innerText = titles[screenKey] || titles.new;
        $("#active-run-banner").hidden = !(screenKey === "new" && runInProgress);
        if (screenKey === "new" && runInProgress) $("#btn-start-run").disabled = true;
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
        const folderModal = $("#folder-confirm-modal");
        const detailsModal = $("#details-modal");
        if (folderModal && !folderModal.hidden) {
            $("#btn-cancel-folder-confirm").click();
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
            detailEl.innerText = pt ? "Abrindo o Edge e carregando o Coupa" : "Opening Edge and loading Coupa";
            topLabel.innerText = pt ? "Abrindo o Coupa" : "Opening Coupa";
        } else if (state === "auth_browser_ready") {
            text.innerText = pt ? "Verificando o Coupa…" : "Checking Coupa…";
            detailEl.innerText = pt ? "A página foi carregada; verificando a sessão" : "Page loaded; checking the session";
            topLabel.innerText = pt ? "Verificando sessão" : "Checking session";
        } else if (state === "auth_user_action_required") {
            text.innerText = pt ? "Ação necessária" : "Action required";
            detailEl.innerText = pt ? "Conclua o login na janela do Edge" : "Complete sign-in in the Edge window";
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
        $("#btn-authenticate").classList.toggle("is-authenticated", state === "authenticated");
        const action = $("#btn-authenticate .auth-action");
        if (action) action.innerText = state === "authenticated" ? (pt ? "Autenticado" : "Ready") : (state.startsWith("auth_") || state === "authenticating" ? (pt ? "Aguarde…" : "Please wait…") : (pt ? "Entrar" : "Sign in"));
        $("#btn-authenticate").disabled = state.startsWith("auth_") || state === "authenticating";
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

    function syncHierarchyLevels(list) {
        list.querySelectorAll("li[data-column]").forEach((item, index) => {
            item.dataset.level = String(index + 1);
            item.style.setProperty("--hierarchy-level", String(index));
            const level = item.querySelector(".hierarchy-level");
            if (level) level.innerText = `${appSettings.language === "pt-BR" ? "Nível" : "Level"} ${index + 1}`;
        });
    }

    function renderHierarchy() {
        const list = $("#folder-hierarchy");
        if (!hierarchyOrder.length) {
            list.innerHTML = '<li class="hierarchy-empty">No hierarchy columns detected.</li>';
            return;
        }
        const levelLabel = appSettings.language === "pt-BR" ? "Nível" : "Level";
        list.innerHTML = hierarchyOrder.map((column, index) => `<li draggable="false" data-column="${escapeHtml(column)}" data-level="${index + 1}" style="--hierarchy-level:${index}"><span class="hierarchy-branch" aria-hidden="true">└</span><span class="hierarchy-level">${levelLabel} ${index + 1}</span><span class="drag-handle" aria-hidden="true">☷</span><span>${escapeHtml(column)}</span></li>`).join("");
        let pointerDrag = null;
        const finishHierarchyDrag = () => {
            const item = draggedHierarchyItem;
            const placeholder = list.querySelector(".hierarchy-placeholder");
            if (!item) return;
            if (placeholder) placeholder.replaceWith(item);
            item.style.display = "";
            item.classList.remove("dragging");
            draggedHierarchyItem = null;
            pointerDrag = null;
            hierarchyOrder = [...list.querySelectorAll("li[data-column]")].map((node) => node.dataset.column);
            syncHierarchyLevels(list);
            list.classList.remove("drag-active");
        };

        const placeHierarchyPlaceholder = (clientY) => {
            if (!draggedHierarchyItem) return;
            let placeholder = list.querySelector(".hierarchy-placeholder");
            if (!placeholder) {
                placeholder = document.createElement("li");
                placeholder.className = "hierarchy-placeholder";
            }
            const candidates = [...list.querySelectorAll("li[data-column]:not(.dragging)")];
            const target = candidates.find((item) => clientY < item.getBoundingClientRect().top + item.getBoundingClientRect().height / 2);
            const targetIndex = target ? candidates.indexOf(target) : candidates.length;
            placeholder.style.setProperty("--hierarchy-level", String(targetIndex));
            if (target) list.insertBefore(placeholder, target); else list.appendChild(placeholder);
        };

        // Pointer events are used instead of native HTML5 drag events. The
        // latter are inconsistent in WebKit/pywebview and made reordering feel
        // stuck or fail altogether.
        list.querySelectorAll("li[data-column]").forEach((item) => {
            item.addEventListener("pointerdown", (event) => {
                if (event.button !== 0) return;
                pointerDrag = { item, pointerId: event.pointerId, startY: event.clientY, active: false };
                try { item.setPointerCapture(event.pointerId); } catch (_) { /* best effort */ }
            });
            item.addEventListener("pointermove", (event) => {
                if (!pointerDrag || pointerDrag.item !== item || pointerDrag.pointerId !== event.pointerId) return;
                if (!pointerDrag.active && Math.abs(event.clientY - pointerDrag.startY) < 5) return;
                if (!pointerDrag.active) {
                    pointerDrag.active = true;
                    draggedHierarchyItem = item;
                    item.classList.add("dragging");
                    item.style.display = "none";
                    list.classList.add("drag-active");
                }
                event.preventDefault();
                placeHierarchyPlaceholder(event.clientY);
            });
            item.addEventListener("pointerup", () => {
                if (pointerDrag && pointerDrag.active) finishHierarchyDrag();
                else pointerDrag = null;
            });
            item.addEventListener("pointercancel", finishHierarchyDrag);
        });
        list.addEventListener("pointermove", (event) => {
            if (pointerDrag && pointerDrag.active) {
                event.preventDefault();
                placeHierarchyPlaceholder(event.clientY);
            }
        });
    }

    function setHierarchyColumns(columns) {
        const available = (columns || []).map(String);
        const kept = hierarchyOrder.filter((column) => available.includes(column));
        hierarchyOrder = kept.concat(available.filter((column) => !kept.includes(column)));
        renderHierarchy();
    }

    function setFile(filePath, fileName, fileSize) {
        if (generatedTemplatePath && String(filePath || "") !== String(generatedTemplatePath)) generatedTemplatePath = null;
        selectedFilePath = filePath || null;
        selectedFileValidated = false;
        validatedFingerprint = null;
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
    }

    function clearFile() {
        selectedFilePath = null;
        selectedFileValidated = false;
        validatedFingerprint = null;
        if (fileMonitorInterval) clearInterval(fileMonitorInterval);
        $("#file-input").value = "";
        $("#dropzone").hidden = false;
        $("#file-details").hidden = true;
        $("#validation-feedback").hidden = true;
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
        const hasJourneyState = Boolean(selectedFilePath || generatedTemplatePath || journeyMaxStep > 1);
        if (!hasJourneyState) {
            clearFile();
            return;
        }
        const confirmed = confirm(pt
            ? "Começar de novo? O template criado pelo aplicativo será excluído. Arquivos de input escolhidos por você serão preservados."
            : "Start over? A template created by the application will be deleted. Input files chosen by you will be preserved.");
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
        clearFile();
        $("#download-dir").value = "";
        await ensureDefaultDestination();
        logToConsole("System", pt ? "Nova jornada iniciada do zero." : "New journey started from zero.");
    }

    $("#btn-start-over").addEventListener("click", startOver);

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
            if (path) $("#download-dir").value = path;
        } else {
            $("#download-dir").value = "Downloads/CoupaAttachments";
        }
        $("#btn-next-review").disabled = !$("#download-dir").value;
    });
    $("#download-dir").addEventListener("input", () => {
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
        panel.hidden = false;
        panel.classList.remove("ready", "blocked");
        if (state.open_detected) {
            panel.classList.add("blocked");
            dot.className = "status-dot unauthenticated";
            label.innerText = "Excel appears to be open — save and close it";
            selectedFileValidated = false;
            $("#btn-next-input").disabled = true;
        } else if (state.ready) {
            panel.classList.add("ready");
            dot.className = "status-dot authenticated";
            label.innerText = "File saved and ready to validate";
            $("#btn-next-input").disabled = false;
        } else {
            dot.className = "status-dot authenticating";
            label.innerText = "Waiting for the file to finish saving…";
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

    function renderValidation(result) {
        const feedback = $("#validation-feedback");
        const errors = Array.isArray(result.errors) ? result.errors : [];
        const warnings = Array.isArray(result.warnings) ? result.warnings : [];
        const fixes = Array.isArray(result.fixes) ? result.fixes : [];
        let html = "";
        setHierarchyColumns(result.hierarchy_columns || []);
        if (result.valid) html += `<div class="validation-success">File is valid — ${result.valid_po_count || 0} PO(s) ready.</div>`;
        else html += `<div class="validation-error-header">File needs correction (${errors.length} error${errors.length === 1 ? "" : "s"})</div>`;
        errors.forEach((error) => { html += `<div class="validation-error">${escapeHtml(error)}</div>`; });
        warnings.forEach((warning) => { html += `<div class="validation-warning">${escapeHtml(warning)}</div>`; });
        fixes.forEach((fix) => { html += `<div class="validation-info">Suggested fix: ${escapeHtml(fix.description || fix.action)}</div>`; });
        if (fixes.length && hasApi("repair_input_file")) {
            html += `<button class="btn btn-secondary btn-small" id="btn-repair-file" type="button">Apply safe fixes and create backup</button>`;
        }
        feedback.innerHTML = html;
        const repairButton = $("#btn-repair-file");
        if (repairButton) repairButton.addEventListener("click", async () => {
            repairButton.disabled = true;
            repairButton.innerText = "Applying fixes…";
            const repaired = await api().repair_input_file(selectedFilePath, fixes.map((fix) => fix.action));
            if (!repaired.success) {
                logToConsole("Error", repaired.error || "Could not repair the file.");
                repairButton.disabled = false;
                repairButton.innerText = "Apply safe fixes and create backup";
                return;
            }
            selectedFileValidated = false;
            validatedFingerprint = null;
            logToConsole("Success", `${repaired.message} Backup: ${repaired.backup_path}`);
            feedback.innerHTML = `<div class="validation-success">${escapeHtml(repaired.message)} Revalidating…</div>`;
            setTimeout(validateCurrentFile, 1000);
        });
        feedback.hidden = false;
        selectedFileValidated = Boolean(result.valid);
        const state = result.file_state || {};
        validatedFingerprint = state.mtime_ns && state.size ? `${state.mtime_ns}:${state.size}` : null;
        $("#btn-next-hierarchy").disabled = !selectedFileValidated;
        updateReadyState(result.valid ? "authenticated" : "unauthenticated", result.valid ? "Input validated" : "Input needs correction", result.valid ? "Ready to configure the download." : "Edit the same file and validate again.");
        return result;
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
            $("#btn-validate-file").innerText = "Validate file";
        }
    }

    $("#btn-validate-file").addEventListener("click", validateCurrentFile);
    $("#btn-next-input").addEventListener("click", () => {
        if (!selectedFilePath || $("#btn-next-input").disabled) return;
        completeJourneyStep(2);
        validateCurrentFile();
    });
    $("#btn-next-hierarchy").addEventListener("click", () => completeJourneyStep(3));
    $("#btn-next-destination").addEventListener("click", () => completeJourneyStep(4));
    $("#btn-next-review").addEventListener("click", () => {
        if (!$("#download-dir").value) {
            logToConsole("Error", "Choose a destination folder before continuing.");
            return;
        }
        completeJourneyStep(5);
    });
    document.querySelectorAll("[data-journey-back]").forEach((button) => button.addEventListener("click", () => showJourneyStep(Math.min(Number(button.dataset.journeyBack), journeyMaxStep))));
    document.querySelectorAll("[data-journey-step]").forEach((button) => button.addEventListener("click", () => showJourneyStep(button.dataset.journeyStep)));
    showJourneyStep(1);
    ensureDefaultDestination();

    function requestFolderConfirmation() {
        const modal = $("#folder-confirm-modal");
        const directory = $("#download-dir").value || "Downloads/CoupaAttachments";
        const parts = hierarchyOrder.length ? hierarchyOrder : ["Company"];
        $("#folder-preview").innerText = `${directory}/\n└── ${parts.join("/\n    └── ")}\n        └── <PO>\n\nEach PO will be saved only after its Coupa attachments are found.`;
        modal.hidden = false;
        return new Promise((resolve) => {
            const finish = (value) => { modal.hidden = true; resolve(value); };
            $("#btn-confirm-folder-run").onclick = () => finish(true);
            $("#btn-cancel-folder-run").onclick = () => finish(false);
            $("#btn-cancel-folder-confirm").onclick = () => finish(false);
        });
    }

    $("#btn-start-run").addEventListener("click", async () => {
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

        if (!(await requestFolderConfirmation())) {
            $("#btn-start-run").disabled = false;
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
            ? "Zerar o login do Coupa? O cache será removido. Seu perfil Edge existente, downloads, inputs e relatórios serão preservados. Feche todas as janelas do Edge antes de continuar."
            : "Reset Coupa sign-in? The cache will be removed. Your existing Edge profile, downloads, inputs, and reports will be preserved. Close all Edge windows first.");
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
            ? "Começar limpo? O histórico local, sessões e login serão apagados. Downloads, relatórios e inputs serão preservados. Feche o Edge e pare qualquer execução antes de continuar."
            : "Start clean? Local history, sessions, and sign-in state will be cleared. Downloads, reports, and inputs will be preserved. Close Edge and stop any active run before continuing.");
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
        body.innerHTML = '<tr><td colspan="6" class="empty-state">Loading runs…</td></tr>';
        if (!hasApi("get_session_history")) {
            body.innerHTML = '<tr><td colspan="6" class="empty-state">History is available in the desktop app.</td></tr>';
            return;
        }
        try {
            const history = await api().get_session_history();
            if (!history.length) { body.innerHTML = '<tr><td colspan="6" class="empty-state">No runs yet.</td></tr>'; return; }
            body.innerHTML = history.map((session) => {
                const status = String(session.status || "PENDING").toUpperCase();
                return `<tr><td>#${session.id}</td><td>${escapeHtml(session.input_file)}</td><td>${escapeHtml(new Date(session.created_at).toLocaleString())}</td><td>${session.total_pos || 0}</td><td><span class="status-badge status-${status.toLowerCase()}">${status}</span></td><td class="history-actions"><button class="btn btn-secondary btn-small btn-view-details" data-id="${session.id}" type="button">Details</button><button class="btn btn-danger btn-small btn-delete-run" data-id="${session.id}" data-input="${escapeHtml(session.input_file || "")}" type="button">Delete</button></td></tr>`;
            }).join("");
            body.querySelectorAll(".btn-view-details").forEach((button) => button.addEventListener("click", () => openDetailsModal(button.dataset.id)));
            body.querySelectorAll(".btn-delete-run").forEach((button) => button.addEventListener("click", () => deleteRun(button)));
        } catch (error) { body.innerHTML = `<tr><td colspan="6" class="empty-state">Could not load history: ${escapeHtml(error.message || error)}</td></tr>`; }
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
            updateAuthUI(result.authenticated ? "authenticated" : (result.state || "unauthenticated"), result.message);
        } catch (error) { updateAuthUI("unauthenticated", error.message); }
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
    async function runStartupChecks() {
        if (startupChecksDone) return;
        startupChecksDone = true;
        initializeAuth();
        await loadSettings();
        checkForUpdates();
    }
    window.addEventListener("pywebviewready", runStartupChecks);
    setTimeout(runStartupChecks, 150);
});
