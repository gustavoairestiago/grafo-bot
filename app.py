import streamlit as st
from transitions import Machine
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
import io

# 1. Projetos e paletas
PROJECTS = {
    "Projeto Alpha": {"plotly": ["#005CA9","#FFA726","#66BB6A","#EF5350","#AB47BC"], "folium": "YlGn"},
    "Projeto Beta":  {"plotly": ["#FFD700","#0E4C92","#E63946","#457B9D","#2A9D8F"], "folium": "BuPu"},
    "Projeto Gamma": {"plotly": ["#FF5733","#33FFBD","#3385FF","#FF33A8","#8D33FF"], "folium": "OrRd"}
}

# 2. Utilitários
def col_type(df,col):
    dt=df[col].dtype
    if pd.api.types.is_numeric_dtype(dt):       return "Numérica"
    if pd.api.types.is_bool_dtype(dt):          return "Booleana"
    if pd.api.types.is_datetime64_any_dtype(dt):return "Data/Hora"
    if pd.api.types.is_categorical_dtype(dt) or df[col].nunique()<20: return "Categórica"
    return "Texto"

def format_cols(df):
    return [f"{c} ({col_type(df,c)})" for c in df.columns]

def name(label):
    return label.split(" (")[0]

def aggregate_df(df,x,y,agg):
    funcs={"Média":"mean","Soma":"sum","Contagem":"count","Mínimo":"min","Máximo":"max"}
    if agg=="Contagem":
        return df.groupby(x)[y].count().reset_index(name=y)
    return df.groupby(x)[y].agg(funcs[agg]).reset_index()

def map_choro(df,geojson,column,fill_color):
    m=folium.Map(location=[-14,-52],zoom_start=4)
    folium.Choropleth(
        geo_data=geojson, data=df,
        columns=[df.columns[0],column],
        key_on="feature.properties.id",
        fill_color=fill_color, legend_name=column
    ).add_to(m)
    st_folium(m,width=700)

# 3. Estados
states=['project','start','choose_chart','chart_bar','chart_scatter',
        'choose_agg','show_agg','choose_map','map_choropleth']
transitions=[
    {'trigger':'to_start','source':'project','dest':'start'},
    {'trigger':'go_chart','source':'start','dest':'choose_chart'},
    {'trigger':'bar','source':'choose_chart','dest':'chart_bar'},
    {'trigger':'scatter','source':'choose_chart','dest':'chart_scatter'},
    {'trigger':'agg','source':'choose_chart','dest':'choose_agg'},
    {'trigger':'showagg','source':'choose_agg','dest':'show_agg'},
    {'trigger':'go_map','source':'start','dest':'choose_map'},
    {'trigger':'choropleth','source':'choose_map','dest':'map_choropleth'},
    {'trigger':'back','source':'*','dest':'start'},
    {'trigger':'restart','source':'*','dest':'project'}
]

class Bot: pass

# 4. Session state
for key,default in [('state','project'),('project',None),('dataset',None)]:
    if key not in st.session_state: st.session_state[key]=default

bot=Bot()
Machine(model=bot, states=states, transitions=transitions, initial=st.session_state['state'])
def upd(): st.session_state['state']=bot.state

st.title("GrafoBot")

# 5. Projeto
if bot.state=='project':
    st.write("**Selecione projeto**:")
    proj=st.selectbox("Projeto",list(PROJECTS.keys()),key="proj_sel")
    if st.button("Confirmar"):
        st.session_state['project']=proj; bot.to_start(); upd(); st.rerun()
    st.stop()

project=st.session_state['project']
palette=PROJECTS[project]['plotly']
folium_pal=PROJECTS[project]['folium']

# 6. Upload
if st.session_state['dataset'] is None:
    up=st.file_uploader("CSV ou XLSX",type=["csv","xlsx"])
    if up:
        df=pd.read_csv(up) if up.name.endswith('.csv') else pd.read_excel(up)
        st.session_state['dataset']=df; st.success("Carregado!"); st.rerun()
    st.stop()

df=st.session_state['dataset']

# 7. Fluxo
if bot.state=='start':
    st.write(f"**Projeto:** {project}")
    c1,c2,c3=st.columns(3)
    if c1.button("Gráfico",on_click=lambda:[bot.go_chart(),upd()]): st.rerun()
    if c2.button("Mapa",   on_click=lambda:[bot.go_map(),upd()]):   st.rerun()
    if c3.button("Trocar projeto",on_click=lambda:[bot.restart(),upd()]): st.rerun()

elif bot.state=='choose_chart':
    st.write("**Gráfico ou Tabela**")
    c1,c2,c3=st.columns(3)
    if c1.button("Barra",on_click=lambda:[bot.bar(),upd()]):      st.rerun()
    if c2.button("Dispersão",on_click=lambda:[bot.scatter(),upd()]):st.rerun()
    if c3.button("Tabela/Agregação",on_click=lambda:[bot.agg(),upd()]):st.rerun()
    if st.button("Voltar",on_click=lambda:[bot.back(),upd()]):    st.rerun()

