import json
import os
import random
import re
import smtplib
import sqlite3
import time
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import feedparser
from google import genai
from google.genai import types

DB_NAME = "curadoria.db"
API_KEY = os.environ.get("API_KEY")
EMAIL_REMETENTE = os.environ.get("EMAIL_REMETENTE")
EMAIL_SENHA = os.environ.get("EMAIL_SENHA")

# Fontes reais com RSS oficial divididas por trilha
FEEDS_POR_TRILHA = {
    "Acadêmica & Pesquisa (IA/LLMs)": [
        "https://export.arxiv.org/rss/cs.IR",  # Information Retrieval (Busca e GEO)
        "https://export.arxiv.org/rss/cs.CL",  # Computation and Language (LLMs)
    ],
    "Aplicação de Mercado (GEO & Search)": [
        "https://searchengineland.com/feed",
        "https://www.searchenginejournal.com/feed/",
        "https://www.kevin-indig.com/feed/",
    ],
    "Liderança & Comportamento": [
        "https://sloanreview.mit.edu/feed/",
        "http://feeds.harvardbusiness.org/harvardbusiness",
    ],
}


def coletar_artigos_reais():
    artigos_coletados = []

    for trilha, urls_feeds in FEEDS_POR_TRILHA.items():
        candidatos_trilha = []
        for feed_url in urls_feeds:
            try:
                feed = feedparser.parse(feed_url)
                fonte_nome = feed.feed.get("title", feed_url)
                for entry in feed.entries[:6]:
                    link_real = entry.get("link", "").strip()
                    titulo_real = entry.get("title", "").strip()
                    resumo_bruto = entry.get("summary", entry.get("description", ""))
                    # Remove tags HTML do resumo bruto
                    resumo_limpo = re.sub(r"<[^<]+?>", "", resumo_bruto)[:1200]

                    if link_real.startswith("http") and titulo_real:
                        candidatos_trilha.append({
                            "trilha": trilha,
                            "fonte": fonte_nome,
                            "titulo_original": titulo_real,
                            "url_real": link_real,
                            "texto_base": resumo_limpo,
                        })
            except Exception as e:
                print(f"Aviso ao ler feed {feed_url}: {e}")

        if candidatos_trilha:
            # Escolhe 1 artigo real recente desta trilha
            escolhido = random.choice(candidatos_trilha[:5])
            artigos_coletados.append(escolhido)

    if len(artigos_coletados) < 3:
        raise RuntimeError("Não foi possível coletar artigos reais suficientes dos feeds.")

    return artigos_coletados


def extrair_json(texto):
    texto_limpo = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip(), flags=re.MULTILINE)
    return json.loads(texto_limpo)


def gerar_curadoria_com_ia(artigos_reais):
    client = genai.Client(api_key=API_KEY)

    prompt = f"""
    Atue como um Curador-Chefe de Inteligência Executiva.
    Data de referência: {date.today()}.

    Abaixo estão 3 artigos REAIS coletados hoje de fontes oficiais.
    Sua tarefa é:
    1. Redigir uma "Carta do Editor" em português do Brasil conectando os temas desses 3 artigos e explicando por que importam hoje.
    2. Para cada um dos 3 artigos, escrever um resumo executivo claro em português do Brasil (2 parágrafos) e extrair um "Key Insight" prático e contra-intuitivo baseado EXCLUSIVAMENTE no texto fornecido.

    ARTIGOS REAIS COLETADOS:
    {json.dumps(artigos_reais, ensure_ascii=False, indent=2)}

    Responda EXCLUSIVAMENTE com um JSON válido nesta estrutura:
    {{
      "carta_editor": "Texto completo da carta em português do Brasil...",
      "itens": [
        {{
          "indice": 0,
          "titulo_pt": "Tradução fiel do título para português (ou título original se for nome próprio)",
          "tempo_min": 8,
          "resumo_executivo": "Resumo executivo em português...",
          "key_insight": "Insight prático extraído do texto..."
        }},
        {{
          "indice": 1,
          "titulo_pt": "...",
          "tempo_min": 10,
          "resumo_executivo": "...",
          "key_insight": "..."
        }},
        {{
          "indice": 2,
          "titulo_pt": "...",
          "tempo_min": 7,
          "resumo_executivo": "...",
          "key_insight": "..."
        }}
      ]
    }}
    """

   modelos = ["gemini-3.5-flash-lite", "gemini-3.8-flash"]

    for tentativa in range(5):
        modelo_atual = modelos[tentativa % len(modelos)]
        try:
            print(f"Tentativa {tentativa + 1} processando artigos reais com {modelo_atual}...")
            response = client.models.generate_content(
                model=modelo_atual,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
            resultado_ia = extrair_json(response.text)

            # Monta o resultado final mantendo as URLs 100% originais coletadas pelo Python
            leituras_finais = []
            for item_ia in resultado_ia["itens"]:
                idx = item_ia["indice"]
                artigo_original = artigos_reais[idx]
                leituras_finais.append({
                    "titulo": item_ia["titulo_pt"],
                    "autor_fonte": artigo_original["fonte"],
                    "trilha": artigo_original["trilha"],
                    "tempo_min": item_ia.get("tempo_min", 8),
                    "url": artigo_original["url_real"],  # URL real intocada pela IA
                    "resumo_executivo": item_ia["resumo_executivo"],
                    "key_insight": item_ia["key_insight"],
                })

            return {
                "carta_editor": resultado_ia["carta_editor"],
                "leituras": leituras_finais,
            }
        except Exception as e:
            print(f"Erro temporário ({e}). Aguardando 30 segundos...")
            time.sleep(30)

    raise RuntimeError("Não foi possível gerar a curadoria após 5 tentativas.")


def salvar_no_banco(dados):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS carta_editor (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data DATE NOT NULL UNIQUE,
                conteudo TEXT NOT NULL
            )
        """)

        cursor.execute("""
            INSERT OR REPLACE INTO carta_editor (data, conteudo)
            VALUES (?, ?)
        """, (str(date.today()), dados["carta_editor"]))

        cursor.execute("""
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
        """)

        cursor.execute("DELETE FROM leituras WHERE data_inclusao = ?", (str(date.today()),))

        for item in dados["leituras"]:
            cursor.execute("""
                INSERT INTO leituras (
                    titulo, autor_fonte, trilha, tempo_min, url,
                    resumo_executivo, key_insight, data_inclusao, status, notas_pessoais
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Não lido', '')
            """, (
                item["titulo"],
                item["autor_fonte"],
                item["trilha"],
                item["tempo_min"],
                item["url"],
                item["resumo_executivo"],
                item["key_insight"],
                str(date.today()),
            ))

        conn.commit()


def enviar_email(dados):
    if not EMAIL_REMETENTE or not EMAIL_SENHA:
        print("Credenciais de e-mail não configuradas. Pulando envio.")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📖 Curadoria Executiva Diária — {date.today()}"
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_REMETENTE

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
    artigos_reais = coletar_artigos_reais()
    conteudo = gerar_curadoria_com_ia(artigos_reais)
    salvar_no_banco(conteudo)
    enviar_email(conteudo)
    print("Processo completo finalizado com fontes reais!")
