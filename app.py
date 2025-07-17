import streamlit as st
import pandas as pd
import plotly.express as px

# ─── 0. Configuração e CSS ───────────────────────────────────────────────
st.set_page_config(page_title="GrafoBot", layout="wide")
st.markdown("""
<style>
  .reportview-container .main,
  .reportview-container .block-container,
  html, body { background-color: #FFFFFF; }
  .sidebar .sidebar-content { background-color: #F9F9F9; }
</style>
""", unsafe_allow_html=True)

# ─── 1. Utilitários e cache ───────────────────────────────────────────────
@st.cache_data
def load_data(f):
    return pd.read_csv(f) if f.name.lower().endswith(".csv") else pd.read_excel(f)

@st.cache_data
def aggregate_df(df, x, y, agg, by=None):
    funcs = {
        "Média": "mean", "Soma": "sum", "Contagem": "count",
        "Contagem distinta": "nunique", "Mínimo": "min", "Máximo": "max"
    }
    cols = [x] + ([by] if by else [])
    if agg == "Contagem":
        return df.groupby(cols)[y].count().reset_index(name=y)
    if agg == "Contagem distinta":
        return df.groupby(cols)[y].nunique().reset_index(name=y)
    return df.groupby(cols)[y].agg(funcs[agg]).reset_index(name=y)

def col_type(df, c):
    dt = df[c].dtype
    if pd.api.types.is_numeric_dtype(dt):        return "Numérica"
    if pd.api.types.is_bool_dtype(dt):           return "Booleana"
    if pd.api.types.is_datetime64_any_dtype(dt): return "Data/Hora"
    if pd.api.types.is_categorical_dtype(dt) or df[c].nunique() < 20:
        return "Categórica"
    return "Texto"

def format_cols(df):
    return [f"{c} ({col_type(df,c)})" for c in df.columns]

def unlabel(lbl):
    return lbl.split(" (")[0]

# ─── 2. Sidebar: projeto, upload, reset tudo ──────────────────────────────
PROJECTS = {
    "Projeto Alpha": ["#005CA9","#FFA726","#66BB6A","#EF5350","#AB47BC"],
    "Projeto Beta":  ["#FFD700","#0E4C92","#E63946","#457B9D","#2A9D8F"],
    "Projeto Gamma": ["#FF5733","#33FFBD","#3385FF","#FF33A8","#8D33FF"],
}

st.sidebar.title("GrafoBot")
project = st.sidebar.selectbox("1. Projeto", list(PROJECTS.keys()), key="proj")
uploaded = st.sidebar.file_uploader("2. Upload CSV/XLSX", ["csv","xlsx"], key="up")

if st.sidebar.button("🔄 Resetar tudo"):
    for k in list(st.session_state.keys()):
        if k not in ("proj","df_orig","df_filtered"):
            del st.session_state[k]
    st.rerun()

if not uploaded:
    st.sidebar.info("Faça upload de um arquivo CSV ou XLSX para começar.")
    st.stop()

# ─── 3. Carregar dados ────────────────────────────────────────────────────
df0 = load_data(uploaded)
st.session_state["df_orig"] = df0
st.session_state.setdefault("df_filtered", df0.copy())
palette = PROJECTS[project]
df_orig = st.session_state["df_orig"]
df       = st.session_state["df_filtered"]

# ─── 4. Callbacks de filtro ───────────────────────────────────────────────
def apply_filters():
    temp = df_orig.copy()
    for c in st.session_state["flt_cols"]:
        key = f"flt_{c}"
        if key not in st.session_state: continue
        t = col_type(df_orig, c)
        if t == "Numérica":
            lo, hi = st.session_state[key]
            temp = temp[(temp[c] >= lo) & (temp[c] <= hi)]
        elif t == "Categórica":
            sel = st.session_state[key]
            temp = temp[temp[c].isin(sel)]
        elif t == "Data/Hora":
            start, end = st.session_state[key]
            dates = pd.to_datetime(df_orig[c]).dt.date
            temp = temp[(dates >= start) & (dates <= end)]
    st.session_state["df_filtered"] = temp