# 8. Barra
elif bot.state=='chart_bar':
    st.write("**Barra com agregação**")
    x_opts=[o for o in format_cols(df) if "(Categórica)" in o or "(Texto)" in o]
    y_opts=[o for o in format_cols(df) if "(Numérica)" in o]
    xl=st.selectbox("Eixo X",x_opts,key="bx"); yl=st.selectbox("Eixo Y",y_opts,key="by")
    agg=st.selectbox("Agregação",["Média","Soma","Contagem","Mínimo","Máximo"],key="ba")
    x=name(xl); y=name(yl)

    st.markdown("#### Opções")
    title=st.text_input("Título",value=f"{agg} de {y} por {x}",key="bt")
    meta=st.text_area("Fonte/ano",key="bm")
    show=st.checkbox("Exibir valores",value=True,key="bv")
    dec=st.number_input("Casas decimais",min_value=0,max_value=6,value=2,key="bd")

    if st.button("Gerar gráfico"):
        df2=aggregate_df(df,x,y,agg)
        labels = df2[y].round(dec)
        fig=px.bar(df2,x=x,y=y,color=x,
                   color_discrete_sequence=palette,title=title,
                   text=labels if show else None)
        fig.update_traces(texttemplate='%{text}',textposition="auto")
        if meta.strip():
            fig.add_annotation(text=meta,xref="paper",yref="paper",
                               x=0,y=-0.22,showarrow=False,
                               font=dict(size=12,color="gray"),align="left")
        st.plotly_chart(fig,use_container_width=True)
        buf=io.BytesIO(); fig.write_image(buf,format="png",engine="kaleido",width=800,height=500,scale=2)
        st.download_button("Exportar PNG",buf.getvalue(),"grafico.png","image/png")
        if meta.strip(): st.markdown(f"_Fonte: {meta}_")
    if st.button("Voltar",on_click=lambda:[bot.back(),upd()]): st.rerun()

# 9. Dispersão
elif bot.state=='chart_scatter':
    st.write("**Dispersão com agregação**")
    x_opts=[o for o in format_cols(df) if "(Categórica)" in o or "(Texto)" in o]
    y_opts=[o for o in format_cols(df) if "(Numérica)" in o]
    xl=st.selectbox("Eixo X",x_opts,key="sx"); yl=st.selectbox("Eixo Y",y_opts,key="sy")
    agg=st.selectbox("Agregação",["Média","Soma","Contagem","Mínimo","Máximo"],key="sa")
    col_opts=["(nenhum)"]+x_opts
    cl=st.selectbox("Colorir",col_opts,key="sc")
    x=name(xl); y=name(yl)
    color=None if cl=="(nenhum)" else name(cl)

    st.markdown("#### Opções")
    title=st.text_input("Título",value=f"{agg} de {y} por {x}",key="st")
    meta=st.text_area("Fonte/ano",key="sm")
    show=st.checkbox("Exibir valores",value=False,key="sv")
    dec=st.number_input("Casas decimais",min_value=0,max_value=6,value=2,key="sd")

    if st.button("Gerar gráfico"):
        df2=aggregate_df(df,x,y,agg)
        labels = df2[y].round(dec)
        fig=px.scatter(df2,x=x,y=y,color=color,
                       color_discrete_sequence=palette,title=title,
                       text=labels if show else None)
        fig.update_traces(textposition="top center")
        if meta.strip():
            fig.add_annotation(text=meta,xref="paper",yref="paper",
                               x=0,y=-0.22,showarrow=False,
                               font=dict(size=12,color="gray"),align="left")
        st.plotly_chart(fig,use_container_width=True)
        buf=io.BytesIO(); fig.write_image(buf,format="png",engine="kaleido",width=800,height=500,scale=2)
        st.download_button("Exportar PNG",buf.getvalue(),"grafico.png","image/png")
        if meta.strip(): st.markdown(f"_Fonte: {meta}_")
    if st.button("Voltar",on_click=lambda:[bot.back(),upd()]): st.rerun()

# 10. Tabela
elif bot.state=='choose_agg':
    st.write("**Tabela de Agregação**")
    cat=[o for o in format_cols(df) if "(Categórica)" in o or "(Texto)" in o]
    num=[o for o in format_cols(df) if "(Numérica)" in o]
    if not cat or not num:
        st.warning("Precisa de col. categórica/texto e numérica.")
    else:
        xl=st.selectbox("Agrupar por",cat,key="tx")
        yl=st.selectbox("Valor",num,key="ty")
        agg=st.selectbox("Agregação",["Média","Soma","Contagem","Mínimo","Máximo"],key="tt")
        if st.button("Gerar tabela"):
            st.session_state['agg_cat']=name(xl)
            st.session_state['agg_num']=name(yl)
            st.session_state['agg_func']=agg
            bot.showagg(); upd(); st.rerun()
    if st.button("Voltar",on_click=lambda:[bot.back(),upd()]): st.rerun()

elif bot.state=='show_agg':
    x=st.session_state['agg_cat']; y=st.session_state['agg_num']; agg=st.session_state['agg_func']
    funcs={"Média":"mean","Soma":"sum","Contagem":"count","Mínimo":"min","Máximo":"max"}
    df2=df.groupby(x)[y].agg(funcs[agg]).reset_index()
    st.dataframe(df2)
    if st.button("Voltar",on_click=lambda:[bot.back(),upd()]): st.rerun()

# 11. Mapa
elif bot.state=='choose_map':
    st.write("**Mapa Choropleth**")
    if st.button("Choropleth",on_click=lambda:[bot.choropleth(),upd()]): st.rerun()
    if st.button("Voltar",on_click=lambda:[bot.back(),upd()]): st.rerun()

elif bot.state=='map_choropleth':
    st.write("Selecione coluna e GeoJSON")
    cols=format_cols(df)
    cl=st.selectbox("Coluna",cols,key="mc")
    geo=st.file_uploader("GeoJSON",type="geojson",key="mf")
    if geo and st.button("Gerar mapa"):
        gj=geo.read().decode("utf-8")
        map_choro(df,gj,name(cl),folium_pal)
    if st.button("Voltar",on_click=lambda:[bot.back(),upd()]): st.rerun()
