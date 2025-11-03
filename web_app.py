"""
PythonAnywhere Web App file
This file is used by PythonAnywhere's web app feature to serve the health check endpoints
"""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Discord Bot is running!<br><br>Use /ping to check status"

@app.route('/ping')
def ping():
    return "pong", 200

@app.route('/health')
def health():
    return {"status": "ok", "service": "discord-bot"}, 200

# PythonAnywhere will use this app object
# Note: The Discord bot itself runs separately via an Always-on Task or in a Bash console



