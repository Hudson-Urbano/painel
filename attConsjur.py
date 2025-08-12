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

# Configurações do PostgreSQL
PG_HOST = os.getenv("PG_HOST")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DATABASE = os.getenv("PG_DATABASE")
PG_PORT = int(os.getenv("PG_PORT", 5432))  # Converter para inteiro

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
conn.execute("SET CLIENT_ENCODING TO 'UTF8'")
cursor = conn.cursor()

# ==================== Atualizar aba CONSULTA JURÍDICA ====================
def atualizar_consulta_juridica():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(CRED_FILE, scopes=scope)
    cliente = gspread.authorize(creds)

    planilha = cliente.open_by_key(SHEET_ID)
    aba = planilha.worksheet("CONSULTA JURÍDICA")

    linhas = aba.get_all_values()
    # Mapa chave -> linha real na planilha (considerando cabeçalho na linha 1)
    mapa = {linha[0]: idx + 2 for idx, linha in enumerate(linhas[1:]) if len(linha) > 0}

    cursor.execute("SELECT chave, resumo, responsavel, status FROM tarefas_jira")
    tarefas = cursor.fetchall()

    atualizacoes = []
    atualizadas = 0

    for chave, resumo, responsavel, status in tarefas:
        resumo_upper = resumo.upper()

        if "CONSULTA JURÍDICA" in resumo_upper and chave in mapa:
            linha_idx = mapa[chave]  # linha real já calculada no mapa
            atualizacoes.extend([
                gspread.Cell(row=linha_idx, col=4, value=responsavel),  # Coluna D
                gspread.Cell(row=linha_idx, col=7, value=status),       # Coluna G
            ])
            atualizadas += 1

    if atualizacoes:
        aba.update_cells(atualizacoes)

    print("✅ Aba 'CONSULTA JURÍDICA' atualizada com sucesso.")
    print(f"🔄 {atualizadas} linhas atualizadas.")

# ==================== Executa o script ====================
atualizar_consulta_juridica()

cursor.close()
conn.close()
print("🔒 Conexão encerrada.")
