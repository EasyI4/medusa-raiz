import os
from colorama import init, Fore
from openai import OpenAI
from typing import Union

# Inicializa o colorama (para suportar no Windows)
init(autoreset=True)

class MainAgent:
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
                model="gpt-4o",  # Use o modelo mais recente se possível
                messages=[
                    {
                        "role": "user",
                        "content": prompt.strip()
                    }
                ],
            )
            content = completion.choices[0].message.content.strip()
            return content

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
