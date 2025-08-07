import streamlit as st
import geopandas as gpd
import numpy as np
import folium
from folium.plugins import Fullscreen
from streamlit_folium import st_folium
import plotly.express as px
import os

st.set_page_config(layout="wide", page_title="Painel de Talhões de Eucalipto", page_icon="🌳")
st.markdown("""
    <h1 style='text-align: center; color: #2e7d32;'>
         Dashboard - Dados Florestais
    </h1>
    <h3 style='text-align: center; font-weight: normal;'>
        Análise de produtividade, idade e volume por talhão
    </h3>
""", unsafe_allow_html=True)


# Carregar dados
@st.cache_data
def carregar_dados():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    path_geojson = os.path.join(BASE_DIR, "dados", "talhoes.geojson")
    gdf = gpd.read_file(path_geojson)
    np.random.seed(42)
    gdf["idade"] = np.random.randint(1, 10, len(gdf))
    gdf["produtividade"] = np.random.uniform(15, 35, len(gdf))
    gdf["volume"] = gdf["idade"] * gdf["produtividade"] + np.random.normal(0, 10, len(gdf))
    gdf["especie"] = gdf["fazenda"].map({"Fazenda 1": "Eucalyptus urophylla", "Fazenda 2": "Eucalyptus grandis"})
    gdf["area"] = gdf.to_crs(epsg=5880).geometry.area / 10000
    np.random.seed(42)
    gdf["taxa_sobrevivencia"] = np.random.uniform(85, 95, len(gdf))  # em %
    gdf["rendimento_operacional"] = np.random.uniform(5, 10, len(gdf))  # ha/dia
    gdf["custo_por_talhao"] = 1200 + np.random.normal(0, 150, len(gdf)) - (gdf["produtividade"] * 10)
    return gdf


gdf = carregar_dados()

# Filtros (sidebar)
fazendas = gdf["fazenda"].unique()
fazenda_sel = st.sidebar.multiselect("Seleção de Fazenda", options=fazendas, default=list(fazendas))

colormap_labels = {
    "Produtividade": "produtividade",
    "Volume": "volume",
    "Taxa de Sobrevivência": "taxa_sobrevivencia",
    "Rendimento Operacional": "rendimento_operacional"
}
colormap_label = st.sidebar.selectbox("Colorir Mapa por", options=list(colormap_labels.keys()))
colormap = colormap_labels[colormap_label]

idade_min, idade_max = int(gdf["idade"].min()), int(gdf["idade"].max())
idade_sel = st.sidebar.slider("Idade (anos)", idade_min, idade_max, (idade_min, idade_max))

filtros = (
        gdf["fazenda"].isin(fazenda_sel) &
        gdf["idade"].between(*idade_sel)
)
gdf_filtrado = gdf[filtros]
gdf_filtrado2 = gdf_filtrado.to_crs(epsg=5880)

# Paleta de cores
cores_fazenda = {"Fazenda 1": "#FF8000", "Fazenda 2": "#0055FF"}


def get_color(value, min_val_1, max_val_1):
    norm = (value - min_val_1) / (max_val_1 - min_val_1)
    if norm < 0.5:
        r = int(255 * (1 - 2 * norm))
        g = int(255 * (2 * norm))
        b = 0
    else:
        norm2 = 2 * (norm - 0.5)
        r = 0
        g = int(255 * (1 - norm2))
        b = int(255 * norm2)
    return f'#{r:02x}{g:02x}{b:02x}'


# Abas
abas = st.tabs(["📌 Introdução", "🌳 Visão Geral", "🌍 Mapa", "🔍 Análise Estatística", "• Relatório", "📄 Tabela"])

# Introdução
with abas[0]:
    st.title("• Introdução ao Projeto")
    st.markdown("""
      Este painel interativo tem como objetivo demonstrar um modelo de análise automatizada de dados de talhões de eucalipto de duas fazendas fictícias, localizadas na cidade de Três Lagoas - MS, próximas à planta industrial de celulose da Eldorado Brasil, sendo: **Fazenda Pontal** e **Fazenda Eldorado**.
      Os dados foram gerados artificialmente e incluem informações sobre idade, produtividade, volume, taxa de sobrevivência, rendimento operacional e custo por talhão.
      Os paineis foram desenvolvidos utilizando a biblioteca **Streamlit** e inclui visualizações interativas com **Plotly** e **Folium**, desenvolvido em ambiente Python (3.12).
      Para facilitar a navegação, o painel foi dividido em abas temáticas: Visão Geral, Mapa (interativo), Análise Estatística e Tabela.
      Também para fins de facilidade de visualização, as fazendas foram chamadas de Fazenda 1 e Fazenda 2, sendo elas a Fazenda Pontal e a Fazenda Eldorado, respectivamente.

      Através deste dashboard, é possível:

      - Visualizar a distribuição espacial dos talhões;
      - Visualizar indicadores como idade, volume, produtividade, taxa de sobrevivência, rendimento operacional e custo por talhão;
      - Explorar estatísticas e comparações entre as fazendas e talhões;
      - Observar os dados em forma de tabela.

      Mapa de localização das fazendas: \n\n\n\n
    """)
    image_path = os.path.join("dados", "mapa-areas.png")
    st.image(image_path, caption="Fonte: Do autor", use_container_width=True)

