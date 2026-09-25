from sql_database.connection import SqlDatabaseConnection

class SqlDatabaseExecuteQuery:
    def __init__(self, driver, server, database, uid, pwd, command_query):
        """Inicializa e estabelece a conexão com o banco de dados"""
        # Classe para conexão
        self.sql_connection = SqlDatabaseConnection(driver,server, database, uid, pwd)
        self.sql_connection.connect()
        self.execute_query(command_query)

    def execute_query(self, query):
        """Executa uma query e retorna tanto a query formatada quanto os resultados.

        Returns:
            tuple: (query_executada, resultados)
        """
        # Formata a query (remove espaços desnecessários)
        formatted_query = query.strip()

        # Executa a query
        self.sql_connection.cursor.execute(formatted_query)
        results = self.sql_connection.cursor.fetchall()

        print(f"{results}")

        return formatted_query, results

    def __enter__(self):
        """Suporte para gerenciamento de contexto (with statement)"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Garante que a conexão será fechada ao sair do contexto"""
        self.sql_connection.close()