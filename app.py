import streamlit as st
import plotly.express as px
import pandas as pd
import os

st.set_page_config(
    page_title= "IDH Brasil",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

path = "Tabela4.csv"

df = pd.read_csv(path, sep=";", skiprows=1, decimal=",", encoding="latin-1")
df = df.dropna(axis=1, how="all")

@st.cache_data
def carregar_e_limpar_afazeres(caminho_ou_arquivo):
    if isinstance(caminho_ou_arquivo, str):
        if caminho_ou_arquivo.lower().endswith(".csv"):
            bruto = pd.read_csv(caminho_ou_arquivo, header=None)
        else:
            bruto = pd.read_excel(caminho_ou_arquivo, engine="xlrd", header=None)
    else:
        nome = caminho_ou_arquivo.name.lower()
        if nome.endswith(".csv"):
            bruto = pd.read_csv(caminho_ou_arquivo, header=None)
        elif nome.endswith(".xls"):
            bruto = pd.read_excel(caminho_ou_arquivo, engine="xlrd", header=None)
        else:
            bruto = pd.read_excel(caminho_ou_arquivo, header=None)

    df = bruto.iloc[8:41].copy()

    df.columns = [
        "uf_regiao",
        "total",
        "total_branca",
        "total_preta_parda",
        "homem_branca",
        "homem_preta_parda",
        "mulher_branca",
        "mulher_preta_parda",
    ]
    df = df.reset_index(drop=True)

    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["homens_media"] = ((df["homem_branca"] + df["homem_preta_parda"]) / 2).round(2)
    df["mulheres_media"] = ((df["mulher_branca"] + df["mulher_preta_parda"]) / 2).round(2)
    df["diferenca_genero"] = (df["mulheres_media"] - df["homens_media"]).round(2)

    return df


@st.cache_data
def carregar_e_limpar_formacao(caminho_ou_arquivo):
    if isinstance(caminho_ou_arquivo, str):
        if caminho_ou_arquivo.lower().endswith(".csv"):
            bruto = pd.read_csv(caminho_ou_arquivo, header=None)
        else:
            bruto = pd.read_excel(caminho_ou_arquivo, header=None)
    else:
        nome = caminho_ou_arquivo.name.lower()
        if nome.endswith(".csv"):
            bruto = pd.read_csv(caminho_ou_arquivo, header=None)
        else:
            bruto = pd.read_excel(caminho_ou_arquivo, header=None)

    f_bruto = bruto.iloc[3:36].copy()

    f_total = f_bruto.iloc[:, 0:4].copy()
    f_total.columns = ["uf_regiao", "total", "homens", "mulheres"]

    f_stem = f_bruto.iloc[:, [0, 4, 5, 6]].copy()
    f_stem.columns = ["uf_regiao", "total", "homens", "mulheres"]

    f_saude = f_bruto.iloc[:, [0, 7, 8, 9]].copy()
    f_saude.columns = ["uf_regiao", "total", "homens", "mulheres"]

    for sub_df in [f_total, f_stem, f_saude]:
        for col in ["total", "homens", "mulheres"]:
            sub_df[col] = pd.to_numeric(sub_df[col], errors="coerce")
        sub_df["pct_mulheres"] = ((sub_df["mulheres"] / sub_df["total"]) * 100).round(2)

    df_consolidado = pd.DataFrame({
        "uf_regiao": f_total["uf_regiao"].values,
        "total_graduados": f_total["total"].values,
        "mulheres_total": f_total["mulheres"].values,
        "pct_mulheres_total": f_total["pct_mulheres"].values,
        "stem_total": f_stem["total"].values,
        "pct_mulheres_stem": f_stem["pct_mulheres"].values,
        "saude_total": f_saude["total"].values,
        "pct_mulheres_saude": f_saude["pct_mulheres"].values,
    })

    return df_consolidado


# ==============================================================================
# 3. BARRA LATERAL (SIDEBAR) - CARREGAMENTO DE DADOS E FILTROS
# ==============================================================================

st.sidebar.title("📌 Menu & Filtros")

st.sidebar.subheader("📂 Arquivos de Entrada (Pandas)")

file_afazeres = st.sidebar.file_uploader("Upload Tabela 1.1.1 (Afazeres):", type=["xls", "xlsx", "csv"])
file_formacao = st.sidebar.file_uploader("Upload Tabela 3 (Formação):", type=["xls", "xlsx", "csv"])

df_afazeres = None
df_formacao = None

try:
    if file_afazeres is not None:
        df_afazeres = carregar_e_limpar_afazeres(file_afazeres)
    elif os.path.exists(caminho_afazeres_padrao):
        df_afazeres = carregar_e_limpar_afazeres(caminho_afazeres_padrao)
except Exception as e:
    st.sidebar.error(f"Erro ao carregar Tabela 1.1.1: {e}")

try:
    if file_formacao is not None:
        df_formacao = carregar_e_limpar_formacao(file_formacao)
    elif os.path.exists(caminho_formacao_padrao):
        df_formacao = carregar_e_limpar_formacao(caminho_formacao_padrao)
except Exception as e:
    st.sidebar.error(f"Erro ao carregar Tabela de Formação: {e}")

if df_afazeres is None or df_formacao is None:
    st.warning("⚠️ **Aguardando leitura de dados pelo Pandas.**")
    st.info(f"""
    Não foi possível encontrar automaticamente os arquivos nos caminhos:
    - `{caminho_afazeres_padrao}`
    - `{caminho_formacao_padrao}`

    **Solução:** Utilize o campo de upload na barra lateral para carregar as tabelas.
    """)
    st.stop()

# ==============================================================================
# VARIÁVEIS GLOBAIS (DEFINIDAS PARA TODAS AS PÁGINAS)
# ==============================================================================
br_afazeres = df_afazeres[df_afazeres["uf_regiao"] == "Brasil"]
br_formacao = df_formacao[df_formacao["uf_regiao"] == "Brasil"]

media_br = br_afazeres["total"].values[0] if not br_afazeres.empty else 0
homem_br = br_afazeres["homens_media"].values[0] if not br_afazeres.empty else 0
mulher_br = br_afazeres["mulheres_media"].values[0] if not br_afazeres.empty else 0
stem_br = br_formacao["pct_mulheres_stem"].values[0] if not br_formacao.empty else 0

# Navegação
st.sidebar.markdown("---")
pagina = st.sidebar.radio(
    "Selecione a Visualização:",
    ["🏠 Visão Geral", "📊 Afazeres Domésticos", "🎓 Formação Acadêmica"]
)

REGIOES = ["Brasil", "Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"]

st.sidebar.markdown("---")
tipo_visao = st.sidebar.radio("Filtrar recorte:", ["Apenas Estados (27 UFs)", "Apenas Regiões e Brasil"])

if tipo_visao == "Apenas Estados (27 UFs)":
    df_af_fil = df_afazeres[~df_afazeres["uf_regiao"].isin(REGIOES)].copy()
    df_fo_fil = df_formacao[~df_formacao["uf_regiao"].isin(REGIOES)].copy()
else:
    df_af_fil = df_afazeres[df_afazeres["uf_regiao"].isin(REGIOES)].copy()
    df_fo_fil = df_formacao[df_formacao["uf_regiao"].isin(REGIOES)].copy()

locais_disp = df_af_fil["uf_regiao"].tolist()
locais_sel = st.sidebar.multiselect("Filtrar UFs / Regiões:", locais_disp, default=locais_disp)

if locais_sel:
    df_af_fil = df_af_fil[df_af_fil["uf_regiao"].isin(locais_sel)]
    df_fo_fil = df_fo_fil[df_fo_fil["uf_regiao"].isin(locais_sel)]


# ==============================================================================
# 4. PÁGINA: VISÃO GERAL
# ==============================================================================

if pagina == "🏠 Visão Geral":
    st.title("📊 Painel de Análise Social IBGE - Gênero e Raça")
    st.markdown("Dados lidos do diretório especificado e tratados via **Pandas**.")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Média Horas Casa (Brasil)", f"{media_br:.1f} h/sem")
    col2.metric("Média Homens", f"{homem_br:.1f} h/sem")
    col3.metric("Média Mulheres", f"{mulher_br:.1f} h/sem", delta=f"+{mulher_br - homem_br:.1f} h")
    col4.metric("% Mulheres em STEM", f"{stem_br:.1f}%")

    st.markdown("---")
    st.subheader("📋 Visualização das Tabelas Tratadas (Pandas)")
    tab1, tab2 = st.tabs(["Tabela 1.1.1 (Afazeres Domésticos)", "Tabela 3 (Formação Acadêmica)"])
    
    with tab1:
        st.dataframe(df_af_fil, use_container_width=True)
    with tab2:
        st.dataframe(df_fo_fil, use_container_width=True)


# ==============================================================================
# 5. PÁGINA: AFAZERES DOMÉSTICOS
# ==============================================================================

elif pagina == "📊 Afazeres Domésticos":
    st.title("🧹 Dedicação a Cuidados de Pessoas e Afazeres Domésticos")

    st.subheader("1. Horas Dedicadas por Localidade vs. Média Brasil")
    fig_tot = px.bar(
        df_af_fil.sort_values("total", ascending=True),
        x="total",
        y="uf_regiao",
        orientation="h",
        color="total",
        labels={"total": "Horas / Semana", "uf_regiao": "Localidade"},
        text_auto=".1f",
        color_continuous_scale="Blues"
    )
    if not br_afazeres.empty:
        fig_tot.add_vline(x=media_br, line_dash="dash", line_color="red", annotation_text=f"Média Brasil ({media_br:.1f}h)")
    st.plotly_chart(fig_tot, use_container_width=True)

    st.subheader("2. Comparativo Homens vs. Mulheres")
    df_melt_gen = df_af_fil.melt(
        id_vars=["uf_regiao"],
        value_vars=["homens_media", "mulheres_media"],
        var_name="Gênero",
        value_name="Horas"
    )
    df_melt_gen["Gênero"] = df_melt_gen["Gênero"].map({"homens_media": "Homens", "mulheres_media": "Mulheres"})

    fig_gen = px.bar(
        df_melt_gen,
        x="uf_regiao",
        y="Horas",
        color="Gênero",
        barmode="group",
        labels={"Horas": "Horas / Semana", "uf_regiao": "Localidade"},
        color_discrete_map={"Homens": "#2b5c8f", "Mulheres": "#d95f02"}
    )
    st.plotly_chart(fig_gen, use_container_width=True)

    st.subheader("3. Cruzamento por Sexo e Cor/Raça (Boxplot)")
    df_melt_raca = df_af_fil.melt(
        id_vars=["uf_regiao"],
        value_vars=["homem_branca", "homem_preta_parda", "mulher_branca", "mulher_preta_parda"],
        var_name="Grupo",
        value_name="Horas"
    )
    mapa_raca = {
        "homem_branca": "Homem Branco",
        "homem_preta_parda": "Homem Preto/Pardo",
        "mulher_branca": "Mulher Branca",
        "mulher_preta_parda": "Mulher Preta/Parda"
    }
    df_melt_raca["Grupo"] = df_melt_raca["Grupo"].map(mapa_raca)

    fig_box = px.box(
        df_melt_raca,
        x="Grupo",
        y="Horas",
        color="Grupo",
        points="all",
        title="Distribuição das Horas entre as Localidades Selecionadas"
    )
    st.plotly_chart(fig_box, use_container_width=True)


# ==============================================================================
# 6. PÁGINA: FORMAÇÃO ACADÊMICA
# ==============================================================================

elif pagina == "🎓 Formação Acadêmica":
    st.title("🎓 Proporção de Mulheres na Graduação Superior")

    st.subheader("1. % de Mulheres por Área (Total vs. STEM vs. Saúde/Educação)")
    df_melt_form = df_fo_fil.melt(
        id_vars=["uf_regiao"],
        value_vars=["pct_mulheres_total", "pct_mulheres_stem", "pct_mulheres_saude"],
        var_name="Área",
        value_name="Percentual"
    )
    mapa_area = {
        "pct_mulheres_total": "Graduação Total",
        "pct_mulheres_stem": "STEM (Exatas/Tecnologia)",
        "pct_mulheres_saude": "Saúde e Educação"
    }
    df_melt_form["Área"] = df_melt_form["Área"].map(mapa_area)

    fig_form = px.bar(
        df_melt_form,
        x="uf_regiao",
        y="Percentual",
        color="Área",
        barmode="group",
        labels={"Percentual": "% de Mulheres", "uf_regiao": "Localidade"}
    )
    fig_form.add_hline(y=50, line_dash="dash", line_color="gray", annotation_text="Paridade (50%)")
    st.plotly_chart(fig_form, use_container_width=True)

    st.subheader("2. Comparativo da Distribuição por Área (Boxplot)")
    fig_box_form = px.box(
        df_melt_form,
        x="Área",
        y="Percentual",
        color="Área",
        points="all"
    )
    fig_box_form.add_hline(y=50, line_dash="dash", line_color="gray")
    st.plotly_chart(fig_box_form, use_container_width=True)