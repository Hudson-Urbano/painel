from flask import Flask, render_template, redirect, url_for, flash, jsonify, request
import subprocess
import threading
from datetime import datetime
import logging
import copy
import sys
import psycopg

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "segredo"

logging.basicConfig(level=logging.INFO)

SCRIPTS = {
    "elaboracao": "atualizar_jira.py",
    "lgpd": "attLGPD.py",
    "consulta": "attConsjur.py"
}

status_execucao = {
    nome: {"status": "idle", "ultima_execucao": None} for nome in SCRIPTS
}

status_lock = threading.Lock()

def executar_script(nome_script):
    with status_lock:
        status_execucao[nome_script]["status"] = "executando"

    logging.info(f"Iniciando script {nome_script}")

    try:
        result = subprocess.run(
            [sys.executable, SCRIPTS[nome_script]],
            capture_output=True,
            text=True,
            check=False  # vamos tratar erro abaixo
        )
        logging.info(f"[{nome_script}] stdout:\n{result.stdout}")
        if result.returncode != 0:
            logging.error(f"[{nome_script}] stderr:\n{result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, result.args)
        status = "sucesso"
        logging.info(f"Script {nome_script} executado com sucesso")
    except subprocess.CalledProcessError as e:
        status = "erro"
        logging.error(f"Erro na execução do script {nome_script}: {e}")
    except Exception as e:
        status = "erro"
        logging.error(f"Erro inesperado no script {nome_script}: {e}")
    finally:
        with status_lock:
            status_execucao[nome_script]["status"] = status
            status_execucao[nome_script]["ultima_execucao"] = datetime.now().strftime("%d/%m/%Y %H:%M")

@app.route("/")
def home():
    with status_lock:
        status = copy.deepcopy(status_execucao)
    return render_template("index.html", status=status)

@app.route("/executar/<nome>", methods=["POST"])
def executar(nome):
    if nome not in SCRIPTS:
        flash("❌ Script inválido.", "danger")
        return redirect(url_for("home"))

    with status_lock:
        if status_execucao[nome]["status"] == "executando":
            flash(f"⚠️ O script '{nome}' já está em execução.", "warning")
            return redirect(url_for("home"))

        status_execucao[nome]["status"] = "iniciando"

    threading.Thread(target=executar_script, args=(nome,), daemon=True).start()
    flash(f"⏳ Atualização '{nome}' iniciada...", "info")
    return redirect(url_for("home"))

@app.route("/status")
def status():
    with status_lock:
        return jsonify(copy.deepcopy(status_execucao))

if __name__ == "__main__":
    app.run(debug=True)
