import os
import base64
import requests
import psycopg
from datetime import datetime
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

# ==================== Carrega variáveis do .env ====================
load_dotenv()

# Configurações do Jira
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")
PROJETO = "LCSD"

# Configurações do PostgreSQL
PG_HOST = os.getenv("PG_HOST")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DATABASE = os.getenv("PG_DATABASE")
PG_PORT = os.getenv("PG_PORT", 5432)

# Google Sheets
SHEET_ID = "1aj2jk71FoC_wvzsEu3-mcdzKahpi6TdnUjdSoiQsYlk"
CRED_FILE = "credenciais.json"

# ==================== Conexão com o banco de dados ====================
conn = psycopg.connect(
    host=PG_HOST,
    user=PG_USER,
    password=PG_PASSWORD,
    dbname=PG_DATABASE,
    port=PG_PORT
)
conn.set_client_encoding('UTF8')
cursor = conn.cursor()

# ==================== Atualizar aba COMPLIANCE & LGPD ====================
def atualizar_compliance_lgpd():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(CRED_FILE, scopes=scope)
    cliente = gspread.authorize(creds)

    planilha = cliente.open_by_key(SHEET_ID)
    aba = planilha.worksheet("COMPLIANCE & LGPD")

    linhas = aba.get_all_values()
    mapa = {linha[0]: idx + 1 for idx, linha in enumerate(linhas[1:]) if len(linha) > 0}

    cursor.execute("SELECT chave, resumo, responsavel, status FROM tarefas_jira")
    tarefas = cursor.fetchall()

    atualizacoes = []
    atualizadas = 0

    for chave, resumo, responsavel, status in tarefas:
        resumo_upper = resumo.upper()

        if ("COMPLIANCE" in resumo_upper or "LGPD" in resumo_upper) and chave in mapa:
            linha_idx = mapa[chave] + 1
            atualizacoes.extend([
                gspread.Cell(row=linha_idx, col=8, value=status),       # Coluna H
                gspread.Cell(row=linha_idx, col=5, value=responsavel),  # Coluna E
            ])
            atualizadas += 1

    if atualizacoes:
        aba.update_cells(atualizacoes)

    print("✅ Aba 'COMPLIANCE & LGPD' atualizada com sucesso.")
    print(f"🔄 {atualizadas} linhas atualizadas.")

# ==================== Executa o script ====================
atualizar_compliance_lgpd()

cursor.close()
conn.close()
print("🔒 Conexão encerrada.")
