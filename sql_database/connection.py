import pyodbc

class SqlDatabaseConnection:
    def __init__(self, driver, server, database, uid, pwd):
        """Inicializa e estabelece a conexão com o banco de dados"""
        self.driver = driver
        self.server = server
        self.database = database
        self.uid = uid
        self.pwd = pwd
        self.conn = None
        self.cursor = None
        self.connect()  # Estabelece a conexão imediatamente

    def connect(self):
        """Estabelece uma nova conexão com o banco de dados"""
        self.close()  # Fecha qualquer conexão existente

        connection_string = (
            f'DRIVER={self.driver};'
            f'SERVER={self.server};'
            f'DATABASE={self.database};'
            f'UID={self.uid};'
            f'PWD={self.pwd}'
        )

        try:
            self.conn = pyodbc.connect(connection_string)
            self.cursor = self.conn.cursor()
            return True
        except pyodbc.Error as e:
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