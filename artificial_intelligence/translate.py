from sql_database.connection import SqlDatabaseConnection
from response.formatted import Formatted

class Translate:
    def __init__(self, driver, server, database, uid, pwd, schema, user_question, type_sql):
        # abre conexão com o banco
        self.sql_connection = SqlDatabaseConnection(driver, server, database, uid, pwd)
        self.sql_connection.connect()

        # prepara o gerador de prompts
        self.formatted = Formatted(driver, server, database, uid, pwd, schema)

        # armazena o resultado da tradução
        self.generated_sql = self.translate(user_question, type_sql)

    def translate(self, user_question: str, type_sql: str) -> str:
        """
        Traduza a pergunta do usuário para um comando SQL único,
        disparando a função correta de acordo com type_sql.
        type_sql deve ser: "SQL SERVER", "MYSQL" ou "POSTGRESQL"
        """
        key = type_sql.strip().lower()
        if key in ("sql server", "sqlserver"):
            return self.formatted.response_sql(user_question, type_sql="SQL SERVER")
        elif key == "mysql":
            return self.formatted.response_sql(user_question, type_sql="MYSQL")
        elif key in ("postgresql", "postgres", "postgree"):
            return self.formatted.response_sql(user_question, type_sql="POSTGRESQL")
        else:
            raise ValueError(f"Tipo de SQL desconhecido: '{type_sql}'. Use SQL SERVER, MYSQL ou POSTGRESQL.")
