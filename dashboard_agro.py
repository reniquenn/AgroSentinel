import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import plotly.express as px
import plotly.graph_objects as go
import os
import io
import qrcode
import numpy as np
from fpdf import FPDF
import tempfile
from datetime import timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AgroSentinel AI Ultimate", layout="wide", page_icon="🔮")

# --- CONEXIÓN FIREBASE ---
@st.cache_resource
def conectar_firebase():
    base_path = os.path.dirname(os.path.abspath(__file__))
    cert_path = os.path.join(base_path, "serviceAccountKey.json")
    if not firebase_admin._apps:
        cred = credentials.Certificate(cert_path)
        firebase_admin.initialize_app(cred)
    return firestore.client()

try: db = conectar_firebase()
except Exception as e: st.stop()

# --- CARGA DATOS ---
def cargar_datos():
    docs = db.collection("sensor_data").order_by("timestamp", direction=firestore.Query.DESCENDING).limit(1000).stream()
    data = [doc.to_dict() for doc in docs]
    df = pd.DataFrame(data)
    
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 1. Asegurar que existan todas las columnas
        cols = ['area', 'monto_estimado', 'destino', 'peso_kg', 'producto', 
                'temperatura_motor', 'vibracion_nivel', 'estado_operativo',
                'ph_agua', 'sensor_id', 'nivel_actual', 'capacidad_max']
        for c in cols: 
            if c not in df.columns: df[c] = None

        # 2. CORRECCIÓN IMPORTANTE: Forzar que nivel_actual sea numérico
        df['nivel_actual'] = pd.to_numeric(df['nivel_actual'], errors='coerce')
        df['vibracion_nivel'] = pd.to_numeric(df['vibracion_nivel'], errors='coerce')

        # Feature Engineering simple
        def iso(d): return "CHN" if isinstance(d,str) and "China" in d else "USA" if isinstance(d,str) and "USA" in d else "CHL"
        df['iso_alpha'] = df['destino'].apply(iso)
        
        # Fix montos
        df['monto_estimado'] = df.apply(lambda r: r['peso_kg']*5000 if r['area']=='CALIDAD' and pd.notnull(r['peso_kg']) and pd.isnull(r['monto_estimado']) else r['monto_estimado'], axis=1)

    return df

# --- PDF GENERATOR ---
def generar_pdf_certificado(datos, qr_bytes):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'CERTIFICADO DE CALIDAD', 0, 1, 'C')
    pdf.ln(20)
    pdf.set_font('Arial', '', 12)
    pdf.cell(0, 10, f'ID: {datos["sensor_id"]}', 0, 1)
    pdf.cell(0, 10, f'Producto: {datos["producto"]}', 0, 1)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as t:
        t.write(qr_bytes.getvalue())
        path = t.name
    pdf.image(path, x=10, y=60, w=50)
    os.unlink(path)
    return pdf.output(dest='S').encode('latin-1')

