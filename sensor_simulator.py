import time
import random
import os
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# --- CONFIGURACIÓN ---
directorio_actual = os.path.dirname(os.path.abspath(__file__))
ruta_credencial = os.path.join(directorio_actual, "serviceAccountKey.json")

if not os.path.exists(ruta_credencial):
    print(f"❌ ERROR: No encuentro el archivo json en: {directorio_actual}")
    exit()

cred = credentials.Certificate(ruta_credencial)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# --- VARIABLES GLOBALES DE ESTADO ---
# Tendencia de vibración (Mantenimiento)
DESGASTE_MTR_CINTA = 1.0 
# Tendencia de Stock (Logística) - Empezamos con 5000 cajas
STOCK_CAJAS = 5000 

# --- FUNCIONES GENERADORAS ---

def generar_calidad():
    global STOCK_CAJAS
    # Cada vez que producimos, gastamos cajas
    STOCK_CAJAS -= random.randint(10, 50) 
    
    # Simular reposición si bajamos mucho (para que el ciclo no muera)
    if STOCK_CAJAS < 500:
        STOCK_CAJAS = 5000
        print("🚚 LOGÍSTICA: ¡Llegó camión con cajas! Stock repuesto.")

    corte = random.choice([{"n": "Pollo", "p": 4500}, {"n": "Cerdo", "p": 8900}])
    peso = random.randint(500, 2000)
    
    return {
        "area": "CALIDAD",
        "sensor_id": f"LOTE-{random.randint(100,999)}",
        "timestamp": datetime.now(),
        "producto": corte["n"],
        "peso_kg": peso,
        "destino": random.choice(["China", "USA", "Chile"]),
        "monto_estimado": peso * corte["p"]
    }

def generar_inventario():
    """NUEVO: Sensor de nivel de bodega en tiempo real"""
    global STOCK_CAJAS
    return {
        "area": "INVENTARIO", # Nueva Área
        "sensor_id": "BODEGA-INSUMOS-01",
        "timestamp": datetime.now(),
        "item": "Cajas de Cartón Estándar",
        "nivel_actual": STOCK_CAJAS,
        "capacidad_max": 5000,
        "unidad": "Unidades"
    }

def generar_mantenimiento():
    global DESGASTE_MTR_CINTA
    # Simulación de desgaste progresivo
    DESGASTE_MTR_CINTA += random.uniform(0.02, 0.08)
    if DESGASTE_MTR_CINTA > 8.0: DESGASTE_MTR_CINTA = 1.0
    
    vib = round(DESGASTE_MTR_CINTA + random.uniform(-0.3, 0.3), 2)
    
    return {
        "area": "MANTENIMIENTO",
        "sensor_id": "MTR-CINTA-01",
        "timestamp": datetime.now(),
        "maquina": "Cinta Principal",
        "vibracion_nivel": vib,
        "estado_operativo": "CRÍTICO" if vib > 5.0 else "OPERATIVO"
    }

def generar_sustentabilidad():
    return {
        "area": "SUSTENTABILIDAD", 
        "sensor_id": "RILES-01",
        "timestamp": datetime.now(), 
        "ph_agua": round(random.uniform(6.5, 8.5), 2)
    }

# --- BUCLE ---
def iniciar_simulacion():
    print("🚀 AgroSentinel AI: Simulando Desgaste y Consumo de Stock...")
    try:
        while True:
            # Generamos eventos aleatorios
            dado = random.choice(["CALIDAD", "MANTENIMIENTO", "SUSTENTABILIDAD", "INVENTARIO"])
            
            if dado == "CALIDAD":
                d = generar_calidad()
                print(f"🍖 CALIDAD: Nuevo lote. Stock cajas restante: {STOCK_CAJAS}")
            elif dado == "INVENTARIO":
                d = generar_inventario()
                print(f"📦 INVENTARIO: Reportando nivel bodega: {d['nivel_actual']}")
            elif dado == "MANTENIMIENTO":
                d = generar_mantenimiento()
                print(f"⚙️ MANTENIMIENTO: Vibración {d['vibracion_nivel']}")
            else:
                d = generar_sustentabilidad()
                print(f"🌿 AMBIENTE: pH {d['ph_agua']}")

            db.collection("sensor_data").add(d)
            time.sleep(1) 
            
    except KeyboardInterrupt:
        print("\n🛑 Fin.")

if __name__ == "__main__":
    iniciar_simulacion()