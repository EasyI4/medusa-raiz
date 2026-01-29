from idlelib.rpc import response_queue
from flask import Flask, jsonify, request

# IMPORTS DO CONTEXTO SQL
from sql_database.connection import SqlDatabaseConnection
from sql_database.execute_query import SqlDatabaseExecuteQuery
from sql_database.show_schema import SqlDatabaseShowSchema

# IMPORTS DO CONTEXTO ARTIFICIAL INTELLIGENCE
from artificial_intelligence.translate import Translate
from artificial_intelligence.validade import Validate

class AlloraApp:
    """
    Classe principal da aplicação Allora API.
    Gerencia conexões SQL e rotas Flask.
    """

    def __init__(self):
        """Inicializa o servidor Flask e configura as rotas."""
        self.app = Flask(__name__)
        self.database = None  # Armazena a conexão com o banco de dados
        self.response = None   # Armazena as respostas
        self._setup_routes()

    def _setup_routes(self):
        """Configura todas as rotas da API."""

        # ROTAS SQL ACTIONS
        self.app.route("/sql/connection", methods=["POST"])(self.handle_sql_connection)
        self.app.route("/sql/execute-query", methods=["POST"])(self.sql_query)
        self.app.route("/sql/show-schema", methods=["POST"])(self.show_schema)

        # ROTAS ARTIFICIAL INTELLIGENCE
        self.app.route("/question/translate-sql", methods=["POST"])(self.translate_sql)
        self.app.route("/question/validate", methods=["POST"])(self.validate_sql)
        #self.app.route("/question/optimize", methods=["POST"])()

    def run(self, host="0.0.0.0", port=5000, debug=False):
        """Inicia o servidor Flask."""
        self.app.run(host=host, port=port, debug=debug)

    # region SQL FUNCTIONS

    def handle_sql_connection(self):
        """
        Estabelece uma conexão com o banco de dados SQL.

        Requer (via JSON ou Form-Data):
        - driver (str): Ex: "SQL Server", "PostgreSQL"
        - server (str): Endereço do servidor
        - database (str): Nome do banco de dados
        - uid (str): Usuário
        - pwd (str): Senha

        Retorna:
        - JSON com status (sucesso/erro) e mensagem.
        """
        try:
            # Obtém os dados da requisição (JSON ou Form-Data)
            request_data = request.get_json() if request.is_json else request.form

            # Verifica se todos os campos necessários foram enviados
            required_fields = ["driver", "server", "database", "uid", "pwd"]
            if not all(field in request_data for field in required_fields):
                return jsonify({
                    "success": False,
                    "error": "Campos obrigatórios ausentes",
                    "message": "Forneça: driver, server, database, uid e pwd"
                }), 400  # Bad Request

            self.database = SqlDatabaseConnection(
                driver=request_data["driver"],
                server=request_data["server"],
                database=request_data["database"],
                uid=request_data["uid"],
                pwd=request_data["pwd"]
            )

            return jsonify({
                "success": True,
                "message": "Conexão estabelecida com sucesso!"
            })

        except Exception as error:
            return jsonify({
                "success": False,
                "error": str(error),
                "message": "Falha ao conectar ao banco de dados"
            }), 500  # Internal Server Error

    def sql_query(self):
        """
        Executa comandos SQL no banco de dados.
        """
        try:
            # Obtém os dados da requisição (JSON ou Form-Data)
            request_data = request.get_json() if request.is_json else request.form

            # Verifica se todos os campos necessários foram enviados
            required_fields = ["driver", "server", "database", "uid", "pwd", "command_query"]
            missing = [f for f in required_fields if f not in request_data]
            if missing:
                return jsonify({
                    "success": False,
                    "error": f"Campos obrigatórios ausentes: {', '.join(missing)}",
                    "message": "Forneça: driver, server, database, uid e pwd"
                }), 400  # Bad Request

            self.database = SqlDatabaseExecuteQuery(
                driver=request_data["driver"],
                server=request_data["server"],
                database=request_data["database"],
                uid=request_data["uid"],
                pwd=request_data["pwd"],
                command_query=request_data["command_query"]
            )

            return jsonify({
                "success": True,
                "message": "Query executada!"
            }), 200  # OK

        except Exception as error:
            return jsonify({
                "success": False,
                "error": str(error),
                "message": "Falha ao conectar ao banco de dados"
            }), 500  # Internal Server Error

    def show_schema(self):
        """
        Executa comandos SQL no banco de dados.
        """
        try:
            # Obtém os dados da requisição (JSON ou Form-Data)
            request_data = request.get_json() if request.is_json else request.form

            # Verifica se todos os campos necessários foram enviados
            required_fields = ["driver", "server", "database", "uid", "pwd", "catalog", "schema", "db_type"]
            missing = [f for f in required_fields if f not in request_data]
            if missing:
                return jsonify({
                    "success": False,
                    "error": f"Campos obrigatórios ausentes: {', '.join(missing)}",
                    "message": "Forneça: driver, server, database, uid e pwd"
                }), 400  # Bad Request

            self.database = SqlDatabaseShowSchema(
                driver=request_data["driver"],
                server=request_data["server"],
                database=request_data["database"],
                uid=request_data["uid"],
                pwd=request_data["pwd"],
                schema=request_data["schema"],
                db_type=request_data["db_type"]
            )

            return jsonify({
                "success": True,
                "message": "Estrutura do banco de dados gerada!"
            }), 200  # OK

        except Exception as error:
            return jsonify({
                "success": False,
                "error": str(error),
                "message": "Falha ao conectar ao banco de dados"
            }), 500  # Internal Server Error

    # endregion

    # region ARTIFICIAL INTELLIGENCE FUNCTIONS
    def translate_sql(self):
        """
        Traduz uma pergunta em linguagem natural para comando SQL.
        """
        try:
            request_data = request.get_json() if request.is_json else request.form

            required_fields = ["driver", "server", "database", "uid", "pwd", "schema", "user_question", "type_sql"]
            missing = [f for f in required_fields if f not in request_data]
            if missing:
                return jsonify({
                    "success": False,
                    "error": f"Campos obrigatórios ausentes: {', '.join(missing)}",
                    "message": "Forneça: driver, server, database, uid e pwd"
                }), 400

            translator = Translate(
                driver=request_data["driver"],
                server=request_data["server"],
                database=request_data["database"],
                uid=request_data["uid"],
                pwd=request_data["pwd"],
                schema=request_data["schema"],
                user_question=request_data["user_question"],
                type_sql=request_data["type_sql"]
            )

            generated_command = translator.generated_sql
            if not generated_command:
                return jsonify({
                    "success": False,
                    "error": "Nenhum comando SQL foi gerado.",
                    "message": "Falha na tradução da pergunta para SQL."
                }), 400

            # Valida o comando SQL gerado
            result = Validate(
                driver=request_data["driver"],
                server=request_data["server"],
                database=request_data["database"],
                uid=request_data["uid"],
                pwd=request_data["pwd"],
                command_query=generated_command
            )

            # Verifica se a validação foi bem-sucedida
            if not result.generated_sql.get("success", False):
                return jsonify({
                    "success": False,
                    "error": result.generated_sql.get("error", "Erro desconhecido"),
                    "message": "Falha ao validar o comando SQL gerado."
                }), 400

            # Tudo OK: Retorna o comando traduzido e validado
            return jsonify({
                "success": True,
                "message": "Comando SQL gerado e validado com sucesso!",
                "command": generated_command
            }), 200

        except Exception as error:
            return jsonify({
                "success": False,
                "error": str(error),
                "message": "Falha ao traduzir para SQL"
            }), 500

        except Exception as error:
            return jsonify({
                "success": False,
                "error": str(error),
                "message": "Falha geral ao traduzir e validar o SQL."
            }), 500
    
    def validate_sql(self):
        """
        Valida e executa um comando SQL fornecido pelo usuário.
        """
        try:
            request_data = request.get_json() if request.is_json else request.form

            required_fields = ["driver", "server", "database", "uid", "pwd", "command_query"]
            missing = [f for f in required_fields if f not in request_data]
            if missing:
                return jsonify({
                    "success": False,
                    "error": f"Campos obrigatórios ausentes: {', '.join(missing)}",
                    "message": "Forneça: driver, server, database, uid e pwd"
                }), 400

            result = Validate(
                driver=request_data["driver"],
                server=request_data["server"],
                database=request_data["database"],
                uid=request_data["uid"],
                pwd=request_data["pwd"],
                command_query=request_data["command_query"]
            )

            # Retorna o resultado gerado (que já é um dicionário estruturado)
            return jsonify(result.generated_sql), 200

        except Exception as error:
            return jsonify({
                "success": False,
                "error": str(error),
                "message": "Falha ao validar o comando SQL"
            }), 500

    # endregion

# ⚡ Inicia o servidor quando o arquivo é executado diretamente
if __name__ == "__main__":
    api = AlloraApp()
    api.run(debug=True)  # Ativa modo debug para desenvolvimento