# Visão Geral
with abas[1]:
    st.title("🌳 Visão Geral das Fazendas")
    st.subheader("📊 Indicadores Operacionais")

    col1, col2, col3 = st.columns(3)
    col1.metric("Área Total", f"{(gdf_filtrado2.area.sum() / 10000):.2f} ha")
    col2.metric("Volume Médio", f"{gdf_filtrado['volume'].mean():.1f} m³")
    col3.metric("Produtividade Média", f"{gdf_filtrado['produtividade'].mean():.1f} m³/ha/ano")

    col4, col5, col6 = st.columns(3)
    col4.metric("Taxa de Sobrevivência Média", f"{gdf_filtrado['taxa_sobrevivencia'].mean():.1f} %")
    col5.metric("Rendimento Operacional Médio", f"{gdf_filtrado['rendimento_operacional'].mean():.1f} ha/dia")
    col6.metric("Custo Médio por Talhão", f"R$ {gdf_filtrado['custo_por_talhao'].mean():,.0f}")

    # Dados para gráficos
    # Soma da área por fazenda (usar dados filtrados)
    area_talhoes = gdf_filtrado.groupby("fazenda", as_index=False)["area"].sum()
    # Quantidade de talhões por fazenda (usando dados filtrados)
    contagem_talhoes = gdf_filtrado["fazenda"].value_counts().reset_index()
    contagem_talhoes.columns = ["fazenda", "quantidade"]

    # Gráfico pizza por área
    fig_pizza = px.pie(
        area_talhoes,
        values="area",
        names="fazenda",
        title="Distribuição da Área por Fazenda",
        labels={"area": "Área (ha)", "fazenda": "Fazenda"},
        color_discrete_map=cores_fazenda
    )
    st.plotly_chart(fig_pizza, use_container_width=True, key="pizza_area")

    # Gráfico barras por quantidade de talhões
    min_val = contagem_talhoes["quantidade"].min()
    max_val = contagem_talhoes["quantidade"].max()
    limite_inferior = max(min_val - 1, 0)  # um buffer pequeno, não negativo
    limite_superior = max_val + 1  # um buffer pequeno

    fig_barras = px.bar(
        contagem_talhoes,
        x="fazenda",
        y="quantidade",
        title="Quantidade Total de Talhões por Fazenda",
        color="fazenda",
        labels={"quantidade": "Quantidade de Talhões", "fazenda": "Fazenda"},
        color_discrete_map=cores_fazenda
    )
    fig_barras.update_yaxes(range=[14, 20])
    st.plotly_chart(fig_barras, use_container_width=True, key="barras_quantidade")



    # Histograma de Idade
    fig_hist_idade = px.histogram(
        gdf_filtrado,
        x="idade",
        nbins=8,
        title="Distribuição da Idade dos Talhões",
        labels={"idade": "Idade"}
    )
    st.plotly_chart(fig_hist_idade, use_container_width=True)

    # Boxplot de Produtividade
    fig_box_prod = px.box(
        gdf_filtrado,
        x="fazenda",
        y="produtividade",
        color="fazenda",
        title="Produtividade por Fazenda (m³/ha/ano)",
        labels={"fazenda": "Fazenda", "produtividade": "Produtividade"}
    )
    st.plotly_chart(fig_box_prod, use_container_width=True)

