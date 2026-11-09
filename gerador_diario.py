import json
import os
import sqlite3
import time
from datetime import date
from google import genai
from google.genai import types

DB_NAME = "curadoria.db"
API_KEY = os.environ.get("API_KEY")


def gerar_conteudo():
    client = genai.Client(api_key=API_KEY)

    prompt = f"""
    Atue como um Curador-Chefe de Inteligência Executiva em GEO (Generative Engine Optimization), IA, Liderança e Comunicação.
    Data de referência: {date.today()}.
    
    Selecione exatamente 3 leituras relevantes e complementares seguindo este equilíbrio:
    1. Acadêmica / Pesquisa (papers, ciência cognitiva, modelos de LLM)
    2. Aplicação de Mercado (estratégias de busca/GEO, cases de marcas, produtos)
    3. Comportamento / Liderança (psicologia organizacional, oratória, credibilidade executiva)

    Além das 3 leituras, redija uma "Carta do Editor" contextualizando as escolhas, explicando o critério do dia e a tensão intelectual entre as fontes.

    Responda ESTRITAMENTE em formato JSON com esta estrutura:
    {{
      "carta_editor": "Texto completo da carta em markdown...",
      "leituras": [
        {{
          "titulo": "Título da leitura",
          "autor_fonte": "Autor ou Instituição",
          "trilha": "GEO & Search",
          "tempo_min": 10,
          "url": "https://link-relevante.com",
          "resumo_executivo": "Resumo de 2 parágrafos...",
          "key_insight": "Insight central contra-intuitivo..."
        }}
      ]
    }}
    """

    # Lista de modelos para tentar caso algum esteja congestionado
    modelos = ["gemini-3.8-flash", "gemini-2.5-flash-lite"]

    for tentativa in range(5):
        modelo_atual = modelos[tentativa % len(modelos)]
        try:
            print(f"Tentativa {tentativa + 1} usando o modelo {modelo_atual}...")
            response = client.models.generate_content(
                model=modelo_atual,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Erro temporário ({e}). Aguardando 30 segundos...")
            time.sleep(30)

    raise RuntimeError(
        "Não foi possível gerar a curadoria após 5 tentativas devido a instabilidade na API."
    )


def salvar_no_banco(dados):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS carta_editor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data DATE NOT NULL UNIQUE,
                conteudo TEXT NOT NULL
            )
        """
        )

        cursor.execute(
            """
            INSERT OR REPLACE INTO carta_editor (data, conteudo)
            VALUES (?, ?)
        """,
            (str(date.today()), dados["carta_editor"]),
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS leituras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                autor_fonte TEXT NOT NULL,
                trilha TEXT NOT NULL,
                tempo_min INTEGER NOT NULL,
                url TEXT NOT NULL,
                resumo_executivo TEXT NOT NULL,
                key_insight TEXT NOT NULL,
                data_inclusao DATE NOT NULL,
                status TEXT DEFAULT 'Não lido',
                notas_pessoais TEXT DEFAULT ''
            )
        """
        )

        for item in dados["leituras"]:
            cursor.execute(
                """
                INSERT INTO leituras (
                    titulo, autor_fonte, trilha, tempo_min, url,
                    resumo_executivo, key_insight, data_inclusao, status, notas_pessoais
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Não lido', '')
            """,
                (
                    item["titulo"],
                    item["autor_fonte"],
                    item["trilha"],
                    item["tempo_min"],
                    item["url"],
                    item["resumo_executivo"],
                    item["key_insight"],
                    str(date.today()),
                ),
            )

        conn.commit()


if __name__ == "__main__":
    conteudo = gerar_conteudo()
    salvar_no_banco(conteudo)
    print("Curadoria do dia e Carta do Editor geradas com sucesso!")
