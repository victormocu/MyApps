# -*- coding: utf-8 -*-
"""
Created on Fri Jul 11 10:56:14 2025

@author: UIN
"""
import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
import datetime
import plotly.express as px

# ----------- Contraseña simple -----------
PASSWORD = "uinapp"

def check_password():
    """Muestra input de contraseña en la ventana principal, desaparece tras validarse."""
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if not st.session_state.password_correct:
        st.title("🔒 Acceso restringido")
        password = st.text_input("Introduce la contraseña para acceder:", type="password")
        if password:
            if password == PASSWORD:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ----------- Subir archivo -----------
st.title("📊 Explorador de Datos de Inventario")

archivo = st.file_uploader("📁 Sube un archivo CSV o Excel", type=["csv", "xlsx"])

if archivo is not None:
    try:
        if archivo.name.endswith(".csv"):
            datos = pd.read_csv(archivo)
        else:
            xls = pd.ExcelFile(archivo)
            dfs = [pd.read_excel(xls, sheet) for sheet in xls.sheet_names]
            datos = pd.concat(dfs, ignore_index=True)
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.stop()



    # ----------- Filtros dinámicos en barra lateral -----------
    
    filtros = {}
    
    for col in datos.columns:
        valores_unicos = datos[col].dropna().unique()
        if len(valores_unicos) <= 1:
            # No mostrar filtro si no hay valores o solo hay 1 opción
            continue
    
        if len(valores_unicos) <= 30:
            seleccion = st.sidebar.multiselect(f"Filtrar por {col}", options=sorted(valores_unicos))
            if seleccion:
                filtros[col] = seleccion
    
        elif np.issubdtype(datos[col].dtype, np.datetime64) or np.issubdtype(datos[col].dtype, np.dtype('O')):
            try:
                fechas = pd.to_datetime(datos[col], errors='coerce')
                fechas_validas = fechas.dropna()
                if fechas_validas.nunique() > 1:
                    min_date = fechas_validas.min().date()
                    max_date = fechas_validas.max().date()
                    rango = st.sidebar.date_input(f"Rango de fechas para {col}", [min_date, max_date])
                    if rango and len(rango) == 2:
                        # Solo agregar filtro si el rango seleccionado no es el rango completo
                        if rango[0] > min_date or rango[1] < max_date:
                            filtros[col] = rango
            except:
                pass
    
        elif np.issubdtype(datos[col].dtype, np.number):
            col_sin_na = datos[col].dropna()
            if not col_sin_na.empty:
                min_val = float(col_sin_na.min())
                max_val = float(col_sin_na.max())
                if min_val != max_val:
                    rango = st.sidebar.slider(f"Rango para {col}", min_val, max_val, (min_val, max_val))
                    # Solo agregar filtro si el rango seleccionado no es el rango completo
                    if rango != (min_val, max_val):
                        filtros[col] = rango



    # Copiar datos para filtrar
    datos_filtrados = datos.copy()
    
    for col, valor in filtros.items():
        # Ignorar filtros vacíos
        if (isinstance(valor, list) or isinstance(valor, tuple)) and len(valor) == 0:
            continue
    
        if isinstance(valor, list) and all(isinstance(x, datetime.date) for x in valor):
            datos_filtrados = datos_filtrados[
                (pd.to_datetime(datos_filtrados[col], errors='coerce').dt.date >= valor[0]) &
                (pd.to_datetime(datos_filtrados[col], errors='coerce').dt.date <= valor[1])
            ]
        elif isinstance(valor, tuple) and (isinstance(valor[0], int) or isinstance(valor[0], float)):
            datos_filtrados = datos_filtrados[
                (datos_filtrados[col] >= valor[0]) & (datos_filtrados[col] <= valor[1])
            ]
        else:
            datos_filtrados = datos_filtrados[datos_filtrados[col].isin(valor)]

    
    # Ahora sí imprimes la cantidad de registros después de filtrar
    st.write(f"Registros totales: {datos.shape[0]}")
    st.write(f"Registros filtrados: {datos_filtrados.shape[0]}")


    # ----------- Tabs: Datos y Resumen -----------
    tab1, tab2 = st.tabs(["📈 Datos", "📊 Resumen"])

    with tab1:
        st.subheader("Tabla de datos filtrados")
        st.dataframe(datos_filtrados, use_container_width=True)

        def descargar_excel(df):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            processed_data = output.getvalue()
            return processed_data

        st.download_button(
            label="💾 Descargar archivo filtrado",
            data=descargar_excel(datos_filtrados),
            file_name=f"archivo_filtrado_{datetime.date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


    
    
    with tab2:
        st.subheader("Resumen General")
        st.write(f"✅ **Número de registros filtrados:** {datos_filtrados.shape[0]}")
        st.write(f"✅ **Número de columnas:** {datos_filtrados.shape[1]}")
    
        st.markdown("## Resumen Visual y Tabular por Variable Clave")
    
        # Definimos columnas clave y su tipo (para decidir gráfico y resumen)
        cols_clave = {
            "Linea": "cat",
            "Acrónimo línea": "cat",
            "Sexo": "cat",
            "Cepa": "cat",
            "Jaula": "cat",
            "Cruce origen": "cat",
            "F. nacimiento": "date",
            "Edad (días)": "num",
            "Gen": "cat"
        }
    
        for col, tipo in cols_clave.items():
            if col in datos_filtrados.columns:
                st.markdown(f"### {col}")
    
                # Categóricas: barra o pie + tabla top 5
                if tipo == "cat":
                    conteo = datos_filtrados[col].value_counts(dropna=False).reset_index()
                    conteo.columns = [col, "Cantidad"]
    
                    # Gráfico barra si muchas categorías, pie si pocas
                    if len(conteo) > 10:
                        fig = px.bar(conteo.head(20), x=col, y="Cantidad", color="Cantidad", color_continuous_scale="Blues")
                    else:
                        fig = px.pie(conteo, names=col, values="Cantidad", color=col)
    
                    st.plotly_chart(fig)
    
                    # Tabla top 5 categorías
                    st.dataframe(conteo.head(5), use_container_width=True)
    
                elif tipo == "num":
                    # Estadísticas y boxplot
                    min_val = datos_filtrados[col].min()
                    mean_val = datos_filtrados[col].mean()
                    median_val = datos_filtrados[col].median()
                    max_val = datos_filtrados[col].max()
                    na_count = datos_filtrados[col].isna().sum()
    
                    st.metric("Mínimo", round(min_val,2) if pd.notna(min_val) else "NA")
                    st.metric("Media", round(mean_val,2) if pd.notna(mean_val) else "NA")
                    st.metric("Mediana", round(median_val,2) if pd.notna(median_val) else "NA")
                    st.metric("Máximo", round(max_val,2) if pd.notna(max_val) else "NA")
                    st.metric("Valores NA", na_count)
    
                    fig = px.box(datos_filtrados, y=col, points="all")
                    st.plotly_chart(fig)
    
                elif tipo == "date":
                    # Histograma fechas + tabla con conteo top 5 años o meses
                    datos_filtrados[col] = pd.to_datetime(datos_filtrados[col], errors='coerce')
                    fig = px.histogram(datos_filtrados, x=col, nbins=30)
                    st.plotly_chart(fig)
    
                    # Conteo por año como ejemplo
                    años = datos_filtrados[col].dt.year.value_counts().reset_index()
                    años.columns = ["Año", "Cantidad"]
                    st.dataframe(años.head(5), use_container_width=True)


else:
    st.info("📥 Sube un archivo CSV o Excel para comenzar.")

