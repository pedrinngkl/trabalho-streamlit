import os

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="IDHM Brasil",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


PATH = "Tabela4.csv"

REGIOES = {
    "Norte": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
}
SIGLA_REGIAO = {uf: reg for reg, ufs in REGIOES.items() for uf in ufs}


# ==============================================================================
# 2. CARREGAMENTO E LIMPEZA (PANDAS)
# ==============================================================================
def _ler_bruto(origem):
    """Lê CSV (utf-8 ou latin-1) ou Excel, sem cabeçalho."""
    nome = origem if isinstance(origem, str) else origem.name
    nome = nome.lower()

    if nome.endswith(".csv"):
        for enc in ("utf-8", "latin-1"):
            try:
                if not isinstance(origem, str):
                    origem.seek(0)
                return pd.read_csv(origem, header=None, encoding=enc, sep=None, engine="python")
            except UnicodeDecodeError:
                continue
        raise ValueError("Não foi possível ler o CSV (encoding).")

    if not isinstance(origem, str):
        origem.seek(0)
    if nome.endswith(".xls"):
        return pd.read_excel(origem, header=None, engine="xlrd")
    return pd.read_excel(origem, header=None)


@st.cache_data
def carregar_idhm(origem):
    bruto = _ler_bruto(origem)

    # Localiza a linha de cabeçalho (a que começa com "Sigla")
    primeira_col = bruto.iloc[:, 0].astype(str).str.strip()
    idx_cab = primeira_col[primeira_col == "Sigla"].index[0]

    df = bruto.iloc[idx_cab + 1:].copy()
    df.columns = [str(c).strip() for c in bruto.iloc[idx_cab]]
    df = df.dropna(subset=["Sigla"]).reset_index(drop=True)

    df = df.rename(columns={"Sigla": "sigla", "Código": "codigo", "Estado": "estado"})
    anos = [c for c in df.columns if c.isdigit()]

    for col in anos:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce")

    df["regiao"] = df["sigla"].map(SIGLA_REGIAO)
    return df, anos


def classificar(valor):
    """Faixas oficiais do IDHM (PNUD)."""
    if pd.isna(valor):
        return "Sem dado"
    if valor >= 0.800:
        return "Muito alto"
    if valor >= 0.700:
        return "Alto"
    if valor >= 0.600:
        return "Médio"
    if valor >= 0.500:
        return "Baixo"
    return "Muito baixo"


# ==============================================================================
# 3. BARRA LATERAL: UPLOAD, NAVEGAÇÃO E FILTROS
# ==============================================================================
st.sidebar.title("📌 Menu & Filtros")

st.sidebar.subheader("📂 Arquivo de entrada")
arquivo = st.sidebar.file_uploader("Upload da Tabela 4 (IDHM):", type=["csv", "xls", "xlsx"])

df, anos = None, None
try:
    if arquivo is not None:
        df, anos = carregar_idhm(arquivo)
    elif os.path.exists(PATH):
        df, anos = carregar_idhm(PATH)
except Exception as e:
    st.sidebar.error(f"Erro ao carregar a tabela: {e}")

if df is None:
    st.warning("⚠️ **Aguardando leitura dos dados.**")
    st.info(f"Arquivo `{PATH}` não encontrado. Use o campo de upload na barra lateral.")
    st.stop()

st.sidebar.markdown("---")
pagina = st.sidebar.radio(
    "Selecione a Visualização:",
    ["🏠 Visão Geral", "📈 Evolução Temporal", "📊 Ranking e Dispersão", "📰 Notícias e Projetos"],
)

st.sidebar.markdown("---")
st.sidebar.subheader("🎯 Filtros")

regioes_sel = st.sidebar.multiselect("Região:", list(REGIOES.keys()), default=list(REGIOES.keys()))
ufs_regiao = df[df["regiao"].isin(regioes_sel)]["sigla"].tolist()
ufs_sel = st.sidebar.multiselect("UF:", ufs_regiao, default=ufs_regiao)

ano_ini, ano_fim = st.sidebar.select_slider(
    "Período:", options=anos, value=(anos[0], anos[-1])
)
anos_periodo = [a for a in anos if int(ano_ini) <= int(a) <= int(ano_fim)]

df_fil = df[df["sigla"].isin(ufs_sel)].copy()

if df_fil.empty:
    st.warning("Selecione ao menos uma UF na barra lateral.")
    st.stop()

# Série longa (tidy) para os gráficos de linha / boxplot
df_long = df_fil.melt(
    id_vars=["sigla", "estado", "regiao"],
    value_vars=anos_periodo,
    var_name="ano",
    value_name="idhm",
)
df_long["ano"] = df_long["ano"].astype(int)