def reset_filters():
    for c in st.session_state.get("flt_cols", []):
        st.session_state.pop(f"flt_{c}", None)
    st.session_state["flt_cols"] = []
    st.session_state["df_filtered"] = df_orig.copy()

# ─── 5. Navegação por abas ─────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(
    ["🔍 Filtros", "📊 Barras", "🔎 Dispersão", "📋 Tabela"]
)

# ─── Aba 1: Filtros ────────────────────────────────────────────────────────
with tab1:
    st.header("🔍 Filtros de Dados")
    st.info(
        "1) Escolha as colunas que deseja filtrar.\n"
        "2) Defina intervalos (numérico/data) ou seleções (categórico).\n"
        "3) Os filtros são aplicados automaticamente e serão usados em todas as abas abaixo.\n"
        "4) Para limpar, clique em 'Resetar filtros'."
    )

    st.session_state.setdefault("flt_cols", [])
    cols = st.multiselect(
        "Colunas para filtrar",
        df_orig.columns.tolist(),
        default=st.session_state["flt_cols"],
        key="flt_cols",
        on_change=apply_filters
    )
    for c in cols:
        key = f"flt_{c}"
        t = col_type(df_orig, c)
        if t == "Numérica":
            mn, mx = float(df_orig[c].min()), float(df_orig[c].max())
            st.slider(c, mn, mx,
                      value=st.session_state.get(key, (mn, mx)),
                      key=key, on_change=apply_filters)
        elif t == "Categórica":
            opts = [v for v in df_orig[c].dropna().unique().tolist()]
            prev = st.session_state.get(key, opts)
            default = [v for v in prev if v in opts] or opts
            st.multiselect(c, opts, default=default, key=key, on_change=apply_filters)
        elif t == "Data/Hora":
            dates = pd.to_datetime(df_orig[c]).dt.date
            dmin, dmax = dates.min(), dates.max()
            prev = st.session_state.get(key, (dmin, dmax))
            start, end = prev if isinstance(prev, (list,tuple)) else (dmin, dmax)
            st.date_input(c, value=(start, end), key=key, on_change=apply_filters)

    st.button("🔄 Resetar filtros", on_click=reset_filters)
    st.write(f"Linhas após filtro: {len(st.session_state['df_filtered'])}")
    st.dataframe(st.session_state["df_filtered"].head(10))

