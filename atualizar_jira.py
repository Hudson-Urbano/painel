import os
import base64
import requests
import psycopg
from datetime import datetime
from dotenv import load_dotenv
from tabulate import tabulate
import gspread
from google.oauth2.service_account import Credentials

# ==================== Carrega variáveis do .env ====================
load_dotenv()

# Jira
JIRA_URL = os.getenv("JIRA_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")
PROJETO = "LCSD"

# PostgreSQL
PG_HOST = os.getenv("PG_HOST")
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
PG_DATABASE = os.getenv("PG_DATABASE")
PG_PORT = int(os.getenv("PG_PORT", 5432))  # garantir int

# Google Sheets
SHEET_ID = "1aj2jk71FoC_wvzsEu3-mcdzKahpi6TdnUjdSoiQsYlk"
CRED_FILE = "credenciais.json"

# ==================== Conexão com PostgreSQL ====================
conn = psycopg.connect(
    host=PG_HOST,
    user=PG_USER,
    password=PG_PASSWORD,
    dbname=PG_DATABASE,
    port=PG_PORT,
)
conn.autocommit = False  # controle manual do commit
cursor = conn.cursor()

# ==================== Criação da tabela ====================
cursor.execute("""
    CREATE TABLE IF NOT EXISTS tarefas_jira (
        chave VARCHAR(20) PRIMARY KEY,
        criado TIMESTAMP NOT NULL,
        responsavel VARCHAR(100),
        relator VARCHAR(100),
        status VARCHAR(50),
        resumo TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
conn.commit()

# ==================== Importar dados do Jira ====================
auth_str = f"{JIRA_EMAIL}:{JIRA_TOKEN}"
auth_bytes = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

headers = {
    "Authorization": f"Basic {auth_bytes}",
    "Content-Type": "application/json"
}

params = {
    "jql": f'project = {PROJETO}',
    "fields": "summary,created,assignee,reporter,status",
    "maxResults": 1000
}

response = requests.get(f"{JIRA_URL}/rest/api/3/search", headers=headers, params=params)

if response.status_code != 200:
    print("Erro ao buscar dados do Jira:", response.status_code, response.text)
    exit(1)

dados = response.json()
if "issues" not in dados:
    print("Erro: 'issues' não encontrado na resposta do Jira.")
    exit(1)

for issue in dados["issues"]:
    try:
        resumo = issue["fields"]["summary"]
        id_tarefa = issue["key"]
        criado = issue["fields"]["created"]
        responsavel = issue["fields"]["assignee"]["displayName"] if issue["fields"]["assignee"] else "Não atribuído"
        relator = issue["fields"]["reporter"]["displayName"]
        status = issue["fields"]["status"]["name"]
        criado_dt = datetime.strptime(criado, "%Y-%m-%dT%H:%M:%S.%f%z").astimezone()

        # UPSERT no PostgreSQL com ON CONFLICT
        cursor.execute("""
            INSERT INTO tarefas_jira (chave, criado, resumo, responsavel, relator, status, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (chave) DO UPDATE SET
                criado = EXCLUDED.criado,
                resumo = EXCLUDED.resumo,
                responsavel = EXCLUDED.responsavel,
                relator = EXCLUDED.relator,
                status = EXCLUDED.status,
                updated_at = CURRENT_TIMESTAMP
        """, (id_tarefa, criado_dt, resumo, responsavel, relator, status))

    except Exception as e:
        print(f"Erro ao inserir tarefa do Jira {issue['key']}: {e}")

conn.commit()

print("✅ Tarefas do Jira inseridas/atualizadas com sucesso.")
print("Quantidade de tarefas inseridas/atualizadas:", cursor.rowcount)

# ==================== Mostrar últimas tarefas ====================
cursor.execute("SELECT chave, resumo, responsavel, status FROM tarefas_jira ORDER BY criado DESC LIMIT 10")
tarefas_jira = cursor.fetchall()
print("\n📋 Últimas tarefas do Jira:")
print(tabulate(tarefas_jira, headers=["Chave", "Resumo", "Responsável", "Status"], tablefmt="grid"))

# ==================== Atualizar Google Sheets ====================
def atualizar_google_sheets():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(CRED_FILE, scopes=scope)
    cliente = gspread.authorize(creds)

    planilha = cliente.open_by_key(SHEET_ID)
    aba_elaboracao = planilha.worksheet("CONTRATOS")

    linhas_elaboracao = aba_elaboracao.get_all_values()
    mapa_elaboracao = {linha[0]: idx + 2 for idx, linha in enumerate(linhas_elaboracao[1:]) if len(linha) > 0}
    # +2 pois planilha começa na linha 1 e header

    cursor.execute("SELECT chave, criado, status, resumo, responsavel, relator FROM tarefas_jira")
    tarefas = cursor.fetchall()

    atualizacoes_elaboracao = []
    atualizadas_elaboracao = 0

    for chave, criado, status, resumo, responsavel, relator in tarefas:
        resumo_upper = resumo.upper()

        if "ELABORAÇÃO" in resumo_upper and chave in mapa_elaboracao:
            linha_idx = mapa_elaboracao[chave]
            atualizacoes_elaboracao.extend([
                gspread.Cell(row=linha_idx, col=10, value=status),
                gspread.Cell(row=linha_idx, col=5, value=responsavel),
            ])
            atualizadas_elaboracao += 1

    if atualizacoes_elaboracao:
        aba_elaboracao.update_cells(atualizacoes_elaboracao)

    print(f"✅ Planilha atualizada com sucesso.")
    print(f"🔄 {atualizadas_elaboracao} linhas atualizadas na aba CONTRATOS.")

# ==================== Executa tudo ====================
cursor.execute("SELECT * FROM tarefas_jira")
tarefas = cursor.fetchall()

atualizar_google_sheets()

# ==================== Fecha conexão ====================
cursor.close()
conn.close()
print("\n🔒 Conexão com banco de dados encerrada.")
print("✅ Script executado com sucesso.")
print("🔚 Fim do script.")
