import pandas as pd

def procesar_y_derivar(dato):
    """
    Recibe un dato crudo (JSON) y decide a qué departamento enviarlo.
    """
    derivacion = {
        "departamento": "",
        "accion": "",
        "prioridad": ""
    }
    
    # --- REGLA 1: CALIDAD (Crítica) ---
    # Si es para exportación, somos más estrictos (max 2°C)
    limite_temp = 2.0 if "Exportación" in dato['destino'] else 4.0
    
    if dato['temperatura'] > limite_temp:
        derivacion["departamento"] = "CALIDAD_Y_SEGURIDAD"
        derivacion["accion"] = f"BLOQUEAR LOTE (Valor: ${dato['valor_monetario']})"
        derivacion["prioridad"] = "ALTA 🚨"
        
    # --- REGLA 2: MANTENIMIENTO (Preventiva con IA) ---
    # Aquí usarías tu modelo IsolationForest. Si detecta anomalía técnica:
    elif dato.get('es_anomalia_ia') == -1: 
        derivacion["departamento"] = "MANTENIMIENTO"
        derivacion["accion"] = "REVISAR CALIBRACIÓN SENSOR"
        derivacion["prioridad"] = "MEDIA ⚠️"
        
    # --- REGLA 3: COMERCIAL/LOGÍSTICA ---
    # Si todo está bien, informamos a logística que el producto avanza
    else:
        derivacion["departamento"] = "LOGISTICA"
        derivacion["accion"] = "LIBERAR PARA DESPACHO"
        derivacion["prioridad"] = "NORMAL ✅"
        
    return derivacion

# Simulación de uso
# Supongamos que este dato llegó de Firebase
dato_ejemplo = {
    "sensor_id": "SENS-001", 
    "temperatura": 3.5, 
    "destino": "Exportación China", 
    "valor_monetario": 5000000,
    "es_anomalia_ia": 1
}

decision = procesar_y_derivar(dato_ejemplo)
print(f"Decisión del Sistema: Enviar a {decision['departamento']} -> {decision['accion']}")