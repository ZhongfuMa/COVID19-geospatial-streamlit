import datetime
import os
import pathlib
import requests
import zipfile
import pickle
import pandas as pd
import pydeck as pdk
import geopandas as gpd
import streamlit as st
import leafmap.colormaps as cm
from leafmap.common import hex_to_rgb


STREAMLIT_STATIC_PATH = pathlib.Path(st.__path__[0]) / "static"
# We create a downloads directory within the streamlit static asset directory
# and we write output files to it
DOWNLOADS_PATH = STREAMLIT_STATIC_PATH / "downloads"
if not DOWNLOADS_PATH.is_dir():
    DOWNLOADS_PATH.mkdir()

# Data source: https://www.realtor.com/research/data/


@st.cache
def get_inventory_data(url,month,ch,sp_attribute,scale):
    df = open(url,'rb')
    data=pickle.load(df)

    if scale=='state':
        temp={}
        for state, char in data[month].items():
            temp.setdefault('STUSPS',[]).append(state)
            if sp_attribute in char[ch].keys():
                temp.setdefault(sp_attribute,[]).append(char[ch][sp_attribute])
            else:
                temp.setdefault(sp_attribute,[]).append(0)
            df=pd.DataFrame(temp)
    else:
        temp={}
        for state, char in data[month].items():
            temp.setdefault('NAME',[]).append(state.title())
            if sp_attribute in char[ch].keys():
                temp.setdefault(sp_attribute,[]).append(char[ch][sp_attribute])
            else:
                temp.setdefault(sp_attribute,[]).append(0)
            df=pd.DataFrame(temp)
    return df


@st.cache
def get_geom_data(category):

    prefix =os.getcwd()+'/data/'
    
    links = {
        "state": prefix + "us_states.geojson",
        "county": prefix + "us_counties.geojson"
    }

    gdf = gpd.read_file(links[category])
    return gdf


def join_attributes(gdf, df, category):

    new_gdf = None
    if category == "county":
        new_gdf = gdf.merge(df, left_on="NAME", right_on="NAME", how="outer")
        
    elif category == "state":
        new_gdf = gdf.merge(df, left_on="STUSPS", right_on="STUSPS", how="outer")
    new_gdf.set_geometry('geometry')
    new_gdf.crs=gdf.crs
    new_gdf=new_gdf.drop(axis=0,index=new_gdf[new_gdf.geometry.isna()].index)
    return new_gdf


def select_non_null(gdf, col_name):
    new_gdf=gdf.loc[gdf[col_name]!=0]
    new_gdf=new_gdf.loc[~gdf_new[col_name].isna()]
    return new_gdf


def select_null(gdf, col_name):
    new_gdf=gdf.loc[gdf[col_name]==0 | gdf[col_name].isna()]
    return new_gdf

def app():

    st.title("U.S. COVID-19 Surveillance Data")
    st.markdown(
        """**Introduction:** This interactive dashboard is designed for visualizing U.S. COVID-19 surveillance data at multiple levels (i.e.
         state and county). The data sources include [COVID-19 Case Surveillance Public Use Data with Geography](https://data.cdc.gov/Case-Surveillance/COVID-19-Case-Surveillance-Public-Use-Data-with-Ge/n8mc-b4w4) from data.cdc.gov and 
         [Cartographic Boundary Files](https://www.census.gov/geographies/mapping-files/time-series/geo/carto-boundary-file.html) from U.S. Census Bureau.
         Several open-source packages are used to process the data and generate the visualizations, e.g., [streamlit](https://streamlit.io),
          [geopandas](https://geopandas.org), [leafmap](https://leafmap.org), and [pydeck](https://deckgl.readthedocs.io). This project is developed based on [streamlit-geospatial](https://github.com/giswqs/streamlit-geospatial).
    """
    )

#     with st.expander("See a demo"):
#         st.image("https://i.imgur.com/Z3dk6Tr.gif")

#      
    row1_col1, row1_col2, row1_col3, row1_col4 = st.columns([0.6, 0.6, 1.0, 0.6])
    with row1_col1:
        scale = st.selectbox("Scale", ["State", "County"])
    with row1_col2:
        types = ["Age_group", "Sex", "Race", "Ethnicity"]
        characteristic = st.selectbox("Patient Characteristics",types)
    with row1_col3:
        if characteristic=='Age_group':
            data_cols=['0 - 17 years','18 to 49 years','50 to 64 years','65+ years','Unknown','Missing']
        elif characteristic=='Sex':
            data_cols=['Female','Male','Other','Unknown','Missing','NA']
        elif characteristic=='Race':
            data_cols=['American Indian/Alaska Native','Asian', 'Black','Multiple/Other',
                       'Native Hawaiian/Other Pacific Islander', 'White','Unknown','Missing','NA']
        elif characteristic=='Ethnicity':
            data_cols=['Hispanic','Non-Hispanic','Unknown','Missing','NA']
        sp_attribute = st.selectbox("Specific Attribute", data_cols)
    with row1_col4:
         model = st.selectbox("Spatial Model", ["Base", "Uniform", "de Movire"])
    
        
    with st.expander("Select year and month", True):
        selected_year = st.slider("Year",2020,2021)
        if selected_year==2021:
            min_value=1
            max_value=10
        else:
            min_value=1
            max_value=12
        selected_month = st.slider("Month",min_value,max_value,step=1)
    if selected_month<10:
        month=str(selected_year)+'-0'+str(selected_month)
    else:
        month=str(selected_year)+'-'+str(selected_month)
    gdf = get_geom_data(scale.lower())
    url_state=os.getcwd()+'/data/COVID19_bystate.pickle'
    
    if scale == "State":
        inventory_df = get_inventory_data(url_state,month,characteristic.lower(),sp_attribute,scale.lower())
        
        
    url_county=os.getcwd()+'/data/COVID19_bycounty.pickle'

    if scale == "County":
        inventory_df = get_inventory_data(url_county,month,characteristic.lower(),sp_attribute,scale.lower())


    row2_col1, row2_col2, row2_col3 = st.columns(
        [0.6, 0.68, 0.7]
    )#row2_col4, row2_col5, row2_col6 , 0.7, 1.5, 0.8

    with row2_col1:
        palette = st.selectbox("Color palette", cm.list_colormaps(), index=2)
    with row2_col2:
        n_colors = st.slider("Number of colors", min_value=2, max_value=20, value=8)
    with row2_col3:
        show_nodata = st.checkbox("Show nodata areas", value=True)
