import os
import smtplib
from email.mime.text import MIMEText
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash # type: ignore
import sqlite3
import requests # type: ignore
from bs4 import BeautifulSoup # type: ignore

# Inicializa la aplicación Flask
app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Función para obtener la versión de la aplicación
def get_version():
    with open('version.txt', 'r') as file:
        return file.read().strip()

# Función para crear las tablas de la base de datos SQLite
def create_tables():
    conn = sqlite3.connect('/app/source/prices.db')
    cursor = conn.cursor()

    # Crear tabla de categorías
    cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      category_name TEXT UNIQUE,
                      parent_category_id INTEGER,
                      FOREIGN KEY (parent_category_id) REFERENCES categories (id))''')

    # Crear tabla de precios
    cursor.execute('''CREATE TABLE IF NOT EXISTS prices (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      url TEXT,
                      price INTEGER,
                      category_id INTEGER,
                      sub_category_id INTEGER,
                      image TEXT,
                      threshold REAL,
                      date TIMESTAMP,
                      FOREIGN KEY (category_id) REFERENCES categories (id),
                      FOREIGN KEY (sub_category_id) REFERENCES categories (id))''')

    conn.commit()
    conn.close()

# Llamar a create_tables() para asegurar que las tablas se crean al iniciar la aplicación
create_tables()

# Función para obtener los detalles del producto desde una URL
def get_product_details(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Extraer el precio
    price_element = soup.find('span', class_='copy12 primary senary jsx-2835692965 bold line-height-29')
    if price_element is None:
        app.logger.debug(soup.prettify())
        raise ValueError(f"Could not find price element in the page: {url}")
    
    price_text = price_element.text.strip().replace('$', '').replace('.', '').replace(',', '').strip()
    price = int(price_text)  # Convertir a entero

    # Extraer la categoría y subcategoría
    breadcrumbs = soup.find_all('a', href=lambda href: href and '/category/' in href)
    if not breadcrumbs:
        raise ValueError(f"Could not find category element in the page: {url}")

    general_category_name = None
    sub_category_name = None

    if len(breadcrumbs) > 1:
        general_category_element = breadcrumbs[-2]
        sub_category_element = breadcrumbs[-1]
        general_category_name = general_category_element.text.strip()
        sub_category_name = sub_category_element.text.strip()
    else:
        sub_category_element = breadcrumbs[-1]
        sub_category_name = sub_category_element.text.strip()

    # Obtener los IDs de las categorías
    general_category_id = insert_category(general_category_name)
    sub_category_id = insert_category(sub_category_name, general_category_id)

    # Extraer la imagen
    image_section = soup.find(lambda tag: tag.name == "section" and tag.get("class") and any("image" in cls for cls in tag.get("class", [])))
    if image_section is None:
        raise ValueError(f"Could not find image section in the page: {url}")
    
    image_element = image_section.find('img')
    if image_element is None:
        raise ValueError(f"Could not find image element in the page: {url}")
    
    image_url = image_element['src']
    
    return price, general_category_id, sub_category_id, image_url

# Función para insertar una categoría en la base de datos
def insert_category(category_name, parent_category_id=None):
    conn = sqlite3.connect('/app/source/prices.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM categories WHERE category_name = ?', (category_name,))
    result = cursor.fetchone()
    
    if result:
        category_id = result[0]
    else:
        cursor.execute('INSERT INTO categories (category_name, parent_category_id) VALUES (?, ?)', (category_name, parent_category_id))
        category_id = cursor.lastrowid
        conn.commit()
    
    conn.close()
    return category_id

# Función para insertar un nuevo precio en la base de datos
def insert_price(url, price, general_category_id, sub_category_id, image, threshold):
    conn = sqlite3.connect('/app/source/prices.db')
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO prices (url, price, category_id, sub_category_id, image, threshold, date)
                      VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''', (url, price, general_category_id, sub_category_id, image, threshold))
    conn.commit()
    conn.close()

# Función para comprobar si ha habido una bajada significativa en el precio
def check_price_drop(url):
    conn = sqlite3.connect('/app/source/prices.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT price, threshold FROM prices WHERE url = ? ORDER BY date DESC LIMIT 2''', (url,))
    rows = cursor.fetchall()
    conn.close()
    if len(rows) >= 2:
        old_price = rows[1][0]
        new_price = rows[0][0]
        threshold = rows[0][1]  # Usar el umbral del último registro
        if (old_price - new_price) / old_price >= threshold:
            return True, old_price, new_price
    return False, None, None

