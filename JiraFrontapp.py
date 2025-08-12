from flask import Flask, render_template, redirect, url_for, flash, jsonify, request
import subprocess
import threading
from datetime import datetime
import logging
from waitress import serve
import copy

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
        subprocess.run(["python", SCRIPTS[nome_script]], check=True)
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
    print("🚀 Servidor iniciado em http://127.0.0.1:5000")
    serve(app, host="127.0.0.1", port=5000)
