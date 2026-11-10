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

FEEDS_POR_TRILHA = {
    "Acadêmica & Pesquisa (IA/LLMs)": [
        "https://export.arxiv.org/rss/cs.IR",
        "https://export.arxiv.org/rss/cs.CL",
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

    prompt = (
        f"Atue como um Curador-Chefe de Inteligência Executiva. Data: {date.today()}.\n"
        "Abaixo estão 3 artigos REAIS coletados hoje de fontes oficiais.\n"
        "1. Redija uma 'Carta do Editor' em português do Brasil conectando os temas desses 3 artigos.\n"
        "2. Para cada artigo, escreva um resumo executivo em português do Brasil (2 parágrafos) e um 'Key Insight' prático baseado EXCLUSIVAMENTE no texto.\n\n"
        f"ARTIGOS REAIS:\n{json.dumps(artigos_reais, ensure_ascii=False)}\n\n"
        'Responda EXCLUSIVAMENTE com um JSON válido nesta estrutura:\n'
        '{"carta_editor": "Texto da carta...", "itens": ['
        '{"indice": 0, "titulo_pt": "Título em PT", "tempo_min": 8, "resumo_executivo": "Resumo...", "key_insight": "Insight..."},'
        '{"indice": 1, "titulo_pt": "Título em PT", "tempo_min": 10, "resumo_executivo": "Resumo...", "key_insight": "Insight..."},'
        '{"indice": 2, "titulo_pt": "Título em PT", "tempo_min": 7, "resumo_executivo": "Resumo...", "key_insight": "Insight..."}'
        ']}'
    )

    modelos = [
        "gemini-2.5-flash",
        "gemini-3.8-pro",
        "gemini-2.5-pro",
        "gemini-3.5-flash-lite",
        "gemini-3.8-flash",
    ]

    for tentativa in range(len(modelos)):
        modelo_atual = modelos[tentativa]
        try:
            print(f"Tentativa {tentativa + 1} usando o modelo {modelo_atual}...")
            response = client.models.generate_content(
                model=modelo_atual,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
            resultado_ia = extrair_json(response.text)

            leituras_finais = []
            for item_ia in resultado_ia["itens"]:
                idx = item_ia["indice"]
                artigo_original = artigos_reais[idx]
                leituras_finais.append({
                    "titulo": item_ia["titulo_pt"],
                    "autor_fonte": artigo_original["fonte"],
                    "trilha": artigo_original["trilha"],
                    "tempo_min": item_ia.get("tempo_min", 8),
                    "url": artigo_original["url_real"],
                    "resumo_executivo": item_ia["resumo_executivo"],
                    "key_insight": item_ia["key_insight"],
                })

            return {
                "carta_editor": resultado_ia["carta_editor"],
                "leituras": leituras_finais,
            }
        except Exception as e:
            print(f"Modelo {modelo_atual} indisponível ({e}). Tentando próximo servidor em 10s...")
            time.sleep(10)

    # Plano C: Se todos os servidores de IA estiverem congestionados, entrega os artigos reais diretamente
    print("Servidores de IA congestionados. Gerando edição direta a partir dos feeds oficiais...")
    leituras_diretas = []
    for art in artigos_reais:
        leituras_diretas.append({
            "titulo": art["titulo_original"],
            "autor_fonte": art["fonte"],
            "trilha": art["trilha"],
            "tempo_min": 8,
            "url": art["url_real"],
            "resumo_executivo": art["texto_base"] or "Acesse o artigo original no botão abaixo para leitura completa.",
            "key_insight": "Artigo selecionado diretamente do feed oficial da fonte.",
        })

    return {
        "carta_editor": f"Seleção diária de {date.today()} extraída diretamente das fontes oficiais (arXiv, Search Engine Land, MIT Sloan e HBR).",
        "leituras": leituras_diretas,
    }


def salvar_no_banco(dados):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS carta_editor ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "data DATE NOT NULL UNIQUE, "
            "conteudo TEXT NOT NULL)"
        )

        cursor.execute(
            "INSERT OR REPLACE INTO carta_editor (data, conteudo) VALUES (?, ?)",
            (str(date.today()), dados["carta_editor"]),
        )

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS leituras ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "titulo TEXT NOT NULL, "
            "autor_fonte TEXT NOT NULL, "
            "trilha TEXT NOT NULL, "
            "tempo_min INTEGER NOT NULL, "
            "url TEXT NOT NULL, "
            "resumo_executivo TEXT NOT NULL, "
            "key_insight TEXT NOT NULL, "
            "data_inclusao DATE NOT NULL, "
            "status TEXT DEFAULT 'Não lido', "
            "notas_pessoais TEXT DEFAULT '')"
        )

        cursor.execute("DELETE FROM leituras WHERE data_inclusao = ?", (str(date.today()),))

        for item in dados["leituras"]:
            cursor.execute(
                "INSERT INTO leituras ("
                "titulo, autor_fonte, trilha, tempo_min, url, "
                "resumo_executivo, key_insight, data_inclusao, status, notas_pessoais"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Não lido', '')",
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
    msg["Subject"] = f"Curadoria Executiva Diária - {date.today()}"
    msg["From"] = EMAIL_REMETENTE
    msg["To"] = EMAIL_REMETENTE

    html_leituras = ""
    for i, item in enumerate(dados["leituras"], 1):
        html_leituras += (
            '<div style="border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin-bottom: 16px; background-color: #ffffff;">'
            f'<span style="background-color: #eef2ff; color: #3730a3; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">'
            f"{item['trilha']} - {item['tempo_min']} min</span>"
            f'<h3 style="margin: 10px 0 4px 0; color: #111827;">{i}. {item["titulo"]}</h3>'
            f'<p style="margin: 0 0 12px 0; font-size: 13px; color: #6b7280;">Fonte: {item["autor_fonte"]}</p>'
            f'<p style="color: #374151; line-height: 1.5;">{item["resumo_executivo"]}</p>'
            f'<div style="background-color: #f0fdf4; border-left: 4px solid #16a34a; padding: 10px; margin: 12px 0; color: #166534;">'
            f'<strong>Key Insight:</strong> {item["key_insight"]}</div>'
            f'<a href="{item["url"]}" style="display: inline-block; background-color: #111827; color: #ffffff; text-decoration: none; padding: 8px 14px; border-radius: 5px; font-size: 13px;">'
            'Acessar Fonte Original</a></div>'
        )

    carta_formatada = dados["carta_editor"].replace("\n", "<br>")

    html_completo = (
        '<html><body style="font-family: Arial, sans-serif; background-color: #f9fafb; padding: 20px; color: #1f2937;">'
        '<div style="max-width: 650px; margin: auto;">'
        f'<h2 style="color: #111827; border-bottom: 2px solid #111827; padding-bottom: 8px;">Carta do Editor ({date.today()})</h2>'
        f'<div style="background-color: #ffffff; padding: 16px; border-radius: 8px; border: 1px solid #e5e7eb; line-height: 1.6; margin-bottom: 24px;">{carta_formatada}</div>'
        '<h2 style="color: #111827; border-bottom: 2px solid #111827; padding-bottom: 8px;">Leituras Selecionadas</h2>'
        f'{html_leituras}'
        '</div></body></html>'
    )

    msg.attach(MIMEText(html_completo, "html"))

    server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
    server.login(EMAIL_REMETENTE, EMAIL_SENHA)
    server.sendmail(EMAIL_REMETENTE, EMAIL_REMETENTE, msg.as_string())
    server.quit()
    print("E-mail enviado com sucesso!")


if __name__ == "__main__":
    artigos_reais = coletar_artigos_reais()
    conteudo = gerar_curadoria_com_ia(artigos_reais)
    salvar_no_banco(conteudo)
    enviar_email(conteudo)
    print("Processo completo finalizado com fontes reais!")

# FIM DO ARQUIVO
