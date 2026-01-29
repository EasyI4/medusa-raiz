import os
from colorama import init, Fore, Style
from openai import OpenAI
from typing import Union

# Inicializa o colorama (para suportar no Windows)
init(autoreset=True)

class CodeAgent:
    def __init__(self, api_key: str = None):
        """Inicializa o cliente OpenAI com a chave da API."""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError(f"{Fore.RED}[ERRO] API key da OpenAI não fornecida nem encontrada nas variáveis de ambiente.")

        self.client = OpenAI(api_key=self.api_key)

    def ask_openai(self, prompt: str) -> Union[str, dict]:
        """Envia um prompt para a OpenAI e retorna a resposta."""
        try:
            completion = self.client.chat.completions.create(
                model="o3-mini",  # Use o modelo mais recente se possível
                messages=[
                    {
                        "role": "user",
                        "content": prompt.strip()
                    }
                ],
            )
            content = completion.choices[0].message.content.strip()
            print(f"{Fore.CYAN}| Medusa |: {Style.RESET_ALL}{content}")
            return content

        except Exception as e:
            error_msg = f"{Fore.RED}[ERRO] Falha ao consultar OpenAI: {e}"
            print(error_msg)
            return {
                "success": False,
                "error": str(e)
            }
