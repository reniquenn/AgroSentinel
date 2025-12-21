import firebase_admin
from firebase_admin import firestore, credentials
import pandas as pd
from datetime import datetime, timedelta

# (Conexión a Firebase omitida para brevedad, usa la misma lógica anterior)

def crear_reporte_fallas():
    # 1. Extraer: Obtener datos de las últimas 24 horas
    hace_24h = datetime.now() - timedelta(days=1)
    docs = db.collection("sensor_data").where("timestamp", ">", hace_24h).stream()
    
    # 2. Transformar: Filtrar solo las alertas de IA
    df = pd.DataFrame([d.to_dict() for d in docs])
    if df.empty: return
    
    fallas = df[df['estado'] == 'ALERTA']
    
    # Resumen por sensor
    resumen = fallas.groupby('sensor_id').agg({
        'temperatura': ['mean', 'max'],
        'sensor_id': 'count'
    }).reset_index()
    
    # 3. Cargar: Guardar en una nueva colección "warehouse_fallas_diarias"
    for _, fila in resumen.iterrows():
        db.collection("warehouse_fallas_diarias").add({
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "sensor": fila['sensor_id'][0],
            "total_alertas": int(fila['sensor_id']['count']),
            "temp_maxima_registrada": float(fila['temperatura']['max'])
        })
    print("✅ Reporte diario generado en el Warehouse.")