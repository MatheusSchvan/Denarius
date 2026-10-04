"""Instala o ambiente local na primeira execução e abre o aplicativo."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import venv
import webbrowser

ROOT = Path(__file__).resolve().parent
URL = "http://127.0.0.1:8765"


def open_when_ready(process):
    for _ in range(60):
        if process.poll() is not None:
            return
        try:
            with urllib.request.urlopen(URL + "/api/health", timeout=1) as response:
                if json.load(response).get("status") == "ok":
                    webbrowser.open(URL)
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)


def main():
    if sys.version_info < (3, 11):
        print("Instale Python 3.11 ou mais recente e tente novamente.")
        return 1
    if not (ROOT / "frontend/dist/index.html").is_file():
        print("A interface precisa ser compilada: entre em frontend e execute npm ci e npm run build.")
        return 1
    try:
        with socket.socket() as port:
            port.bind(("127.0.0.1", 8765))
    except OSError:
        print("A porta 8765 esta em uso. Se o app ja estiver aberto, acesse " + URL)
        return 1
    environment = ROOT / ".venv"
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.is_file():
        print("Preparando o ambiente Python na pasta do projeto...")
        venv.create(environment, with_pip=True)
    requirements = ROOT / "backend/requirements.txt"
    signature = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = environment / "requirements.sha256"
    if not marker.is_file() or marker.read_text() != signature:
        print("Instalando dependencias. Esta etapa precisa de internet na primeira execucao.")
        subprocess.check_call([str(python), "-m", "pip", "install", "-r", str(requirements)])
        marker.write_text(signature)
    print("\nFinanceiro pessoal: " + URL)
    print("Mantenha esta janela aberta. Para encerrar, pressione Ctrl+C.\n")
    process = subprocess.Popen([str(python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8765"], cwd=ROOT / "backend")
    threading.Thread(target=open_when_ready, args=(process,), daemon=True).start()
    try:
        return process.wait()
    except KeyboardInterrupt:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, subprocess.CalledProcessError) as error:
        print("Falha ao iniciar:", error)
        sys.exit(1)
