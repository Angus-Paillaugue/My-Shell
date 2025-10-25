import eventlet
eventlet.monkey_patch()

from flask import Flask, request, jsonify
import subprocess
import socket
from services.config import config
from flask_cors import CORS
import random
import time
import uuid
from zeroconf import ServiceInfo, Zeroconf, IPVersion
from .utils import get_lan_ip, get_or_create_device_id, get_or_create_api_key
from flask_socketio import SocketIO, send, emit

socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")

API_KEY = get_or_create_api_key()
DEVICE_ID = get_or_create_device_id()
pairing_sessions = {}  # { "device_ip": { "code": "123456", "expires_at": 12345678 } }

@socketio.on('connect')
def on_connect():
    print("[+] Socket connected:", request.sid)

@socketio.on('disconnect')
def on_disconnect():
    print("[+] Socket disconnected")

@socketio.on('message')
def handle_message(data):
    print(f"[+] Received message: {data}")
    action = data.get("action")
    api_key = data.get("api_key")
    payload = data.get("payload", {})
    # Handle pairing actions
    if api_key != API_KEY:
        match action:
            case "pair":
                session_id = str(uuid.uuid4())
                code = str(random.randint(100000, 999999))
                pairing_sessions[session_id] = {"code": code, "created": time.time()}
                subprocess.run(["notify-send", "PhoneBridge Pairing Code", f"Code: {code}"])
                emit('paired', {'session_id': session_id})
            case "verify_pair":
                session_id = payload.get("session_id")
                code = payload.get("code")
                if session_id in pairing_sessions and pairing_sessions[session_id]["code"] == code:
                    del pairing_sessions[session_id]
                    emit('verified', {'api_token': API_KEY})
                else:
                    emit('error', {'error': 'Invalid code'})
            case _:
                emit('error', {'error': 'Unauthorized'})
        return

    # Authenticated actions
    match action:
        case "notify":
            title = payload.get("title", "Notification")
            text = payload.get("text", "")
            subprocess.run(["notify-send", title, text])
        case "get_status":
            lock_state = subprocess.run(["pgrep", "-f", "hyprlock"], capture_output=True)
            locked = lock_state.returncode == 0
            emit('status', {'status': 'ok', 'locked': locked})
        case "lock":
            subprocess.run(["hyprlock"])
        case "unlock":
            subprocess.run(["pkill", "-USR1", "-f", f"hyprlock"])
        case _:
            emit('error', {'error': 'Unknown action'})
            return
    emit('status', {'status': 'ok'})



def create_app():
    app = Flask(__name__)
    socketio.init_app(app)
    return app

# Start Flask + Zeroconf
if __name__ == "__main__":
    hostname = socket.gethostname()

    ip = get_lan_ip()
    if ip is None:
        print("[!] Could not determine LAN IP")
        exit(1)
    zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
    info = ServiceInfo(
        "_phonebridge._tcp.local.",
        f"{hostname}._phonebridge._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=5000,
        properties={"name": hostname},
    )
    info = ServiceInfo(
        "_phonebridge._tcp.local.",
        f"{DEVICE_ID}._phonebridge._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=5000,
        properties={"name": hostname, "device_id": DEVICE_ID},
    )

    zeroconf.register_service(info)
    print(f"[+] Advertising service at {ip}:5000 as {hostname}")
    try:
        app = create_app()
        socketio.run(app, host='0.0.0.0', port=5000)
    finally:
        zeroconf.unregister_service(info)
        zeroconf.close()
