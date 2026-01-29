# formatted.py

import datetime
import textwrap
from artificial_intelligence.agents.code_agent import CodeAgent
from sql_database.show_schema import SqlDatabaseShowSchema
from sql_database.connection import SqlDatabaseConnection

class Formatted:
    def __init__(self, driver, server, database, uid, pwd, schema):
        self.driver = driver
        self.server = server
        self.database = database
        self.uid = uid
        self.pwd = pwd
        self.schema = schema
        self.code_agent = CodeAgent()

    def response_sql(self, user_question, type_sql):
        try:
            # Obtém esquema do banco de dados
            with SqlDatabaseShowSchema(
                    driver=self.driver,
                    server=self.server,
                    database=self.database,
                    uid=self.uid,
                    pwd=self.pwd,
                    schema=self.schema,
                    db_type=type_sql.lower()
            ) as db_schema:
                pass

            # Prepara o overview para o prompt
            schema_overview = textwrap.dedent(f"""
                ### ESTRUTURA DE TABELAS E SUAS COLUNAS E TIPOS : ###
                {db_schema.database_structure or 'Nenhuma coluna encontrada'}
            """)
            contexto = f'PERGUNTA DO USUÁRIO :\n{user_question}\n' if user_question else ''

            # Monta o prompt para o agente de código
            prompt = textwrap.dedent(f"""
                {contexto}

                {schema_overview}

                USE A PERGUNTA DO USUÁRIO E TRADUZA ELA PARA UM COMANDO SQL
                DEVE SER APENAS O COMANDO SQL BEM DEFINIDO PARA EXECUÇÃO

                ### REQUISITOS DE SAÍDA ###
                - Gerar UM comando SQL VÁLIDO em UMA LINHA
                - Sintaxe {type_sql}
            """)

            print(prompt)  # Para debug durante desenvolvimento

            # Gera o comando SQL e retorna como string
            sql_command = self.code_agent.ask_openai(prompt).strip()
            return sql_command

        except Exception as e:
            print(f'Erro durante o processo: {e}')
            return f'ERRO: {e}'
