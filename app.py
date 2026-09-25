import json
import os
import re
from urllib import error as urlerror
from urllib import request as urlrequest

def _load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

_load_env_file()

from flask import Flask, jsonify, request
from chat.auth import FirebaseNotConfigured, public_config, verify_bearer

# IMPORTS DO CONTEXTO SQL
from sql_database.connection import SqlDatabaseConnection
from sql_database.execute_query import SqlDatabaseExecuteQuery
from sql_database.show_schema import SqlDatabaseShowSchema

# IMPORTS DO CONTEXTO ARTIFICIAL INTELLIGENCE
from artificial_intelligence.translate import Translate
from artificial_intelligence.validade import Validate
from artificial_intelligence.ask import Ask

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
        self.app.route("/question/ask", methods=["POST"])(self.ask_question)
        self.app.route("/question/validate", methods=["POST"])(self.validate_sql)

        # CHAT
        self.app.route("/chat/config", methods=["GET"])(self.firebase_config)
        self.app.route("/chat/messages", methods=["POST"])(self.chat_message)
        self.app.route("/health", methods=["GET"])(self.health)
        #self.app.route("/question/optimize", methods=["POST"])()

    def run(self, host="0.0.0.0", port=None, debug=False):
        """Inicia o servidor Flask."""
        self.app.run(
            host=host,
            port=int(port or os.getenv("PORT", 5000)),
            debug=debug,
            use_reloader=False,
            threaded=True,
        )

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
    
    def ask_question(self):
        """
        Responde em linguagem natural a partir do resultado da consulta.
        """
        try:
            request_data = request.get_json() if request.is_json else request.form

            required_fields = ["driver", "server", "database", "uid", "pwd", "schema", "user_question", "type_sql"]
            missing = [f for f in required_fields if f not in request_data]
            if missing:
                return jsonify({
                    "success": False,
                    "error": f"Campos obrigatórios ausentes: {', '.join(missing)}",
                    "message": "Forneça: driver, server, database, uid, pwd, schema, user_question e type_sql"
                }), 400

            result = Ask(
                driver=request_data["driver"],
                server=request_data["server"],
                database=request_data["database"],
                uid=request_data["uid"],
                pwd=request_data["pwd"],
                schema=request_data["schema"],
                user_question=request_data["user_question"],
                type_sql=request_data["type_sql"]
            ).generated

            status = 200 if result.get("success") else 400
            return jsonify(result), status

        except Exception as error:
            return jsonify({
                "success": False,
                "error": str(error),
                "message": "Falha ao responder a pergunta."
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

    # region CHAT
    def health(self):
        return jsonify({"status": "ok"}), 200

    def firebase_config(self):
        """Entrega só a configuração pública do Firebase Web."""
        _load_env_file()
        config, missing = public_config()
        response = jsonify({
            "success": not missing,
            "config": config if not missing else {},
            "missing": missing,
        })
        response.headers["Cache-Control"] = "no-store"
        return response, 200 if not missing else 503

    def chat_message(self):
        """Responde pelo mesmo fluxo de /question/ask, com a conta do Firebase."""
        _load_env_file()
        try:
            verify_bearer(request.headers.get("Authorization"))
        except FirebaseNotConfigured as error:
            return jsonify({"success": False, "message": str(error)}), 503
        except PermissionError as error:
            return jsonify({"success": False, "message": str(error)}), 401

        request_data = request.get_json(silent=True) or {}
        question = str(request_data.get("message") or "").strip()
        if not question:
            return jsonify({"success": False, "message": "Escreva uma pergunta."}), 400
        if len(question) > 2000:
            return jsonify({
                "success": False,
                "message": "A pergunta passa de 2000 caracteres.",
            }), 400

        settings, missing = self._chat_database_settings()
        if missing:
            return jsonify({
                "success": False,
                "message": "Banco de dados do chat não configurado.",
                "missing": missing,
            }), 503

        try:
            result = self._ask_over_http(settings, self._question_with_history(question, request_data.get("history")))
        except Exception as error:
            self.app.logger.exception("Falha ao consultar /question/ask: %s", error)
            return jsonify({
                "success": False,
                "message": "Não foi possível consultar as peças agora.",
            }), 500

        status = 200 if result.get("success") else 400
        answer = result.get("answer")
        if isinstance(answer, str) and re.match(
            r"^\s*(select|with)\b",
            answer,
            flags=re.IGNORECASE,
        ):
            answer = None
        return jsonify({
            "success": bool(result.get("success")),
            "message": result.get("message"),
            "answer": answer,
            "data": result.get("data") or [],
            "row_count": result.get("row_count"),
            "truncated": bool(result.get("truncated")),
            "compatibility": result.get("compatibility"),
        }), status

    def _ask_over_http(self, settings, user_question):
        """Pede a resposta humanizada em /question/ask."""
        payload = {
            "driver": settings["driver"],
            "server": settings["server"],
            "database": settings["database"],
            "uid": settings["uid"],
            "pwd": settings["pwd"],
            "schema": settings["schema"],
            "type_sql": settings["type_sql"],
            "user_question": user_question,
        }
        ask_url = os.getenv("ASK_URL", "http://127.0.0.1:5000/question/ask")
        outgoing = urlrequest.Request(
            ask_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(outgoing, timeout=120) as response:
                return json.loads(response.read().decode("utf-8"))
        except urlerror.HTTPError as error:
            body = error.read().decode("utf-8")
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": "Falha ao responder a pergunta.",
                    "error": self._public_error(body, settings["pwd"]),
                }

    def _chat_database_settings(self):
        mapping = {
            "driver": "DB_DRIVER",
            "server": "DB_SERVER",
            "database": "DB_DATABASE",
            "uid": "DB_UID",
            "pwd": "DB_PWD",
            "schema": "DB_SCHEMA",
            "type_sql": "DB_TYPE",
        }
        values = {key: os.getenv(name, "").strip() for key, name in mapping.items()}
        missing = [name for key, name in mapping.items() if not values[key]]
        return values, missing

    def _question_with_history(self, question, history):
        if not isinstance(history, list):
            return question
        lines = []
        for turn in history[-6:]:
            if not isinstance(turn, dict):
                continue
            role = "Usuário" if turn.get("role") == "user" else "Assistente"
            content = str(turn.get("content") or "").strip()[:800]
            if content:
                lines.append(f"{role}: {content}")
        if not lines:
            return question
        return (
            "Considere o diálogo recente só para entender a pergunta atual. "
            "Responda somente à pergunta atual.\n\n"
            + "\n".join(lines)
            + "\n\nPergunta atual:\n"
            + question
        )

    def _public_error(self, error, secret):
        text = "" if error is None else str(error)
        if secret:
            text = text.replace(secret, "••••")
        return text

    # endregion

api = AlloraApp()
app = api.app

if __name__ == "__main__":
    api.run(debug=True)