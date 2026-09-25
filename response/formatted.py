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

    def response_sql(self, user_question, type_sql, only_select=False):
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
            read_only_rules = ""
            catalog_rules = ""
            if only_select:
                read_only_rules = """
                - Somente leitura: um único SELECT, ou WITH ... SELECT
                - Proibido INSERT, UPDATE, DELETE, MERGE, DDL, EXEC e SELECT INTO
                - Use DISTINCT
                - Não use LIMIT; todos os registros válidos precisam ser retornados
                """
                catalog_rules = """
                ### COMO BUSCAR PEÇA POR VEÍCULO ###
                - A peça está em public.peca (codigo, marca, descricao, codigo_norm).
                - O tipo está em public.peca_tipo. Filtro de ar é tipo = 'FILTRO_AR', ligado por peca_id.
                - Use SOMENTE public.part_fitment (pn_norm, vehicle_id) ligada a public.vehicle (make_norm, model_norm, year_start, year_end) para validar aplicação.
                - Não use part_fitment2/vehicle2: seus intervalos agregados podem gerar aplicações falsas.
                - Não use catalog_part nem aplicacao para aplicação de veículo.
                - peca_tipo.tipo guarda palavras curtas em maiúsculas, como DISCO, PASTILHA, FILTRO_AR, CUBO. Nunca compare tipo com frases como 'disco de freio'.
                - NUNCA filtre apenas pelo tipo genérico. A descrição deve conter todas as palavras significativas da família pedida. Exemplo: "disco de freio" exige p.descricao ILIKE '%disco%' AND p.descricao ILIKE '%freio%'. Adapte para qualquer família solicitada.
                - Com ano, use (ano BETWEEN v.year_start AND v.year_end). Intervalos nulos não confirmam o ano.
                - Sem ano, não filtre year_start/year_end.
                - Filtre o veículo por v.model_norm e v.make_norm.
                - Retorne p.codigo, p.marca, p.fonte, p.descricao, p.specs, t.tipo, v.make_norm AS make, v.model_norm AS model, NULL::text AS variant, v.year_start e v.year_end.
                """

            # Monta o prompt para o agente de código
            prompt = textwrap.dedent(f"""
                {contexto}

                {schema_overview}

                USE A PERGUNTA DO USUÁRIO E TRADUZA ELA PARA UM COMANDO SQL
                DEVE SER APENAS O COMANDO SQL BEM DEFINIDO PARA EXECUÇÃO

                ### REQUISITOS DE SAÍDA ###
                - Gerar UM comando SQL VÁLIDO em UMA LINHA
                - Sintaxe {type_sql}
                - Sem explicação, sem markdown e sem cercas de código
                {read_only_rules}

                {catalog_rules}
            """)

            # Gera o comando SQL e retorna como string
            sql_command = self.code_agent.ask_openai(prompt).strip()
            return sql_command

        except Exception as e:
            return f'ERRO: {e}'

    def retry_select(self, user_question, type_sql, failed_sql):
        """Segunda tentativa quando a primeira consulta volta sem linhas."""
        prompt = textwrap.dedent(f"""
            A consulta abaixo retornou 0 linhas. Gere outra consulta de leitura.
            Pergunta: {user_question}
            Consulta que falhou: {failed_sql}
            Sintaxe: {type_sql}

            Use este caminho, adaptando modelo e tipo à pergunta:
            SELECT DISTINCT p.codigo, p.marca, p.fonte, p.descricao, p.specs, t.tipo, v.make_norm AS make, v.model_norm AS model, NULL::text AS variant, v.year_start, v.year_end
            FROM public.peca p
            JOIN public.peca_tipo t ON t.peca_id = p.id
            JOIN public.part_fitment f ON f.pn_norm = p.codigo_norm
            JOIN public.vehicle v ON v.id = f.vehicle_id
            WHERE p.descricao ILIKE '%disco%'
              AND p.descricao ILIKE '%freio%'
              AND v.model_norm ILIKE '%modelo%'
              AND (ano BETWEEN v.year_start AND v.year_end)

            peca_tipo.tipo usa palavras curtas: DISCO, PASTILHA, FILTRO_AR, CUBO. Nunca compare com frases.
            Exija que p.descricao corresponda à família completa pedida. Nunca aceite apenas t.tipo.
            Confirme modelo e ano somente com part_fitment/vehicle; intervalos nulos não confirmam um ano solicitado.
            Filtre o veículo por model_norm e make_norm.
            Não use aplicacao nem catalog_part.
            Responda só com o SQL, em uma linha, sem markdown.
        """)
        content = self.code_agent.ask_openai(prompt)
        if isinstance(content, dict):
            raise RuntimeError(content.get("error") or "Falha ao gerar a consulta.")
        return str(content).strip()