# Mapa
with abas[2]:
    st.title(f"🌍 Mapa Interativo dos Talhões")
    zoomstart = 14 if gdf_filtrado['fazenda'].nunique() == 1 else 13

    m = folium.Map(location=[gdf_filtrado.centroid.y.mean(), gdf_filtrado.centroid.x.mean()], zoom_start=zoomstart,
                   tiles="OpenStreetMap")
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri", name="Esri Satélite", overlay=False, control=True
    ).add_to(m)

    legend_html = """
    <div style="position: fixed; bottom: 50px; left: 50px; width: 180px; background-color: white; border:2px solid grey; z-index:9999; font-size:14px; padding: 10px">
    <b>Legenda:</b><br>
    <i style="background:#0000ff;width:18px;height:10px;display:inline-block;"></i> Valor máximo<br>
    <i style="background:#ff0000;width:18px;height:10px;display:inline-block;"></i> Valor mínimo<br>
    <i style="border:2px solid #FF8000;width:18px;height:10px;display:inline-block;"></i> Fazenda Pontal<br>
    <i style="border:2px solid #0055FF;width:18px;height:10px;display:inline-block;"></i> Fazenda Eldorado<br>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))
    Fullscreen().add_to(m)

    min_val, max_val = gdf_filtrado[colormap].min(), gdf_filtrado[colormap].max()

    for _, row in gdf_filtrado.iterrows():
        fill = get_color(row[colormap], min_val, max_val)
        border = cores_fazenda.get(row["fazenda"], "black")
        tooltip_text = f"""
        <h4 style='text-align:center;font-weight:bold;'>{row['Talhao']}</h4>
        <b>Fazenda:</b> {row['fazenda']}<br>
        <b>Área:</b> {row['area']:.2f} ha<br>
        <b>Espécie:</b> {row['especie']}<br>
        <b>Idade:</b> {row['idade']} anos<br>
        <b>Produtividade:</b> {row['produtividade']:.1f} m³/ha/ano<br>
        <b>Volume Total:</b> {row['volume']:.1f} m³
        """
        folium.GeoJson(
            row["geometry"],
            tooltip=tooltip_text,
            style_function=lambda feature, fill=fill, border=border: {
                'fillColor': fill,
                'color': border,
                'weight': 1.5,
                'fillOpacity': 0.7,
            },
        ).add_to(m)

    st_folium(m, width=1200, height=600)

# Análise Estatística
with abas[3]:
    st.title("• Análise Estatística Detalhada")

    sub_aba = st.radio("Selecione a visualização:",
                       options=["Distribuição", "Comparação por Fazenda", "Indicadores por Talhão"],
                       horizontal=True)

    if sub_aba == "Distribuição":
        fig1 = px.histogram(gdf_filtrado, x="taxa_sobrevivencia", nbins=15,
                            title="Distribuição da Taxa de Sobrevivência (%)")
        st.plotly_chart(fig1, use_container_width=True)

        fig2 = px.histogram(gdf_filtrado, x="rendimento_operacional", nbins=15,
                            title="Distribuição do Rendimento Operacional (ha/dia)")
        st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.histogram(gdf_filtrado, x="custo_por_talhao", nbins=15, title="Distribuição do Custo por Talhão (R$)")
        st.plotly_chart(fig3, use_container_width=True)

    elif sub_aba == "Comparação por Fazenda":
        st.markdown("---")
        st.subheader("🏷️ Comparações por Fazenda")

        fig4 = px.box(gdf_filtrado, x="fazenda", y="taxa_sobrevivencia", title="Taxa de Sobrevivência por Fazenda")
        st.plotly_chart(fig4, use_container_width=True)

        fig5 = px.box(gdf_filtrado, x="fazenda", y="rendimento_operacional", title="Rendimento Operacional por Fazenda")
        st.plotly_chart(fig5, use_container_width=True)

        fig6 = px.box(gdf_filtrado, x="fazenda", y="custo_por_talhao", title="Custo por Talhão por Fazenda")
        st.plotly_chart(fig6, use_container_width=True)

    elif sub_aba == "Indicadores por Talhão":
        st.subheader("Gráficos por Talhão")
        resumo = gdf_filtrado.groupby(["fazenda", "Talhao"]).agg({
            "idade": "mean",
            "produtividade": "mean",
            "volume": "mean",
            "taxa_sobrevivencia": "mean",
            "rendimento_operacional": "mean",
            "custo_por_talhao": "mean",
        }).reset_index()
        resumo["label"] = resumo["fazenda"] + " - " + resumo["Talhao"]
        indicadores = {
            "idade": "Idade",
            "produtividade": "Produtividade (m³/ha/ano)",
            "volume": "Volume (m³)",
            "taxa_sobrevivencia": "Taxa de Sobrevivência(%)",
            "rendimento_operacional": "Rendimento Operacional (ha/dia)",
            "custo_por_talhao": "Custo por Talhão (R$)"
        }
        for col, label in indicadores.items():
            fig = px.bar(
                resumo.sort_values(col),
                x="label",
                y=col,
                title=label,
                labels={"label": "Fazenda - Talhão", col: label},
            )
            fig.update_layout(xaxis_tickangle=45)
            st.plotly_chart(fig, use_container_width=True)

with abas[4]:
    st.title(" Relatório dos Melhores Talhões por Indicador")

    indicadores = {
        "taxa_sobrevivencia": {"label": "Taxa de Sobrevivência (%)", "asc": False},
        "produtividade": {"label": "Produtividade (m³/ha/ano)", "asc": False},
        "rendimento_operacional": {"label": "Rendimento Operacional (ha/dia)", "asc": False},
        "custo_por_talhao": {"label": "Custo por Talhão (R$)", "asc": True},
    }

    for col, props in indicadores.items():
        st.subheader(f"Top 5 Talhões por {props['label']}")
        melhores = (
            gdf_filtrado[["fazenda", "Talhao", col]]
            .sort_values(col, ascending=props["asc"])
            .head(5)
            .reset_index(drop=True)
        )
        melhores.index += 1
        st.table(melhores)
with abas[5]:
    st.title("📄 Tabela de Talhões")
    st.dataframe(gdf_filtrado.drop(columns="geometry"))
