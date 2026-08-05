// Minimal frontend: mirrors how ContractDownloader/src/gui/web talks to the
// Python backend, but through the Tauri bridge (window.__TAURI__.core.invoke)
// instead of window.pywebview.api.

const { invoke } = window.__TAURI__.core;

const statusDot = document.getElementById("status-dot");
const statusText = document.getElementById("status-text");

function setStatus(state, text) {
  statusDot.className = `dot ${state}`;
  statusText.textContent = text;
}

async function runPython(command, args) {
  setStatus("busy", `python ${command} …`);
  const result = await invoke("run_python", {
    command,
    argsJson: args ? JSON.stringify(args) : "{}",
  });
  if (!result.ok) {
    throw new Error(result.error || "sidecar error");
  }
  return result;
}

function show(elId, value) {
  document.getElementById(elId).textContent =
    typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

const actions = {
  ping: async () => show("out-ping", await runPython("ping")),
  process_csv: async () => {
    const out = await runPython("process_csv");
    show("out-csv", out.summary);
  },
  powerbi_status: async () => show("out-pbi", await runPython("powerbi_status")),
  powerbi_query: async () => show("out-pbi", await runPython("powerbi_query")),
  app_info: async () => show("out-info", await invoke("app_info")),
};

for (const button of document.querySelectorAll("button[data-action]")) {
  button.addEventListener("click", async () => {
    const action = actions[button.dataset.action];
    button.disabled = true;
    setStatus("busy", `${button.dataset.action} …`);
    try {
      await action();
      setStatus("ok", "done");
    } catch (err) {
      setStatus("err", String(err));
    } finally {
      button.disabled = false;
    }
  });
}

window.addEventListener("DOMContentLoaded", () => {
  setStatus("ok", "ready — unsigned build");
});
