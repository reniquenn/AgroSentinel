# 1. Usar una imagen base de Python liviana
FROM python:3.12-slim

# 2. Configurar el directorio de trabajo dentro del contenedor
WORKDIR /app

# 3. Copiar los archivos necesarios
COPY requirements.txt .
COPY dashboard_agro.py .
COPY serviceAccountKey.json .

# 4. Instalar las librerías
RUN pip install --no-cache-dir -r requirements.txt

# 5. Exponer el puerto que usa Streamlit
EXPOSE 8501

# 6. Comando para ejecutar la app
CMD ["streamlit", "run", "dashboard_agro.py", "--server.port=8501", "--server.address=0.0.0.0"]