# Función para enviar un correo electrónico
def send_email(subject, body, to_email):
    from_email = os.getenv('EMAIL_USER')
    from_password = os.getenv('EMAIL_PASS')
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(from_email, from_password)
    server.sendmail(from_email, to_email, msg.as_string())
    server.quit()

# Ruta principal que renderiza el formulario para añadir una nueva URL
@app.route('/')
def index():
    version = get_version()
    conn = sqlite3.connect('/app/source/prices.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, category_name FROM categories WHERE parent_category_id IS NULL')
    categories = cursor.fetchall()
    conn.close()
    return render_template('index.html', categories=categories, version=version)

# Ruta para obtener detalles del producto y renderizarlo en la interfaz
@app.route('/product_details', methods=['GET'])
def product_details():
    url = request.args.get('url')
    try:
        price, general_category_id, sub_category_id, image = get_product_details(url)
        
        # Obtener los nombres de las categorías para mostrar en la interfaz
        conn = sqlite3.connect('/app/source/prices.db')
        cursor = conn.cursor()
        cursor.execute('SELECT category_name FROM categories WHERE id = ?', (general_category_id,))
        general_category_name = cursor.fetchone()[0]
        cursor.execute('SELECT category_name FROM categories WHERE id = ?', (sub_category_id,))
        sub_category_name = cursor.fetchone()[0]
        conn.close()

        return jsonify({
            'price': price,
            'general_category': general_category_name,
            'sub_category': sub_category_name,
            'image': image
        })
    except Exception as e:
        app.logger.error(f"Error getting product details for URL {url}: {e}")
        return jsonify({'error': str(e)}), 500

# Ruta para manejar solicitudes de categorías y obtener subcategorías
@app.route('/categories/<int:category_id>/subcategories', methods=['GET'])
def get_subcategories(category_id):
    conn = sqlite3.connect('/app/source/prices.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, category_name FROM categories WHERE parent_category_id = ?', (category_id,))
    subcategories = cursor.fetchall()
    conn.close()
    return jsonify(subcategories)

# Ruta para manejar solicitudes de productos por categoría o subcategoría
@app.route('/categories/<int:category_id>/products', methods=['GET'])
def get_products_by_category(category_id):
    conn = sqlite3.connect('/app/source/prices.db')
    cursor = conn.cursor()
    cursor.execute('SELECT url, price, image FROM prices WHERE category_id = ? OR sub_category_id = ?', (category_id, category_id))
    products = cursor.fetchall()
    conn.close()
    return jsonify(products)

# Ruta para mostrar los 10 últimos productos agregados
@app.route('/recent')
def recent_products():
    conn = sqlite3.connect('/app/source/prices.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT url, price, image FROM prices ORDER BY date DESC LIMIT 10''')
    recent_products = cursor.fetchall()
    conn.close()
    return render_template('recent.html', recent_products=recent_products)

# Ruta que maneja el formulario de entrada de URL y umbral
@app.route('/add_url', methods=['POST'])
def add_url():
    url = request.form['url']
    threshold = float(request.form['threshold'])
    create_tables()
    try:
        price, general_category_id, sub_category_id, image = get_product_details(url)
        
        # Check for existing product with the same URL and threshold
        conn = sqlite3.connect('/app/source/prices.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM prices WHERE url = ? AND threshold = ?", (url, threshold))
        existing_product = cursor.fetchone()
        
        if existing_product:
            if existing_product[2] != price:
                cursor.execute("INSERT INTO prices (url, price, category_id, sub_category_id, image, threshold, date) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", 
                            (url, price, general_category_id, sub_category_id, image, threshold))
                conn.commit()
                flash('Producto con variación de precio agregado.', 'success')
            else:
                flash('Producto ya registrado.', 'warning')
        else:
            cursor.execute("INSERT INTO prices (url, price, category_id, sub_category_id, image, threshold, date) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)", 
                        (url, price, general_category_id, sub_category_id, image, threshold))
            conn.commit()
            flash('Producto agregado exitosamente.', 'success')
        
        conn.close()
        
    except Exception as e:
        app.logger.error(f"Error getting product details for URL {url}: {e}")
        return f"Error: {e}", 500
    return redirect(url_for('index'))

# Ejecuta la aplicación Flask en el puerto 5000
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
