import streamlit as st
import geopandas as gpd
import pandas as pd
import folium
from folium import Choropleth, GeoJson
from folium.plugins import Fullscreen
from streamlit_folium import st_folium
import numpy as np

st.set_page_config(layout="wide", page_title="Painel de Talhões de Eucalipto", page_icon="🌳")

# Carregar GeoJSON
gdf = gpd.read_file("dados/talhoes.geojson")
gdf2 = gdf.to_crs(epsg=32626)  # Converter para WGS84


# Simular dados
fazendas = gdf["fazenda"].unique()
especies = {"Fazenda 1": "Eucalyptus urophylla", "Fazenda 2": "Eucalyptus grandis"}

np.random.seed(42)
gdf["idade"] = np.random.randint(1, 10, len(gdf))
gdf["produtividade"] = np.random.uniform(12, 35, len(gdf))
gdf["volume"] = gdf["idade"] * gdf["produtividade"] + np.random.normal(0, 10, len(gdf))
gdf["especie"] = gdf["fazenda"].map(especies)
gdf["area"] = gdf.to_crs(epsg=5880).geometry.area / 10000  # Área em hectares

# Sidebar - filtros
st.sidebar.title("Filtros")
fazenda_sel = st.sidebar.multiselect("Fazenda", options=fazendas, default=list(fazendas))
idade_min, idade_max = int(gdf["idade"].min()), int(gdf["idade"].max())
idade_sel = st.sidebar.slider("Idade (anos)", idade_min, idade_max, (idade_min, idade_max))
#especies_sel = st.sidebar.multiselect("Espécie", options=gdf["especie"].unique(), default=list(gdf["especie"].unique()))
colormap = st.sidebar.selectbox("Colorir por", options=["produtividade", "volume"])

# Filtrar dados
filtros = (
    gdf["fazenda"].isin(fazenda_sel) &
    gdf["idade"].between(*idade_sel)
)

gdf_filtrado = gdf[filtros]
gdf_filtrado2 = gdf_filtrado.to_crs(epsg=5880)


m = folium.Map(location=[gdf.centroid.y.mean(), gdf.centroid.x.mean()], zoom_start=13, tiles="OpenStreetMap")
folium.TileLayer(
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    attr="Esri",
    name="Esri Satélite",
    overlay=False,
    control=True
).add_to(m)

legend_html = """
<div style="
    position: fixed;
    bottom: 50px;
    left: 50px;
    width: 140;
    height: 120px;
    background-color: white;
    border:2px solid grey;
    z-index:9999;
    font-size:14px;
    padding: 15px;
">
    <b>Legenda:</b><br>
    <i style="background:#0000ff;width:18px;height:10px;display:inline-block;"></i> Valor máximo<br>
    <i style="background:#00ff00;width:18px;height:10px;display:inline-block;"></i> Valor médio<br>
    <i style="background:#ff0000;width:18px;height:10px;display:inline-block;"></i> Valor mínimo
    
    
</div>
"""

m.get_root().html.add_child(folium.Element(legend_html))


Fullscreen().add_to(m)

# Coloração
min_val = gdf_filtrado[colormap].min()
max_val = gdf_filtrado[colormap].max()


def get_color(value, min_val_1, max_val_1):
    norm = (value - min_val_1) / (max_val_1 - min_val_1)

    if norm < 0.5:
        # Interpola de vermelho (255,0,0) → verde (0,255,0)
        r = int(255 * (1 - 2 * norm))
        g = int(255 * (2 * norm))
        b = 0
    else:
        # Interpola de verde (0,255,0) → azul (0,0,255)
        norm2 = 2 * (norm - 0.5)
        r = 0
        g = int(255 * (1 - norm2))
        b = int(255 * norm2)

    return f'#{r:02x}{g:02x}{b:02x}'

cores_fazenda = {
    "Fazenda 1": "#FF8000",  # laranja
    "Fazenda 2": "#0055FF",  # azul
}

for _, row in gdf_filtrado.iterrows():
    cor_preenchimento = get_color(row[colormap], min_val, max_val)
    cor_borda = cores_fazenda.get(row["fazenda"], "black")  # preto como fallback
    tooltip_text = f"""
    <h4 style="text-align:center; font-weight:bold;">{row['Talhao']}</h4>
    <b>Fazenda:</b> {row['fazenda']}<br>
    <b>Área:</b> {row['area']:.2f} ha<br>
    <b>Espécie:</b> {row['especie']}<br>
    <b>Idade:</b> {row['idade']} anos<br>
    <b>Produtividade:</b> {row['produtividade']:.1f} m³/ha/ano<br>
    <b>Volume Total:</b> {row['volume']:.1f} m³
    """
    geojson = folium.GeoJson(
        row["geometry"],
        tooltip=tooltip_text,
        style_function=lambda feature, fill=cor_preenchimento, border=cor_borda: {
            'fillColor': fill,
            'color': border,
            'weight': 1.5,
            'fillOpacity': 0.7,
        },
    )
    geojson.add_to(m)

# Métricas
st.title("Painel de Talhões de Eucalipto")
col1, col2, col3 = st.columns(3)
col1.metric("Área Total (ha)", f"{(gdf_filtrado2.area.sum()/10000):.2f} ha")
col2.metric("Volume Médio", f"{gdf_filtrado['volume'].mean():.1f} m³")
col3.metric("Produtividade Média", f"{gdf_filtrado['produtividade'].mean():.1f} m³/ha/ano")

# Mostrar mapa
st.subheader("Mapa Interativo")
col1, col2 = st.columns([5, 1])  # Map on the left, info on the right

with col1:
    st_folium(m, width=1200, height=600)  # Adjust width manually to fit container
