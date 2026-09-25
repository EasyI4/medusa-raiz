from sql_database.connection import SqlDatabaseConnection


class SqlDatabaseReadQuery:
    """Executa uma consulta de leitura e devolve as linhas, sem commit."""

    def __init__(self, driver, server, database, uid, pwd, command_query, max_rows=None):
        self.max_rows = max_rows
        self.sql_connection = SqlDatabaseConnection(driver, server, database, uid, pwd)
        try:
            self.result = self._execute(command_query)
        finally:
            self.sql_connection.close()

    def _execute(self, command_query):
        cursor = self.sql_connection.conn.cursor()
        try:
            cursor.execute(command_query)
            if cursor.description is None:
                return {
                    "success": False,
                    "error": "A consulta não retornou colunas.",
                    "message": "Só é possível responder a consultas de leitura.",
                }

            columns = [column[0] for column in cursor.description]
            if self.max_rows is None:
                rows = cursor.fetchall()
                truncated = False
            else:
                fetched = cursor.fetchmany(self.max_rows + 1)
                truncated = len(fetched) > self.max_rows
                rows = fetched[: self.max_rows]
            data = [dict(zip(columns, row)) for row in rows]
            return {
                "success": True,
                "type": "SELECT",
                "data": data,
                "row_count": len(data),
                "truncated": truncated,
            }
        except Exception as error:
            return {
                "success": False,
                "error": str(error),
                "message": "Falha ao executar a consulta.",
            }
        finally:
            cursor.close()