# ─── Aba 2: Gráfico de Barras ─────────────────────────────────────────────
with tab2:
    st.header("📊 Gráfico de Barras")
    st.info(
        "1) Selecione a coluna para o eixo X (categórica/texto).\n"
        "2) Selecione a coluna para o eixo Y (numérica).\n"
        "3) Escolha a função de agregação.\n"
        "4) Use 'Avançado' para renomear e adicionar metadados.\n"
        "5) Clique em 'Gerar gráfico' para visualizar e exportar."
    )

    opts_x = format_cols(df)
    prev_x = st.session_state.get("bar_x", opts_x[0])
    idx_x = opts_x.index(prev_x) if prev_x in opts_x else 0
    x_lbl = st.selectbox("X (cat/texto)", opts_x, index=idx_x, key="bar_x")

    opts_y = format_cols(df)
    prev_y = st.session_state.get("bar_y", opts_y[0])
    idx_y = opts_y.index(prev_y) if prev_y in opts_y else 0
    y_lbl = st.selectbox("Y (numérico)", opts_y, index=idx_y, key="bar_y")

    agg_opts = ["Média","Soma","Contagem","Contagem distinta","Mínimo","Máximo"]
    prev_a = st.session_state.get("bar_agg", agg_opts[0])
    idx_a = agg_opts.index(prev_a) if prev_a in agg_opts else 0
    agg = st.selectbox("Agregação", agg_opts, index=idx_a, key="bar_agg")

    x, y = unlabel(x_lbl), unlabel(y_lbl)
    with st.expander("⚙️ Avançado", expanded=False):
        st.text_input("Rótulo X", value=st.session_state.get("bar_xlabel", x), key="bar_xlabel")
        st.text_input("Rótulo Y", value=st.session_state.get("bar_ylabel", y), key="bar_ylabel")
        clr_opts = ["Nenhum"] + format_cols(df)
        prev_c = st.session_state.get("bar_color", clr_opts[0])
        idx_c = clr_opts.index(prev_c) if prev_c in clr_opts else 0
        st.selectbox("Colorir por", clr_opts, index=idx_c, key="bar_color")
        st.text_input("Título", value=st.session_state.get("bar_title", f"{agg} de {y} por {x}"), key="bar_title")
        st.text_area("Fonte/ano", value=st.session_state.get("bar_meta", ""), key="bar_meta")
        st.checkbox("Exibir valores", value=st.session_state.get("bar_show", True), key="bar_show")
        st.number_input("Decimais", 0, 6, st.session_state.get("bar_dec", 2), key="bar_dec")

    if st.button("Gerar gráfico", key="bar_go"):
        color_by = unlabel(st.session_state["bar_color"]) if st.session_state["bar_color"]!="Nenhum" else None
        df2 = aggregate_df(df, x, y, agg, by=color_by)
        labels = df2[y].round(st.session_state["bar_dec"]) if st.session_state["bar_show"] else None
        fig = px.bar(
            df2, x=x, y=y, color=color_by,
            color_discrete_sequence=palette,
            title=st.session_state["bar_title"], text=labels
        )
        if color_by is None:
            fig.update_traces(marker_color=palette[0]); fig.update_layout(showlegend=False)
        fig.update_layout(
            paper_bgcolor="white", plot_bgcolor="white", font_color="black",
            xaxis_title=st.session_state["bar_xlabel"],
            yaxis_title=st.session_state["bar_ylabel"]
        )
        fig.update_traces(texttemplate="%{text}", textposition="auto")
        if st.session_state["bar_meta"].strip():
            fig.add_annotation(
                text=st.session_state["bar_meta"],
                xref="paper", yref="paper",
                x=0, y=-0.22, showarrow=False,
                font=dict(size=12, color="black"), align="left"
            )
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("📥 Baixar CSV", df2.to_csv(index=False).encode(), "bar.csv", "text/csv")

