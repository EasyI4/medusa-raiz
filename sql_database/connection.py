import os

class SqlDatabaseConnection:
    def __init__(self, driver, server, database, uid, pwd, port=None, sslmode=None):
        """Inicializa e estabelece a conexão com o banco de dados"""
        self.driver = driver
        self.server = server
        self.database = database
        self.uid = uid
        self.pwd = pwd
        self.port = port or os.getenv("DB_PORT")
        self.sslmode = sslmode or os.getenv("DB_SSLMODE")
        self.conn = None
        self.cursor = None
        self.connect()  # Estabelece a conexão imediatamente

    def _use_postgres(self):
        driver_name = (self.driver or "").lower()
        return bool(self.sslmode) or "postgres" in driver_name

    def connect(self):
        """Estabelece uma nova conexão com o banco de dados"""
        self.close()  # Fecha qualquer conexão existente

        try:
            if self._use_postgres():
                import psycopg2

                self.conn = psycopg2.connect(
                    host=self.server,
                    port=int(self.port or 5432),
                    dbname=self.database,
                    user=self.uid,
                    password=self.pwd,
                    sslmode=self.sslmode or "require",
                )
            else:
                connection_string = (
                    f'DRIVER={self.driver};'
                    f'SERVER={self.server};'
                    f'DATABASE={self.database};'
                    f'UID={self.uid};'
                    f'PWD={self.pwd}'
                )
                import pyodbc

                self.conn = pyodbc.connect(connection_string)

            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            raise ConnectionError(f"Falha na conexão: {str(e)}")

    def close(self):
        """Fecha a conexão de forma segura"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        self.cursor = None
        self.conn = None

    def __enter__(self):
        """Suporte para gerenciamento de contexto (with statement)"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Garante que a conexão será fechada ao sair do contexto"""
        self.close()