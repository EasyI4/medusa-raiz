import textwrap
from sql_database.connection import SqlDatabaseConnection

class SqlDatabaseShowSchema:
    def __init__(self, driver, server, database, uid, pwd, schema, db_type):
        """
        Inicializa e estabelece a conexão com o banco de dados.
        """
        self.database = database
        self.schema = schema
        self.db_type = db_type

        self.sql_connection = SqlDatabaseConnection(driver, server, database, uid, pwd)
        self.sql_connection.connect()

        # Obtém estrutura usando métodos estáticos
        self.database_structure = self.get_all_columns(
            connection=self.sql_connection,
            database=self.database,
            schema=self.schema,
            db_type=self.db_type
        )

        self.structure_overview = self.get_structure_overview(self.database_structure)

    @staticmethod
    def get_all_columns(connection, database: str, schema: str, db_type: str) -> str:
        """
        Retorna as colunas de todas as tabelas do schema, ajustando a consulta
        conforme o tipo de banco de dados (SQL Server, MySQL, PostgreSQL).
        """
        try:
            kind = db_type.strip().lower().replace(" ", "").replace("_", "").replace("-", "")
            if kind in ("sqlserver", "mssql"):
                query = textwrap.dedent(f"""
                    SELECT 
                        TABLE_CATALOG, 
                        TABLE_SCHEMA, 
                        TABLE_NAME, 
                        COLUMN_NAME, 
                        DATA_TYPE
                    FROM [{database}].INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = '{schema}'
                    ORDER BY TABLE_NAME, ORDINAL_POSITION;
                """)
            elif kind == "mysql":
                query = textwrap.dedent(f"""
                    SELECT 
                        TABLE_SCHEMA AS TABLE_CATALOG, 
                        TABLE_SCHEMA, 
                        TABLE_NAME, 
                        COLUMN_NAME, 
                        DATA_TYPE
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = '{database}' AND TABLE_NAME IS NOT NULL
                    ORDER BY TABLE_NAME, ORDINAL_POSITION;
                """)
            elif kind in ("postgresql", "postgres", "postgree"):
                query = textwrap.dedent(f"""
                    SELECT 
                        table_catalog AS TABLE_CATALOG, 
                        table_schema AS TABLE_SCHEMA, 
                        table_name AS TABLE_NAME, 
                        column_name AS COLUMN_NAME, 
                        data_type AS DATA_TYPE
                    FROM information_schema.columns
                    WHERE table_schema = '{schema}'
                    ORDER BY table_name, ordinal_position;
                """)
            else:
                raise ValueError(f"Tipo de banco de dados não suportado: {db_type}")

            connection.cursor.execute(query)
            rows = connection.cursor.fetchall()

            columns = {}
            for db, sch, table, col, dtype in rows:
                key = f"{db}.{sch}.{table}"
                columns.setdefault(key, []).append(f"{col} ({dtype})")

            return "\n".join(f"{tbl}: {', '.join(cols)}" for tbl, cols in columns.items())

        except Exception as e:
            print(f"Erro ao obter colunas: {e}")
            raise

    @staticmethod
    def get_structure_overview(database_structure: str) -> str:
        """
        Formata a estrutura para exibição com indentação.
        """
        lines = [f"  {line}" for line in database_structure.splitlines()]
        return "\n".join(lines)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sql_connection.close()
