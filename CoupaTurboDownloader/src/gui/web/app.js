// JavaScript for Coupa Turbo Downloader
document.addEventListener("DOMContentLoaded", () => {
    // Navigation Routing
    const screens = {
        new: document.getElementById("screen-new"),
        progress: document.getElementById("screen-progress"),
        history: document.getElementById("screen-history")
    };
    
    const navButtons = {
        new: document.getElementById("btn-new"),
        progress: document.getElementById("btn-progress"),
        history: document.getElementById("btn-history")
    };

    function showScreen(screenKey) {
        Object.keys(screens).forEach(key => {
            if (key === screenKey) {
                screens[key].classList.add("active");
                navButtons[key].classList.add("active");
            } else {
                screens[key].classList.remove("active");
                navButtons[key].classList.remove("active");
            }
        });
        
        if (screenKey === 'history') {
            loadHistory();
        }
    }

    Object.keys(navButtons).forEach(key => {
        navButtons[key].addEventListener("click", () => showScreen(key));
    });

    // File Drag & Drop
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    const btnBrowse = document.getElementById("btn-browse");
    const fileDetails = document.getElementById("file-details");
    const selectedFilename = document.getElementById("selected-filename");
    const selectedFilesize = document.getElementById("selected-filesize");
    const btnClearFile = document.getElementById("btn-clear-file");
    const downloadDirInput = document.getElementById("download-dir");
    const btnChooseDir = document.getElementById("btn-choose-dir");
    const btnStartRun = document.getElementById("btn-start-run");
    const btnPauseResume = document.getElementById("btn-pause-resume");
    const btnStopSession = document.getElementById("btn-stop-session");

    let importedSessionId = null;
    let selectedFilePath = null;

    btnBrowse.addEventListener("click", () => fileInput.click());

    fileInput.addEventListener("change", (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    dropzone.addEventListener("dragover", (e) => {
        e.preventDefault();
        dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", () => {
        dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", (e) => {
        e.preventDefault();
        dropzone.classList.remove("dragover");
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    function handleFile(file) {
        selectedFilePath = file.path || file.name; // In pywebview, sometimes we mock or can read paths depending on how it's handled.
        // Actually, in pywebview we typically use native file dialogs.
        selectedFilename.innerText = file.name;
        selectedFilesize.innerText = `${(file.size / 1024).toFixed(1)} KB`;
        
        dropzone.style.display = "none";
        fileDetails.style.display = "flex";
        
        // Auto mock folder selection
        downloadDirInput.value = "Downloads/CoupaAttachments";
    }

    btnClearFile.addEventListener("click", () => {
        selectedFilePath = null;
        fileInput.value = "";
        dropzone.style.display = "flex";
        fileDetails.style.display = "none";
    });

    // Folder selection using pywebview native dialog
    btnChooseDir.addEventListener("click", async () => {
        if (window.pywebview && window.pywebview.api) {
            const path = await window.pywebview.api.select_directory();
            if (path) {
                downloadDirInput.value = path;
            }
        }
    });

    // Start download session
    btnStartRun.addEventListener("click", async () => {
        if (!selectedFilePath) {
            logToConsole("Error", "Please select an input file before starting.");
            alert("Please select an input file before starting.");
            return;
        }
        
        logToConsole("System", `Importing ${selectedFilename.innerText}...`);
        
        if (window.pywebview && window.pywebview.api) {
            const res = await window.pywebview.api.import_file(selectedFilePath);
            if (res.success) {
                importedSessionId = res.session_id;
                logToConsole("Success", `Successfully imported! Session ID: ${res.session_id}. Found ${res.total_pos} POs.`);
                showScreen("progress");
                startTelemetryPolling(res.session_id);
                // Start crawling
                const startRes = await window.pywebview.api.start_download(res.session_id, downloadDirInput.value);
                if (!startRes.success) {
                    logToConsole("Error", `Could not start session: ${startRes.error || 'Unknown error'}`);
                    alert(`Could not start session: ${startRes.error || 'Unknown error'}`);
                }
            } else {
                logToConsole("Error", `Import failed: ${res.error}`);
                alert(`Import failed: ${res.error}`);
            }
        } else {
            // Web browser mockup mode
            importedSessionId = Math.floor(Math.random() * 1000);
            logToConsole("Success", `Mock Import OK! Total POs: 15`);
            showScreen("progress");
            mockProgressFlow();
        }
    });

    // Active session telemetry polling
    let activePollInterval = null;

    btnPauseResume.addEventListener("click", async () => {
        if (!importedSessionId || !(window.pywebview && window.pywebview.api)) return;

        const isPaused = btnPauseResume.getAttribute("data-state") === "paused";
        const res = isPaused
            ? await window.pywebview.api.resume_download(importedSessionId)
            : await window.pywebview.api.pause_download(importedSessionId);

        if (!res.success) {
            logToConsole("Error", `Could not ${isPaused ? 'resume' : 'pause'} session: ${res.error || 'Unknown error'}`);
            return;
        }

        btnPauseResume.setAttribute("data-state", isPaused ? "running" : "paused");
        btnPauseResume.innerText = isPaused ? "Pause Session" : "Resume Session";
        logToConsole("System", isPaused ? "Session resumed" : "Session paused");
    });

    btnStopSession.addEventListener("click", async () => {
        if (!importedSessionId || !(window.pywebview && window.pywebview.api)) return;
        if (!confirm("Are you sure you want to stop this session?")) return;

        const res = await window.pywebview.api.stop_download(importedSessionId);
        if (!res.success) {
            logToConsole("Error", `Could not stop session: ${res.error || 'Unknown error'}`);
            return;
        }
        logToConsole("System", "Stop requested. Waiting current operation to end...");
    });
    
    function startTelemetryPolling(sessionId) {
        btnPauseResume.disabled = false;
        btnPauseResume.setAttribute("data-state", "running");
        btnPauseResume.innerText = "Pause Session";
        btnStopSession.disabled = false;
        document.getElementById("active-session-title").innerText = `Session ID: ${sessionId}`;
        
        if (activePollInterval) clearInterval(activePollInterval);
        
        activePollInterval = setInterval(async () => {
            if (window.pywebview && window.pywebview.api) {
                const stats = await window.pywebview.api.get_active_session_status(sessionId);
                updateProgressUI(stats);
                
                // If finished, stop polling
                if (stats.status === "SUCCESS" || stats.status === "ERROR" || stats.status === "STOPPED") {
                    clearInterval(activePollInterval);
                    btnPauseResume.disabled = true;
                    btnStopSession.disabled = true;
                    logToConsole("System", `Session ${sessionId} completed with status: ${stats.status}`);
                }
            }
        }, 1000);
    }

    function updateProgressUI(stats) {
        const percent = stats.total > 0 ? Math.round((stats.processed / stats.total) * 100) : 0;
        document.getElementById("progress-bar").style.width = `${percent}%`;
        document.getElementById("progress-text").innerText = `${percent}% (${stats.processed}/${stats.total})`;
        document.getElementById("speed-val").innerText = `${stats.speed.toFixed(1)} POs/min`;
        document.getElementById("eta-val").innerText = stats.eta;
        document.getElementById("errors-val").innerText = stats.errors;
        
        // Update live logs if any
        if (stats.latest_logs) {
            stats.latest_logs.forEach(log => {
                logToConsole(log.type, log.message);
            });
        }
    }

    function logToConsole(type, message) {
        const consoleLog = document.getElementById("console-log");
        const logLine = document.createElement("div");
        logLine.className = `log-line ${type.toLowerCase()}`;
        logLine.innerText = `[${new Date().toLocaleTimeString()}] [${type}] ${message}`;
        consoleLog.appendChild(logLine);
        consoleLog.scrollTop = consoleLog.scrollHeight;
    }

    document.getElementById("btn-clear-log").addEventListener("click", () => {
        document.getElementById("console-log").innerHTML = "";
    });

    // History Tab Handling
    async function loadHistory() {
        const tbody = document.getElementById("history-list");
        tbody.innerHTML = '<tr><td colspan="5" class="text-center">Loading past runs...</td></tr>';
        
        if (window.pywebview && window.pywebview.api) {
            const history = await window.pywebview.api.get_session_history();
            if (history.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center">No historic sessions found.</td></tr>';
                return;
            }
            tbody.innerHTML = "";
            history.forEach(session => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>#${session.id}</td>
                    <td>${session.input_file}</td>
                    <td>${new Date(session.created_at).toLocaleString()}</td>
                    <td><span class="status-badge ${session.status.toLowerCase()}">${session.status}</span></td>
                    <td>
                        <button class="btn btn-secondary btn-sm btn-view-details" data-id="${session.id}">Details</button>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Bind click events
            document.querySelectorAll(".btn-view-details").forEach(btn => {
                btn.addEventListener("click", (e) => {
                    const sessionId = e.target.getAttribute("data-id");
                    openDetailsModal(sessionId);
                });
            });
        } else {
            // Browser sandbox mock
            tbody.innerHTML = `
                <tr>
                    <td>#1</td>
                    <td>dummy_pos.xlsx</td>
                    <td>20/05/2026, 11:34:00</td>
                    <td><span class="btn btn-success btn-sm">SUCCESS</span></td>
                    <td><button class="btn btn-secondary btn-sm" onclick="alert('Details Mocked!')">Details</button></td>
                </tr>
            `;
        }
    }

    // Modal Handling
    const modal = document.getElementById("details-modal");
    const btnCloseModal = document.getElementById("btn-close-modal");
    
    btnCloseModal.addEventListener("click", () => {
        modal.style.display = "none";
    });

    async function openDetailsModal(sessionId) {
        modal.style.display = "flex";
        document.getElementById("modal-title").innerText = `Session #${sessionId} Details`;
        
        if (window.pywebview && window.pywebview.api) {
            const details = await window.pywebview.api.get_session_details(sessionId);
            document.getElementById("modal-file").innerText = details.session.input_file;
            document.getElementById("modal-status").innerText = details.session.status;
            
            // Render company code items & circuit breaker states
            const companyList = document.getElementById("company-status-items");
            companyList.innerHTML = "";
            
            // Map POs to company codes to detect circuit breaker triggers
            const companyCodes = [...new Set(details.pos.map(p => p.company_code))];
            
            companyCodes.forEach(code => {
                const posOfCompany = details.pos.filter(p => p.company_code === code);
                const hasSuspended = posOfCompany.some(p => p.status === "SKIPPED_VERIFICATION_REQUIRED");
                
                const li = document.createElement("li");
                li.className = `company-badge ${hasSuspended ? 'suspended' : ''}`;
                li.innerHTML = `
                    ${code}
                    ${hasSuspended ? `<span>⚠️ Suspended</span> <button class="btn btn-primary btn-sm btn-retry-company" data-session="${sessionId}" data-company="${code}">Retry</button>` : '<span>✓ OK</span>'}
                `;
                companyList.appendChild(li);
            });

            // Bind confirm & retry actions
            document.querySelectorAll(".btn-retry-company").forEach(btn => {
                btn.addEventListener("click", async (e) => {
                    const sId = e.target.getAttribute("data-session");
                    const compCode = e.target.getAttribute("data-company");
                    if (confirm(`Confirm you verified Company Code "${compCode}" settings in Coupa and want to retry?`)) {
                        const res = await window.pywebview.api.confirm_and_retry_company(sId, compCode);
                        if (res.success) {
                            alert(`Company code ${compCode} status updated. You can now resume execution.`);
                            openDetailsModal(sId); // Reload modal details
                        }
                    }
                });
            });

            // Render PO status
            const tbody = document.getElementById("modal-pos-tbody");
            tbody.innerHTML = "";
            details.pos.forEach(po => {
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td>${po.po_number}</td>
                    <td>${po.company_code}</td>
                    <td><span class="badge-${po.status.toLowerCase()}">${po.status}</span></td>
                    <td>${po.error_message || '--'}</td>
                `;
                tbody.appendChild(tr);
            });

            // Bind export button
            document.getElementById("btn-export-modal-report").onclick = async () => {
                const exportPath = `session_${sessionId}_report.xlsx`;
                const res = await window.pywebview.api.export_session_report(sessionId, exportPath);
                if (res.success) {
                    alert(`Report exported successfully to default path: ${exportPath}`);
                } else {
                    alert(`Export failed: ${res.error}`);
                }
            };
        }
    }

    // Browser Sandbox Mock Progress Flow
    function mockProgressFlow() {
        let pct = 0;
        const interval = setInterval(() => {
            pct += 10;
            if (pct > 100) {
                clearInterval(interval);
                logToConsole("System", "Mock session finished successfully!");
                return;
            }
            document.getElementById("progress-bar").style.width = `${pct}%`;
            document.getElementById("progress-text").innerText = `${pct}% (${Math.round(15 * pct/100)}/15)`;
            document.getElementById("speed-val").innerText = `45.2 POs/min`;
            document.getElementById("eta-val").innerText = "00:08";
            logToConsole("Info", `Processing mock PO ${Math.round(15 * pct/100)}... SUCCESS`);
        }, 1000);
    }
});