media_ufs_por_ano = df_long.groupby("ano")["idhm"].mean().reset_index()


# ==============================================================================
# 4. PÁGINA: VISÃO GERAL
# ==============================================================================
if pagina == "🏠 Visão Geral":
    st.title("📊 Painel IDHM — Consórcio de Governadores")
    st.markdown(
        "Análise do **Índice de Desenvolvimento Humano Municipal (IDHM)** por Unidade da Federação, "
        "para apoiar a criação de um fundo regional de redução de desigualdades."
    )

    col_ref = ano_fim
    serie = df_fil.set_index("sigla")[col_ref].dropna()

    maior_uf, menor_uf = serie.idxmax(), serie.idxmin()
    media = serie.mean()
    desvio = serie.std()
    iqr = serie.quantile(0.75) - serie.quantile(0.25)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(f"Média das UFs ({col_ref})", f"{media:.3f}")
    c2.metric("Maior IDHM", f"{maior_uf} • {serie.max():.3f}")
    c3.metric("Menor IDHM", f"{menor_uf} • {serie.min():.3f}")
    c4.metric("Desvio-padrão", f"{desvio:.3f}")
    c5.metric("IQR", f"{iqr:.3f}")

    # Comparativo com o início do período
    base = df_fil[ano_ini].mean()
    st.caption(
        f"Média das UFs selecionadas em {ano_ini}: **{base:.3f}** → em {ano_fim}: **{media:.3f}** "
        f"({media - base:+.3f})."
    )

    st.markdown("---")
    st.subheader(f"Distribuição das UFs por faixa de desenvolvimento ({col_ref})")
    df_faixa = df_fil[["sigla", "estado", "regiao", col_ref]].copy()
    df_faixa["faixa"] = df_faixa[col_ref].apply(classificar)
    ordem = ["Muito baixo", "Baixo", "Médio", "Alto", "Muito alto"]
    contagem = (
        df_faixa["faixa"].value_counts().reindex(ordem).fillna(0).astype(int).reset_index()
    )
    contagem.columns = ["faixa", "ufs"]
    fig_faixa = px.bar(
        contagem, x="faixa", y="ufs", text="ufs",
        labels={"faixa": "Faixa do IDHM", "ufs": "Nº de UFs"},
        color="faixa",
        color_discrete_sequence=px.colors.sequential.Viridis,
    )
    fig_faixa.update_layout(showlegend=False)
    st.plotly_chart(fig_faixa, use_container_width=True)

    st.subheader("📋 Tabela tratada (Pandas)")
    st.dataframe(df_fil[["sigla", "estado", "regiao"] + anos_periodo], use_container_width=True)


# ==============================================================================
# 5. PÁGINA: EVOLUÇÃO TEMPORAL
# ==============================================================================
elif pagina == "📈 Evolução Temporal":
    st.title("📈 Evolução do IDHM")

    st.subheader("1. IDHM por UF ao longo do tempo")
    fig_lin = px.line(
        df_long.sort_values("ano"),
        x="ano", y="idhm", color="sigla", markers=True,
        hover_name="estado",
        labels={"ano": "Ano", "idhm": "IDHM", "sigla": "UF"},
    )
    fig_lin.update_xaxes(type="category")
    st.plotly_chart(fig_lin, use_container_width=True)

    st.subheader("2. Média das UFs selecionadas")
    fig_media = px.line(
        media_ufs_por_ano, x="ano", y="idhm", markers=True,
        labels={"ano": "Ano", "idhm": "IDHM médio"},
    )
    fig_media.update_xaxes(type="category")
    st.plotly_chart(fig_media, use_container_width=True)

    st.subheader("3. Variação do IDHM no período")
    var = df_fil[["sigla", "estado", ano_ini, ano_fim]].copy()
    var["variacao"] = (var[ano_fim] - var[ano_ini]).round(3)
    var = var.sort_values("variacao", ascending=True)
    fig_var = px.bar(
        var, x="variacao", y="sigla", orientation="h", text="variacao",
        hover_name="estado", color="variacao", color_continuous_scale="Blues",
        labels={"variacao": f"Variação {ano_ini} → {ano_fim}", "sigla": "UF"},
    )
    st.plotly_chart(fig_var, use_container_width=True)

    maior_cresc = var.iloc[-1]
    menor_cresc = var.iloc[0]
    st.info(
        f"Maior ganho: **{maior_cresc['estado']}** ({maior_cresc['variacao']:+.3f}). "
        f"Menor ganho: **{menor_cresc['estado']}** ({menor_cresc['variacao']:+.3f})."
    )