#     with row2_col4:
#         show_3d = st.checkbox("Show 3D view", value=False)
#     with row2_col5:
#         if show_3d:
#             elev_scale = st.slider(
#                 "Elevation scale", min_value=1, max_value=1000000, value=1, step=10
#             )
#             with row2_col6:
#                 st.info("Press Ctrl and move the left mouse button.")
#         else:
#             elev_scale = 1

    gdf = join_attributes(gdf, inventory_df, scale.lower())
    gdf_null = select_null(gdf, sp_attribute)
    gdf = select_non_null(gdf, sp_attribute)
    gdf = gdf.sort_values(by=sp_attribute, ascending=True)

    colors = cm.get_palette(palette, n_colors)
    colors = [hex_to_rgb(c) for c in colors]

    for i, ind in enumerate(gdf.index):
        index = int(i / (len(gdf) / len(colors)))
        if index >= len(colors):
            index = len(colors) - 1
        gdf.loc[ind, "R"] = colors[index][0]
        gdf.loc[ind, "G"] = colors[index][1]
        gdf.loc[ind, "B"] = colors[index][2]

    initial_view_state = pdk.ViewState(
        latitude=40, longitude=-100, zoom=3, max_zoom=16, pitch=0, bearing=0
    )

    min_value = gdf[sp_attribute].min()
    max_value = gdf[sp_attribute].max()
    color = "color"
    # color_exp = f"[({selected_col}-{min_value})/({max_value}-{min_value})*255, 0, 0]"
    color_exp = f"[R, G, B]"

    geojson = pdk.Layer(
        "GeoJsonLayer",
        gdf,
        pickable=True,
        opacity=0.5,
        stroked=True,
        filled=True,
#         extruded=show_3d,
        wireframe=True,
#         get_elevation=f"{sp_attribute}",
#         elevation_scale=elev_scale,
#         get_fill_color="color",
        get_fill_color=color_exp,
        get_line_color=[0, 0, 0],
        get_line_width=2,
        line_width_min_pixels=1,
    )
    geojson_null = pdk.Layer(
        "GeoJsonLayer",
        gdf_null,
        pickable=True,
        opacity=0.2,
        stroked=True,
        filled=True,
        extruded=False,
        wireframe=True,
        # get_elevation="properties.ALAND/100000",
        # get_fill_color="color",
        get_fill_color=[200, 200, 200],
        get_line_color=[0, 0, 0],
        get_line_width=2,
        line_width_min_pixels=1,
    )
    tooltip = {
        "html": "<b>Name:</b> {NAME}<br><b>Value:</b> {"
        + sp_attribute
        + "}<br><b>Date:</b> "
        + month
        + "",
        "style": {"backgroundColor": "steelblue", "color": "white"},
    }

    layers = [geojson]

    if show_nodata:
        layers.append(geojson_null)
    r = pdk.Deck(
        layers=layers,
        initial_view_state=initial_view_state,
        map_style="light",
        tooltip=month,
    )

    row3_col1, row3_col2 = st.columns([6, 1])

    with row3_col1:
        st.pydeck_chart(r)
    with row3_col2:
        st.write(
            cm.create_colormap(
                palette,
                label=sp_attribute.replace("_", " ").title(),
                width=0.2,
                height=3,
                orientation="vertical",
                vmin=min_value,
                vmax=max_value,
                font_size=10,
            )
        )
    row4_col1,  row4_col3 = st.columns([1,  3])#row4_col2,2,
    with row4_col1:
        show_data = st.checkbox("Show raw data")
#     with row4_col2:
#         show_cols = st.multiselect("Select columns", data_cols)
    with row4_col3:
        show_colormaps = st.checkbox("Preview all color palettes")
        if show_colormaps:
            st.write(cm.plot_colormaps(return_fig=True))
    if show_data:
        if scale == "State":
            st.dataframe(gdf[["NAME", "STUSPS"] + [sp_attribute]])
        elif scale == "County":
            st.dataframe(gdf[["NAME", "STATEFP", "COUNTYFP"] + [sp_attribute]])
        
