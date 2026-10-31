import sqlite3
from datetime import date
import pandas as pd
import streamlit as st

# Configuração inicial da página
st.set_page_config(
    page_title="Curadoria Executiva Diária",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_NAME = "curadoria.db"


def init_db():
    """Inicializa o banco de dados SQLite e insere sementes iniciais se vazio."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
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

        # Inserção de dados iniciais de exemplo se o banco estiver vazio
        cursor.execute("SELECT COUNT(*) FROM leituras")
        if cursor.fetchone()[0] == 0:
            dados_iniciais = [
                (
                    "GEO: Generative Engine Optimization",
                    "Aggarwal et al. (Princeton / Georgia Tech)",
                    "GEO & Search",
                    15,
                    "https://arxiv.org/abs/2311.09735",
                    "Estudo seminal que mede empiricamente como otimizar conteúdos para inclusão e citação em respostas de LLMs (SearchGPT, Perplexity, AI Overviews).",
                    "A inclusão de estatísticas proprietárias, termos técnicos claros e fontes primárias eleva a visibilidade do conteúdo em até 30% em respostas geradas por IA.",
                    str(date.today()),
                    "Não lido",
                    "",
                ),
                (
                    "AI-Driven Executive Communication & Leadership Credibility",
                    "Harvard Business Review / MIT Sloan",
                    "Liderança & IA",
                    8,
                    "https://hbr.org",
                    "Análise sobre como líderes utilizam IA para escalar mensagens institucionais sem perder ressonância emocional e senso de autenticidade.",
                    "Mensagens hiper-polidas por IA tendem a sofrer desconto de confiança se não contiverem posicionamentos de vulnerabilidade ou contexto proprietário claro.",
                    str(date.today()),
                    "Não lido",
                    "",
                ),
                (
                    "The Science of Audience Engagement in Corporate Keynotes",
                    "Journal of Organizational Behavior",
                    "Comunicação & Comportamento",
                    10,
                    "https://onlinelibrary.wiley.com",
                    "Pesquisa sobre modulação de ritmo cognitivo em palestras e encontros de alinhamento estratégico.",
                    "Audiências corporativas atingem pico de saturação aos 18 minutos; introduzir perguntas reflexivas ou quebras narrativas restaura a retenção para o restante da sessão.",
                    str(date.today()),
                    "Não lido",
                    "",
                ),
            ]
            cursor.executemany(
                """
                INSERT INTO leituras (
                    titulo, autor_fonte, trilha, tempo_min, url,
                    resumo_executivo, key_insight, data_inclusao, status, notas_pessoais
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                dados_iniciais,
            )
            conn.commit()


def carregar_dados():
    with sqlite3.connect(DB_NAME) as conn:
        return pd.read_sql_query("SELECT * FROM leituras ORDER BY id DESC", conn)


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
                titulo, autor_fonte, trilha, tempo_min, url,
                resumo_executivo, key_insight, data_inclusao, status, notas_pessoais
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '')
        """,
            (
                titulo,
                autor,
                trilha,
                tempo,
                url,
                resumo,
                insight,
                str(date.today()),
                status,
            ),
        )
        conn.commit()


# Inicializa o banco
init_db()
df = carregar_dados()

# --- SIDEBAR DE NAVEGAÇÃO E FILTROS ---
st.sidebar.title("📚 Filtros de Leitura")

todas_trilhas = ["Todas"] + sorted(df["trilha"].unique().tolist())
trilha_selecionada = st.sidebar.selectbox("Trilha temática:", todas_trilhas)

todos_status = ["Todos"] + sorted(df["status"].unique().tolist())
status_selecionado = st.sidebar.selectbox("Status:", todos_status)

tempo_max = st.sidebar.slider(
    "Tempo máximo disponível (minutos):",
    min_value=5,
    max_value=45,
    value=30,
    step=5,
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Métricas de Hábito")
lidos_count = len(df[df["status"] == "Lido"])
pauta_count = len(df[df["status"] == "Pauta Potencial"])
st.sidebar.metric("Leituras Concluídas", lidos_count)
st.sidebar.metric("Salvos para Pauta / Artigo", pauta_count)

# --- CORPO PRINCIPAL ---
st.title("Curadoria Executiva Diária")
st.caption(
    "Dose diária de inteligência em GEO, Liderança, IA e Comunicação Estratégica."
)

tab_leitura, tab_adicionar, tab_analytics = st.tabs(
    ["📖 Leituras do Dia", "➕ Cadastrar Nova Leitura", "📊 Visão Geral"]
)

# TAB 1: CARDS DE LEITURA
with tab_leitura:
    # Aplicação de filtros
    df_filtrado = df[df["tempo_min"] <= tempo_max]
    if trilha_selecionada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["trilha"] == trilha_selecionada]
    if status_selecionado != "Todos":
        df_filtrado = df_filtrado[df_filtrado["status"] == status_selecionado]

    if df_filtrado.empty:
        st.info("Nenhuma leitura encontrada com os filtros selecionados.")
    else:
        for _, row in df_filtrado.iterrows():
            with st.container(border=True):
                col_header1, col_header2 = st.columns([4, 1])
                with col_header1:
                    st.subheader(row["titulo"])
                    st.markdown(
                        f"**Fonte/Autor:** {row['autor_fonte']} | **Trilha:** `{row['trilha']}` | ⏱️ `{row['tempo_min']} min`"
                    )
                with col_header2:
                    st.link_button(
                        "Acessar Original ↗", row["url"], use_container_width=True
                    )

                st.markdown("#### Resumo Executivo")
                st.write(row["resumo_executivo"])

                st.info(f"💡 **Key Insight:** {row['key_insight']}")

                # Área de Ação e Status
                with st.expander("Gerenciar Status e Notas de Pauta"):
                    with st.form(key=f"form_{row['id']}"):
                        novo_status = st.selectbox(
                            "Status de Leitura:",
                            [
                                "Não lido",
                                "Lido",
                                "Pauta Potencial",
                                "Favorito",
                                "Arquivado",
                            ],
                            index=[
                                "Não lido",
                                "Lido",
                                "Pauta Potencial",
                                "Favorito",
                                "Arquivado",
                            ].index(row["status"]),
                        )
                        novas_notas = st.text_area(
                            "Notas pessoais / Ângulo para artigo ou mentoria:",
                            value=row["notas_pessoais"]
                            if row["notas_pessoais"]
                            else "",
                            placeholder="Como conectar isso com um caso corporativo ou coluna...",
                        )

                        salvar = st.form_submit_button("Atualizar")
                        if salvar:
                            atualizar_registro(
                                row["id"], novo_status, novas_notas
                            )
                            st.success("Atualizado com sucesso!")
                            st.rerun()

# TAB 2: ADICIONAR NOVO CONTEÚDO
with tab_adicionar:
    st.subheader("Adicionar Nova Recomendação de Conteúdo")
    with st.form(key="form_novo_conteudo", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            novo_titulo = st.text_input(
                "Título do Artigo / Paper:",
                placeholder="Ex: The Impact of RAG on Search Visibility",
            )
            novo_autor = st.text_input(
                "Autor ou Publicação:",
                placeholder="Ex: Kevin Indig / Growth Memo",
            )
            nova_url = st.text_input("Link (URL):", placeholder="https://...")
        with c2:
            nova_trilha = st.selectbox(
                "Trilha Temática:",
                [
                    "GEO & Search",
                    "Liderança & IA",
                    "Comunicação & Comportamento",
                    "Pesquisa & Métodos",
                    "Negócios & Mídia",
                ],
            )
            novo_tempo = st.number_input(
                "Tempo estimado de leitura (minutos):",
                min_value=1,
                max_value=120,
                value=10,
            )
            status_inicial = st.selectbox(
                "Status Inicial:", ["Não lido", "Pauta Potencial", "Lido"]
            )

        novo_resumo = st.text_area(
            "Resumo Executivo (2 a 3 parágrafos):",
            placeholder="Visão geral do texto e premissas centrais...",
        )
        novo_insight = st.text_input(
            "Key Insight (O dado, reflexão ou conclusão contra-intuitiva):",
            placeholder="Ex: O aumento de citações requer...",
        )

        botao_cadastrar = st.form_submit_button("Salvar no Banco")

        if botao_cadastrar:
            if novo_titulo and novo_url and novo_resumo:
                adicionar_leitura(
                    novo_titulo,
                    novo_autor,
                    nova_trilha,
                    novo_tempo,
                    novo_url,
                    novo_resumo,
                    novo_insight,
                    status_inicial,
                )
                st.success("Leitura cadastrada com sucesso!")
                st.rerun()
            else:
                st.error(
                    "Por favor, preencha ao menos Título, URL e Resumo Executivo."
                )

# TAB 3: VISÃO GERAL / EXPORTAÇÃO
with tab_analytics:
    st.subheader("Acervo Completo")
    st.dataframe(
        df[
            [
                "titulo",
                "trilha",
                "tempo_min",
                "status",
                "data_inclusao",
                "notas_pessoais",
            ]
        ],
        use_container_width=True,
    )

    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Exportar Base para CSV",
        data=csv_data,
        file_name=f"acervo_leituras_{date.today()}.csv",
        mime="text/csv",
    )