# ==============================================================================
# 6. PÁGINA: RANKING E DISPERSÃO
# ==============================================================================
elif pagina == "📊 Ranking e Dispersão":
    st.title("📊 Ranking e Dispersão entre UFs")

    ano_rank = st.selectbox("Ano de referência:", anos_periodo, index=len(anos_periodo) - 1)

    st.subheader(f"1. Ranking do IDHM em {ano_rank}")
    rank = df_fil[["sigla", "estado", "regiao", ano_rank]].dropna().sort_values(ano_rank)
    fig_rank = px.bar(
        rank, x=ano_rank, y="sigla", orientation="h", color="regiao", text=ano_rank,
        hover_name="estado", labels={ano_rank: "IDHM", "sigla": "UF", "regiao": "Região"},
    )
    st.plotly_chart(fig_rank, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**🔻 5 menores IDHM**")
        st.dataframe(rank.head(5)[["estado", ano_rank]].rename(columns={ano_rank: "IDHM"}),
                     hide_index=True, use_container_width=True)
    with col_b:
        st.markdown("**🔺 5 maiores IDHM**")
        st.dataframe(rank.tail(5).iloc[::-1][["estado", ano_rank]].rename(columns={ano_rank: "IDHM"}),
                     hide_index=True, use_container_width=True)

    st.subheader("2. Boxplot do IDHM por região")
    df_box = df_long[df_long["ano"] == int(ano_rank)]
    fig_box = px.box(
        df_box, x="regiao", y="idhm", color="regiao", points="all",
        hover_name="estado", labels={"regiao": "Região", "idhm": "IDHM"},
    )
    st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("3. Dispersão entre UFs ao longo do tempo (desvio-padrão e IQR)")
    disp = df_long.groupby("ano")["idhm"].agg(
        desvio_padrao="std",
        iqr=lambda s: s.quantile(0.75) - s.quantile(0.25),
    ).reset_index()
    disp_long = disp.melt(id_vars="ano", var_name="medida", value_name="valor")
    disp_long["medida"] = disp_long["medida"].map({"desvio_padrao": "Desvio-padrão", "iqr": "IQR"})
    fig_disp = px.line(disp_long, x="ano", y="valor", color="medida", markers=True,
                       labels={"ano": "Ano", "valor": "Dispersão", "medida": "Medida"})
    fig_disp.update_xaxes(type="category")
    st.plotly_chart(fig_disp, use_container_width=True)
    st.caption("Quanto menor a dispersão, mais próximas estão as UFs: sinal de redução de desigualdade regional.")


# ==============================================================================
# 7. PÁGINA: NOTÍCIAS E PROJETOS
# ==============================================================================
elif pagina == "📰 Notícias e Projetos":
    st.title("📰 Superação da extrema pobreza e índices sociais")
    st.markdown(
        "Seleção de fontes para acompanhar projetos de superação da extrema pobreza no Brasil. "
        "Os links abrem buscas atualizadas nas fontes oficiais e na imprensa."
    )

    # Para usar imagens próprias, coloque os arquivos na pasta "imagens" (ex.: imagens/idh1.jpg)
    # e preencha o campo "imagem" abaixo.
    noticias = [
        {
            "titulo": "Atlas do Desenvolvimento Humano no Brasil",
            "resumo": "Base oficial do PNUD, Ipea e FJP com o IDHM de estados e municípios.",
            "link": "https://www.atlasbrasil.org.br/",
            "imagem": "imagens/atlas.jpg",
        },
        {
            "titulo": "Projetos de superação da extrema pobreza (notícias)",
            "resumo": "Reportagens recentes sobre programas de transferência de renda e inclusão produtiva.",
            "link": "https://news.google.com/search?q=supera%C3%A7%C3%A3o%20da%20extrema%20pobreza%20Brasil",
            "imagem": "imagens/pobreza.jpg",
        },
        {
            "titulo": "Relatório de Desenvolvimento Humano (PNUD)",
            "resumo": "Publicação global do PNUD que acompanha o IDH dos países.",
            "link": "https://www.undp.org/pt/brazil",
            "imagem": "imagens/pnud.jpg",
        },
        {
            "titulo": "Desigualdade regional no Brasil (notícias)",
            "resumo": "Cobertura sobre diferenças de renda, saúde e educação entre as regiões.",
            "link": "https://news.google.com/search?q=desigualdade%20regional%20IDH%20Brasil",
            "imagem": "imagens/desigualdade.jpg",
        },
    ]

    cols = st.columns(2)
    for i, n in enumerate(noticias):
        with cols[i % 2]:
            with st.container(border=True):
                if os.path.exists(n["imagem"]):
                    st.image(n["imagem"], use_container_width=True)
                st.markdown(f"### {n['titulo']}")
                st.write(n["resumo"])
                st.link_button("Acessar", n["link"])
