# Utilizar una imagen base oficial de Python
FROM python:3.9-slim

# Establecer el directorio de trabajo en el contenedor
WORKDIR /app

# Copiar todo el contenido del directorio actual al contenedor
COPY . .

# Instalar las dependencias necesarias
RUN pip install --no-cache-dir -r source/requirements.txt

# Exponer el puerto en el que correrá la aplicación
EXPOSE 5000

# Comando por defecto para ejecutar la aplicación
CMD ["python", "source/pricesApp.py"]
