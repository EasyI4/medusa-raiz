from sql_database.connection import SqlDatabaseConnection
from response.formatted import Formatted    

class Validate:
    def __init__(self, driver, server, database, uid, pwd, command_query):
        # Abre conexão com o banco
        self.sql_connection = SqlDatabaseConnection(driver, server, database, uid, pwd)
        self.sql_connection.connect()

        # Executa o comando e armazena o resultado
        self.generated_sql = self.execute_sql(command_query)

    def execute_sql(self, command_query) -> str:
        cursor = None
        try:
            cursor = self.sql_connection.conn.cursor()
            print(f"Executando comando SQL: {command_query}")  # Para debug durante desenvolvimento
            cursor.execute(command_query)

            # Se for um SELECT, traz os dados
            if command_query.strip().upper().startswith("SELECT"):
                columns = [column[0] for column in cursor.description]
                rows = cursor.fetchall()
                result = [dict(zip(columns, row)) for row in rows]
                return {
                    "success": True,
                    "type": "SELECT",
                    "data": result
                }

            else:
                # Se for DML (INSERT, UPDATE, DELETE), faz commit
                self.sql_connection.conn.commit()
                return {
                    "success": True,
                    "type": "DML",
                    "message": f"Comando executado com sucesso. {cursor.rowcount} linhas afetadas."
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": "Falha ao executar o comando SQL."
            }
        finally:
            if cursor:
                cursor.close()
