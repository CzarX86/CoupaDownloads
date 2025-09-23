#!/bin/bash

# Função para limpar os processos em segundo plano ao sair
cleanup() {
    echo -e "\nShutting down servers..."
    # Mata todos os processos no grupo deste script (incluindo os filhos)
    kill 0
}

# Captura o sinal de interrupção (Ctrl+C) e término para executar a limpeza
trap cleanup INT TERM

echo "🚀 Starting AI Builder SPA..."
echo "--------------------------------"

# Inicia o Backend (FastAPI) em segundo plano
echo "[1/3] Starting backend server on http://127.0.0.1:8008..."
PYTHONPATH=src poetry run python -m server.pdf_training_app.main &

# Inicia o Frontend (React) em segundo plano
echo "[2/3] Starting frontend server on http://localhost:5173..."
(cd src/spa && npm run dev) &

# Aguarda um tempo para os servidores inicializarem
echo "Waiting for servers to be ready..."
sleep 15

# Abre o navegador
URL="http://localhost:5173"
echo "[3/3] Opening application in your browser: $URL"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open "$URL"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    open "$URL"
else
    echo "Could not detect OS to open browser. Please open it manually at $URL"
fi

echo "--------------------------------"
echo "✅ Servers are running. Press Ctrl+C in this terminal to stop them."

# Aguarda os processos em segundo plano (que só terminarão com o trap)
wait