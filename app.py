from flask import Flask, render_template
from flask_socketio import SocketIO
from mqtt.mqtt_client import MqqtClient
import json

app = Flask(__name__)
socketio = SocketIO(app)
mqtt_client = MqqtClient(socketio, 'user123')

@app.route('/')
def index():
    return render_template('index.html')



if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
