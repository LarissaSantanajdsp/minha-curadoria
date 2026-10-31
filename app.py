import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

# Configuração da página
st.set_page_config(
    page_title="Curadoria Executiva Diária",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_NAME = "curadoria.db"


def init_db():
    """Garante que as tabelas existam."""
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
        conn.commit()


def carregar_dados():
    with sqlite3.connect(DB_NAME) as conn:
        df_leituras = pd.read_sql_query(
            "SELECT * FROM leituras ORDER BY id DESC", conn
        )
        cursor = conn.cursor()
        cursor.execute(
            "SELECT conteudo, data FROM carta_editor ORDER BY id DESC LIMIT 1"
        )
        carta_row = cursor.fetchone()
        carta_texto = carta_row[0] if carta_row else None
        carta_data = carta_row[1] if carta_row else None
        return df_leituras, carta_texto, carta_data


def atualizar_registro(item_id, novo_status, novas_notas):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE leituras 
            SET status = ?, notas_pessoais = ?
            WHERE id = ?
        """,
            (novo_status, novas_notas, item_id),
        )
        conn.commit()


def adicionar_leitura(
    titulo, autor, trilha, tempo, url, resumo, insight, status
):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO leituras (