# ─── Aba 3: Gráfico de Dispersão ─────────────────────────────────────────
with tab3:
    st.header("🔎 Gráfico de Dispersão")
    st.info(
        "1) Selecione eixos X e Y.\n"
        "2) Escolha agregação e coluna de cor (opcional).\n"
        "3) No 'Avançado' ajuste rótulos, título e metadados.\n"
        "4) Clique em 'Gerar gráfico' para ver e exportar."
    )

    opts_x = format_cols(df)
    prev_x = st.session_state.get("sc_x", opts_x[0])
    idx_x = opts_x.index(prev_x) if prev_x in opts_x else 0
    x_lbl = st.selectbox("X", opts_x, index=idx_x, key="sc_x")

    opts_y = format_cols(df)
    prev_y = st.session_state.get("sc_y", opts_y[0])
    idx_y = opts_y.index(prev_y) if prev_y in opts_y else 0
    y_lbl = st.selectbox("Y", opts_y, index=idx_y, key="sc_y")

    agg_opts = ["Média","Soma","Contagem","Mínimo","Máximo"]
    prev_a = st.session_state.get("sc_agg", agg_opts[0])
    idx_a = agg_opts.index(prev_a) if prev_a in agg_opts else 0
    agg = st.selectbox("Agregação", agg_opts, index=idx_a, key="sc_agg")

    clr_opts = ["Nenhum"] + format_cols(df)
    prev_c = st.session_state.get("sc_color", clr_opts[0])
    idx_c = clr_opts.index(prev_c) if prev_c in clr_opts else 0
    clr = st.selectbox("Colorir por", clr_opts, index=idx_c, key="sc_color")

    x, y = unlabel(x_lbl), unlabel(y_lbl)
    with st.expander("⚙️ Avançado", expanded=False):
        st.text_input("Rótulo X", value=st.session_state.get("sc_xlabel", x), key="sc_xlabel")
        st.text_input("Rótulo Y", value=st.session_state.get("sc_ylabel", y), key="sc_ylabel")
        st.text_input("Título", value=st.session_state.get("sc_title", f"{agg} de {y} por {x}"), key="sc_title")
        st.text_area("Fonte/ano", value=st.session_state.get("sc_meta", ""), key="sc_meta")
        st.checkbox("Exibir valores", value=st.session_state.get("sc_show", False), key="sc_show")
        st.number_input("Decimais", 0, 6, st.session_state.get("sc_dec", 2), key="sc_dec")

    if st.button("Gerar gráfico", key="sc_go"):
        color_by = unlabel(st.session_state["sc_color"]) if st.session_state["sc_color"]!="Nenhum" else None
        df2 = aggregate_df(df, x, y, agg, by=color_by)
        labels = df2[y].round(st.session_state["sc_dec"]) if st.session_state["sc_show"] else None
        fig = px.scatter(
            df2, x=x, y=y, color=color_by,
            color_discrete_sequence=palette,
            title=st.session_state["sc_title"], text=labels
        )
        if color_by is None:
            fig.update_traces(marker_color=palette[0], showlegend=False)
        fig.update_layout(
            paper_bgcolor="white", plot_bgcolor="white", font_color="black",
            xaxis_title=st.session_state["sc_xlabel"],
            yaxis_title=st.session_state["sc_ylabel"]
        )
        fig.update_traces(mode="markers+text", textposition="top center")
        if st.session_state["sc_meta"].strip():
            fig.add_annotation(
                text=st.session_state["sc_meta"],
                xref="paper", yref="paper",
                x=0, y=-0.22, showarrow=False,
                font=dict(size=12, color="black"), align="left"
            )
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("📥 Baixar CSV", df2.to_csv(index=False).encode(), "sc.csv", "text/csv")

# ─── Aba 4: Tabela de Agregação ────────────────────────────────────────────
with tab4:
    st.header("📋 Tabela de Agregação")
    st.info(
        "1) Escolha a coluna categórica para agrupar.\n"
        "2) Escolha a coluna numérica para agregar.\n"
        "3) Selecione a função desejada.\n"
        "4) Clique em 'Gerar tabela' e exporte em CSV."
    )

    cats = [o for o in format_cols(df) if "(Categórica)" in o or "(Texto)" in o]
    nums = [o for o in format_cols(df) if "(Numérica)" in o]

    prev_x = st.session_state.get("tab_x")
    idx_x = cats.index(prev_x) if prev_x in cats else 0
    st.session_state["tab_x"] = cats[idx_x]
    x_lbl = st.selectbox("Agrupar por", cats, index=idx_x, key="tab_x")

    prev_y = st.session_state.get("tab_y")
    idx_y = nums.index(prev_y) if prev_y in nums else 0
    st.session_state["tab_y"] = nums[idx_y]
    y_lbl = st.selectbox("Valor", nums, index=idx_y, key="tab_y")

    agg_opts = ["Média","Soma","Contagem","Mínimo","Máximo"]
    prev_a = st.session_state.get("tab_agg")
    idx_a = agg_opts.index(prev_a) if prev_a in agg_opts else 0
    st.session_state["tab_agg"] = agg_opts[idx_a]
    agg = st.selectbox("Função", agg_opts, index=idx_a, key="tab_agg")

    if st.button("Gerar tabela", key="tab_go"):
        x, y = unlabel(x_lbl), unlabel(y_lbl)
        df2 = aggregate_df(df, x, y, agg)
        st.dataframe(df2)
        st.download_button("📥 Baixar CSV", df2.to_csv(index=False).encode(), "table.csv", "text/csv")