# --- EXCEL ---
def generar_excel(df_in):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as w:
        for area in df_in['area'].unique():
            if area:
                d = df_in[df_in['area']==area].dropna(axis=1, how='all')
                if 'timestamp' in d.columns: d['timestamp'] = d['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
                d.to_excel(w, sheet_name=str(area)[:30], index=False)
    return out.getvalue()

# --- APP ---
st.title("🔮 AgroSentinel: Inteligencia Artificial Logística")

df_raw = cargar_datos()
if df_raw.empty: st.warning("Ejecuta el simulador."); st.stop()

if st.sidebar.button("🔄 Refrescar AI"): st.rerun()
f_date = st.sidebar.date_input("Fecha", df_raw['timestamp'].max())
df = df_raw[df_raw['timestamp'].dt.date == f_date]

# Descarga Excel Global
if not df.empty:
    st.sidebar.download_button("📥 Descargar Reporte Completo", generar_excel(df), "Reporte.xlsx")

# --- DATA PREP ---
df_inv = df_raw[df_raw['area'] == "INVENTARIO"].sort_values('timestamp')
df_mant = df_raw[df_raw['area'] == "MANTENIMIENTO"].sort_values('timestamp')
df_cal = df[df['area'] == "CALIDAD"]

# --- TABS ---
t1, t2, t3, t4, t5 = st.tabs(["📦 AI Stock (Nuevo)", "🧠 AI Mantención", "🌍 Mapa", "📄 Certificados", "🌿 Ambiente"])

# --- TAB 1: PREDICCIÓN DE STOCK (CORREGIDO) ---
with t1:
    st.subheader("Predicción de Agotamiento de Insumos (Supply Chain)")
    
    # Limpieza de datos CRÍTICA antes de calcular
    # Eliminamos filas donde el nivel sea NaN (vacío)
    df_inv_clean = df_inv.dropna(subset=['nivel_actual', 'timestamp'])
    
    if len(df_inv_clean) > 5:
        # Tomamos el último ciclo de consumo
        ultimo_lleno = df_inv_clean[df_inv_clean['nivel_actual'] > 4000]['timestamp'].max()
        
        if pd.notnull(ultimo_lleno):
            df_ciclo = df_inv_clean[df_inv_clean['timestamp'] >= ultimo_lleno].copy()
        else:
            df_ciclo = df_inv_clean.copy()

        # Validación extra: necesitamos al menos 2 puntos para trazar una línea
        if len(df_ciclo) >= 2:
            try:
                # Matemática de Predicción
                df_ciclo['seconds'] = (df_ciclo['timestamp'] - df_ciclo['timestamp'].min()).dt.total_seconds()
                
                # Ajuste lineal (Aquí daba el error, ahora está protegido)
                coeffs = np.polyfit(df_ciclo['seconds'], df_ciclo['nivel_actual'], 1)
                poly = np.poly1d(coeffs)
                
                # Calcular cuándo llegará a CERO
                if coeffs[0] != 0: # Evitar división por cero
                    tiempo_cero_segundos = -coeffs[1] / coeffs[0]
                    fecha_cero = df_ciclo['timestamp'].min() + timedelta(seconds=tiempo_cero_segundos)
                else:
                    fecha_cero = df_ciclo['timestamp'].max() # Si es plano, no cambia

                # Graficar
                df_ciclo['tendencia'] = poly(df_ciclo['seconds'])
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=df_ciclo['timestamp'], y=df_ciclo['nivel_actual'], mode='lines+markers', name='Stock Real'))
                fig.add_trace(go.Scatter(x=df_ciclo['timestamp'], y=df_ciclo['tendencia'], mode='lines', name='Proyección AI', line=dict(dash='dot', color='red')))
                
                # KPI Visual
                stock_hoy = df_ciclo['nivel_actual'].iloc[-1]
                c1, c2 = st.columns(2)
                c1.metric("Stock Actual (Cajas)", int(stock_hoy), delta=f"{coeffs[0]*60:.1f} cajas/min")
                
                minutos_restantes = (fecha_cero - df_ciclo['timestamp'].max()).total_seconds() / 60
                
                if minutos_restantes > 0 and stock_hoy > 0:
                    c2.metric("Tiempo estimado para Quiebre", f"{int(minutos_restantes)} minutos", f"Fecha: {fecha_cero.strftime('%H:%M:%S')}", delta_color="inverse")
                    st.success(f"✅ Abastecimiento OK. Stock proyectado hasta: {fecha_cero}")
                else:
                    c2.metric("ESTADO CRÍTICO", "STOCK AGOTADO", delta_color="inverse")
                    st.error("🚨 ALERTA: Stock crítico o agotado.")
                    
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.warning(f"No se pudo calcular la predicción aún (Datos inestables): {e}")
        else:
            st.info("Esperando más puntos de datos para trazar la línea...")
    else:
        st.info("Recopilando datos históricos de inventario...")

# --- TAB 2: MANTENIMIENTO (CORREGIDO) ---
with t2:
    st.subheader("Mantenimiento Predictivo")
    # Limpieza previa
    df_mant_clean = df_mant.dropna(subset=['vibracion_nivel', 'timestamp'])
    
    if len(df_mant_clean) > 5:
        df_mant_clean['secs'] = (df_mant_clean['timestamp'] - df_mant_clean['timestamp'].min()).dt.total_seconds()
        
        try:
            coeffs = np.polyfit(df_mant_clean['secs'], df_mant_clean['vibracion_nivel'], 1)
            df_mant_clean['trend'] = np.poly1d(coeffs)(df_mant_clean['secs'])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_mant_clean['timestamp'], y=df_mant_clean['vibracion_nivel'], mode='markers', name='Vibración'))
            fig.add_trace(go.Scatter(x=df_mant_clean['timestamp'], y=df_mant_clean['trend'], mode='lines', name='Tendencia', line=dict(color='orange')))
            fig.add_hline(y=5.0, line_color="red")
            st.plotly_chart(fig, use_container_width=True)
            st.info(f"Tasa de degradación: {coeffs[0]*3600:.3f} mm/s por hora.")
        except:
            st.warning("Calculando modelo matemático...")
    else:
        st.info("Esperando datos de sensores de vibración...")

# --- OTRAS TABS ---
with t3:
    if not df_cal.empty:
        st.plotly_chart(px.choropleth(df_cal, locations="iso_alpha", color="monto_estimado"), use_container_width=True)

with t4:
    if not df_cal.empty:
        sel = st.selectbox("Lote:", df_cal['sensor_id'].unique())
        if st.button("Generar PDF"):
            dat = df_cal[df_cal['sensor_id']==sel].iloc[0]
            qr = qrcode.make(sel); b = io.BytesIO(); qr.save(b, format='PNG')
            st.download_button("Descargar", generar_pdf_certificado(dat, b), "Cert.pdf")

with t5:
    df_amb = df_raw[df_raw['area']=="SUSTENTABILIDAD"].dropna(subset=['ph_agua'])
    if not df_amb.empty:
        st.plotly_chart(px.line(df_amb, x='timestamp', y='ph_agua'), use_container_width=True)