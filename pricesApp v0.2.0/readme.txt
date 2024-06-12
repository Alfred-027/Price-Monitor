Estructura de archivos en docker mini pc: 

Archivo docker compose de OMV:
*Aqui se referencia el archivo Dockerfile con las rutas y archivos para generar la imagen del contenedor. Archivo que se ubica en /appdata/pricesApp/ en mi entorno de desarrollo, pero en el proyecto git se ubica en la rai:

/compose/price-monitor/
├── price-monitor.env
└── price-monitor.yml

1 directory, 2 files


Archivos PricesApp:
*Aqui esta el codigo y archivos necesarios para el funcionamiento de la pagina:

/appdata/pricesApp/
├── docker-compose.yml
├── Dockerfile
├── LICENSE
├── RELEASE_NOTES.md
├── source
│   ├── pricesApp.py
│   ├── prices.db
│   └── requirements.txt
├── static
│   └── css
│       └── styles.css
├── templates
│   ├── category.html
│   ├── index.html
│   └── recent.html
└── version.txt

5 directories, 12 files
