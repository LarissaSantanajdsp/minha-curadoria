from datetime import date
import sqlite3
import streamlit as st

st.set_page_config(
    page_title="Curadoria Executiva Diária",
    page_icon="📖",
    layout="wide",
)

DB_NAME = "curadoria.db"


def inicializar_banco():
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
        conn.commit()


def carregar_datas():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT data_inclusao FROM leituras ORDER BY data_inclusao DESC"
        )
        return [row[0] for row in cursor.fetchall()]


def carregar_carta(data_selecionada):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT conteudo FROM carta_editor WHERE data = ?",
            (data_selecionada,),
        )
        row = cursor.fetchone()
        return row[0] if row else None


def carregar_leituras(data_selecionada):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM leituras WHERE data_inclusao = ? ORDER BY id ASC",
            (data_selecionada,),
        )
        return cursor.fetchall()


def atualizar_leitura(leitura_id, novo_status, novas_notas):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE leituras SET status = ?, notas_pessoais = ? WHERE id = ?",
            (novo_status, novas_notas, leitura_id),
        )
        conn.commit()


inicializar_banco()

st.title("📖 Curadoria Executiva Diária")
st.caption("GEO • Inteligência Artificial • Liderança & Comunicação")

datas_disponiveis = carregar_datas()

if not datas_disponiveis:
    st.info(
        "Nenhuma curadoria encontrada ainda. Execute o fluxo no GitHub Actions para gerar a primeira edição."
    )
else:
    data_escolhida = st.sidebar.selectbox(
        "📅 Selecione a edição:",
        options=datas_disponiveis,
        index=0,
    )

    aba_carta, aba_leituras = st.tabs(
        ["✉️ Carta do Editor", "📚 Leituras Selecionadas"]
    )

    with aba_carta:
        carta = carregar_carta(data_escolhida)
        if carta:
            st.markdown(carta)
        else:
            st.warning("Não há Carta do Editor registrada para esta data.")

    with aba_leituras:
        leituras = carregar_leituras(data_escolhida)
        for item in leituras:
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{item['trilha']}** • ⏱️ {item['tempo_min']} min")
                    st.subheader(item["titulo"])
                    st.caption(f"Fonte: {item['autor_fonte']}")
                with col2:
                    st.link_button(
                        "Abrir Fonte ↗", item["url"], use_container_width=True
                    )

                st.write(item["resumo_executivo"])
                st.success(f"💡 **Key Insight:** {item['key_insight']}")

                with st.expander("📝 Anotações e Status de Leitura"):
                    status_opcoes = ["Não lido", "Lido", "Favorito"]
                    idx_status = (
                        status_opcoes.index(item["status"])
                        if item["status"] in status_opcoes
                        else 0
                    )
                    novo_status = st.selectbox(
                        "Status",
                        status_opcoes,
                        index=idx_status,
                        key=f"status_{item['id']}",
                    )
                    novas_notas = st.text_area(
                        "Suas anotações",
                        value=item["notas_pessoais"] or "",
                        key=f"notas_{item['id']}",
                    )
                    if st.button("Salvar", key=f"btn_{item['id']}"):
                        atualizar_leitura(item["id"], novo_status, novas_notas)
                        st.toast("Anotação salva!")
