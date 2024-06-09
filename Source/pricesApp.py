import os
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import requests
from bs4 import BeautifulSoup

# Inicializa la aplicación Flask
app = Flask(__name__)

# Función para obtener el precio desde una URL
def get_price(url):
    # Realiza una solicitud HTTP a la URL dada
    response = requests.get(url)
    # Analiza el contenido HTML de la respuesta
    soup = BeautifulSoup(response.text, 'html.parser')
    # Extrae el precio del HTML (ajustar según la estructura específica de la página)
    price = soup.find('span', {'class': 'price'}).text
    # Convierte el precio a un número flotante
    return float(price.replace('$', '').replace(',', ''))

# Función para crear la tabla de precios en la base de datos SQLite
def create_table():
    # Conecta a la base de datos SQLite (crea el archivo si no existe)
    conn = sqlite3.connect('prices.db')
    cursor = conn.cursor()
    # Crea la tabla si no existe
    cursor.execute('''CREATE TABLE IF NOT EXISTS prices
                      (url TEXT, price REAL, date TIMESTAMP)''')
    conn.commit()
    conn.close()

# Función para insertar un nuevo precio en la base de datos
def insert_price(url, price):
    # Conecta a la base de datos SQLite
    conn = sqlite3.connect('prices.db')
    cursor = conn.cursor()
    # Inserta un nuevo registro de precio con la URL, precio y fecha actual
    cursor.execute('''INSERT INTO prices (url, price, date)
                      VALUES (?, ?, CURRENT_TIMESTAMP)''', (url, price))
    conn.commit()
    conn.close()

# Función para comprobar si ha habido una bajada significativa en el precio
def check_price_drop(url, threshold):
    # Conecta a la base de datos SQLite
    conn = sqlite3.connect('prices.db')
    cursor = conn.cursor()
    # Selecciona los dos precios más recientes para la URL dada
    cursor.execute('''SELECT price FROM prices WHERE url = ? ORDER BY date DESC LIMIT 2''', (url,))
    prices = cursor.fetchall()
    conn.close()
    # Comprueba si hay al menos dos registros de precio
    if len(prices) >= 2:
        old_price = prices[1][0]
        new_price = prices[0][0]
        # Calcula la caída de precio y compara con el umbral
        if (old_price - new_price) / old_price >= threshold:
            return True, old_price, new_price
    return False, None, None

# Función para enviar un correo electrónico
def send_email(subject, body, to_email):
    # Obtiene las credenciales de correo electrónico de las variables de entorno
    from_email = os.getenv('EMAIL_USER')
    from_password = os.getenv('EMAIL_PASS')
    # Crea el mensaje de correo electrónico
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    # Configura y conecta al servidor SMTP de Gmail
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(from_email, from_password)
    # Envía el correo electrónico
    server.sendmail(from_email, to_email, msg.as_string())
    # Cierra la conexión con el servidor SMTP
    server.quit()

# Ruta principal que renderiza el formulario para añadir una nueva URL
@app.route('/')
def index():
    return render_template('index.html')

# Ruta que maneja el formulario de entrada de URL y umbral
@app.route('/add_url', methods=['POST'])
def add_url():
    url = request.form['url']
    threshold = float(request.form['threshold'])
    create_table()
    price = get_price(url)
    insert_price(url, price)
    return redirect(url_for('index'))

# Ejecuta la aplicación Flask en el puerto 5000
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
