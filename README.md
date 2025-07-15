FicharSesame

Bot de Telegram + Flask para automatizar el fichaje en Sesame HR

📖 Descripción

FicharSesame es una aplicación en Python que combina un bot de Telegram, un endpoint HTTP en Flask y un programador de tareas para automatizar el registro de entrada (check-in) en la plataforma Sesame HR de tu empresa. Incluye:
	•	Bot de Telegram en polling con comandos y botones inline.
	•	Recordatorios configurables (modo prueba o producción) para recordar el fichaje.
	•	Persistencia de estado y registro de historial en JSON.
	•	Health endpoint en Flask para mantener el servicio vivo.
	•	Trigger seguro (token) para integrarse con Apple Shortcuts o cualquier cliente HTTP.

🧱 Arquitectura y componentes

+-----------------------+        +-------------------------+
|      Telegram User    |        |       Sesion HR API     |
|   (App Telegram)      | <----> |  (Sesame API endpoints) |
+-----------+-----------+        +-----------+-------------+
            |                                ^
            | Bot Telegram (python-telegram-bot)
            v                                |
+-----------+----------------------+         |
|    Application (main.py)          |--------+
|  - sesame_login()                 |
|  - sesame_check_in()              |
|  - cmd_start, cmd_fichar, handle_callback  |
|  - enviar_recordatorio()          |
|  - load_state(), save_state(), log_checkin()|
|  - Flask app for health & trigger|
|  - JobQueue for scheduling        |
+-----------------------------------+

Ficheros clave
	•	main.py: Lógica principal (bot, Flask, scheduling, persistencia).
	•	requirements.txt: Dependencias de Python.
	•	.env.example: Variables de entorno necesarias.
	•	state.json: Guarda la fecha+hora del último fichaje.
	•	history.json: Registra todos los timestamps de fichajes.

⚙️ Requisitos previos
	•	Python 3.10+ instalado.
	•	Git.
	•	Una cuenta de Telegram y un bot con token (@BotFather).
	•	Credenciales de Sesame HR (email, password, employee_id).
	•	(Opcional) Oracle Cloud Free Tier o VPS para despliegue.

📦 Instalación local
	1.	Clona el repositorio:

git clone https://github.com/<tu-usuario>/FicharSesame.git
cd FicharSesame


	2.	Crea y activa un entorno virtual:

python3 -m venv venv
source venv/bin/activate


	3.	Instala dependencias:

pip install -r requirements.txt


	4.	Copia el ejemplo de configuración:

cp .env.example .env


	5.	Edita .env y asigna valores reales:

TELEGRAM_TOKEN=123456:ABC-...
TELEGRAM_CHAT_ID=987654321
SESAME_EMAIL=tu_correo@empresa.com
SESAME_PASSWORD=tu_password
SESAME_EMPLOYEE_ID=uuid-de-empleado
SHORTCUT_TOKEN=token-secreto-atajo
DEBUG_MODE=1  # 1 para prueba, 0 para producción


	6.	Ejecuta localmente:

python main.py

Verás en consola:

* Running on http://0.0.0.0:8000/ (Flask health endpoint)
🧪 Bot escuchando en modo PRUEBA...


	7.	Prueba el bot en Telegram con /start y el endpoint health en tu navegador.

⸻

🚀 Despliegue en Oracle Cloud Free Tier
	1.	Crear cuenta y acceder a Oracle Cloud Free Tier.
	2.	Crear instancia: ARM Ampere A1 (Ubuntu 22.04, 1 OCPU, 1–2 GB RAM).
	3.	Configurar la Security List para abrir TCP/80 y TCP/443.
	4.	Conectar por SSH:

ssh -i ~/.ssh/id_rsa opc@IP_PUBLICA


	5.	Repetir pasos de instalación local dentro de la VM.
	6.	Crear servicio systemd:

[Unit]
Description=FicharSesame Bot
After=network.target

[Service]
User=opc
WorkingDirectory=/home/opc/FicharSesame
EnvironmentFile=/home/opc/FicharSesame/.env
ExecStart=/home/opc/FicharSesame/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target


	7.	Habilitar y arrancar:

sudo systemctl daemon-reload
sudo systemctl enable fichar
sudo systemctl start fichar


	8.	Verificar:
	•	sudo systemctl status fichar
	•	curl http://IP_PUBLICA/ → “OK”

⸻

🛠️ Uso y funcionamiento
	•	/start: muestra teclado con “✅ Fichar ahora”.
	•	/fichar: intenta login + check-in.
	•	Recordatorios:
	•	Modo prueba (DEBUG_MODE=1): cada 20s.
	•	Modo producción (DEBUG_MODE=0): 07:30 lun–vie + reintentos cada 10m.
	•	Trigger externo: GET /trigger_fichar?token=<SHORTCUT_TOKEN>.
	•	Persistencia:
	•	state.json: { "datetime": "ISO timestamp", "fichado": true/false }.
	•	history.json: [ { "timestamp": "ISO timestamp" }, ... ].

⸻

🗂️ Estructura del repositorio

FicharSesame/
├── main.py
├── requirements.txt
├── .env.example
├── README.md
├── state.json
├── history.json
└── .gitignore


⸻

📄 Licencia

MIT License. Consulta el archivo LICENSE para más detalles.
