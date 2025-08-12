# Painel de Atualizações Jira

Um painel web em Flask para executar scripts automáticos de atualização de dados do Jira, compliance LGPD e consultas jurídicas, integrando banco PostgreSQL e planilhas Google Sheets.

---

## Funcionalidades

- Interface web para disparar scripts individualmente
- Exibição do status atual e histórico da última execução de cada script
- Integração com banco PostgreSQL para armazenar tarefas Jira
- Atualização automatizada de planilhas Google Sheets para controle visual
- Execução assíncrona dos scripts para não travar a interface