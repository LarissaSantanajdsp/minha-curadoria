import json
import os
import smtplib
import sqlite3
import time
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google import genai
from google.genai import types

DB_NAME = "curadoria.db"
API_KEY = os.environ.get("API_KEY")
EMAIL_REMETENTE = os.environ.get("EMAIL_REMETENTE")
EMAIL_SENHA = os.environ.get("EMAIL_SENHA")


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
      "carta_editor": "Texto completo da carta em formato limpo...",
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

    raise RuntimeError("Não foi possível gerar a curadoria após 5 tentativas.")


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


def enviar_email(dados):
    if not EMAIL_REMETENTE or not EMAIL_SENHA:
        print("Credenciais de e-mail não configuradas. Pulando envio.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📖 Curadoria Executiva Diária — {date.today()}"
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_REMETENTE

    # Monta o corpo do e-mail em HTML limpo
    html_leituras = ""
    for i, item in enumerate(dados["leituras"], 1):
        html_leituras += f"""
        <div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 16px; background-color: #ffffff;">
            <span style="background-color: #eef2ff; color: #3730a3; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">
                {item['trilha']} • ⏱️ {item['tempo_min']} min
            </span>
            <h3 style="margin: 10px 0 4px 0; color: #111827;">{i}. {item['titulo']}</h3>
            <p style="margin: 0 0 12px 0; font-size: 13px; color: #6b7280;">Fonte: {item['autor_fonte']}</p>
            <p style="color: #374151; line-height: 1.5;">{item['resumo_executivo']}</p>
            <div style="background-color: #f0fdf4; border-left: 4px solid #16a34a; padding: 10px; margin: 12px 0; color: #166534;">
                <strong>💡 Key Insight:</strong> {item['key_insight']}
            </div>
            <a href="{item['url']}" style="display: inline-block; background-color: #111827; color: #ffffff; text-decoration: none; padding: 8px 14px; border-radius: 5px; font-size: 13px;">
                Acessar Fonte Original ↗
            </a>
        </div>
        """

    carta_formatada = dados["carta_editor"].replace("\n", "<br>")

    html_completo = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f9fafb; padding: 20px; color: #1f2937;">
        <div style="max-width: 650px; margin: auto;">
          <h2 style="color: #111827; border-bottom: 2px solid #111827; padding-bottom: 8px;">
            ✉️ Carta do Editor ({date.today()})
          </h2>
          <div style="background-color: #ffffff; padding: 16px; border-radius: 8px; border: 1px solid #e5e7eb; line-height: 1.6; margin-bottom: 24px;">
            {carta_formatada}
          </div>
          
          <h2 style="color: #111827; border-bottom: 2px solid #111827; padding-bottom: 8px;">
            📖 Leituras Selecionadas
          </h2>
          {html_leituras}
        </div>
      </body>
    </html>
    """

    msg.attach(MIMEText(html_completo, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_REMETENTE, EMAIL_SENHA)
        server.sendmail(EMAIL_REMETENTE, EMAIL_REMETENTE, msg.as_string())
    print("E-mail enviado com sucesso!")


if __name__ == "__main__":
    conteudo = gerar_conteudo()
    salvar_no_banco(conteudo)
    enviar_email(conteudo)
    print("Processo completo finalizado!")
