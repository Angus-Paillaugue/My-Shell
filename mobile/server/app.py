import eventlet
eventlet.monkey_patch()

from flask import Flask, request
import subprocess
import json
import os
import socket
import random
import time
import uuid
import setproctitle
from zeroconf import ServiceInfo, Zeroconf, IPVersion
from . import utils
from flask_socketio import SocketIO, emit
from services.logger import logger

socketio = SocketIO(cors_allowed_origins="*", async_mode="eventlet")
app = Flask(__name__)
socketio.init_app(app)

PORT=5000
API_KEY = utils.get_config()["api_key"]
DEVICE_ID = utils.get_config()["device_id"]
pairing_sessions = {}  # { "device_ip": { "code": "123456", "expires_at": 12345678 } }

@socketio.on('connect')
def on_connect():
    logger.debug("Socket connected: " + request.sid) # type: ignore
    actions = utils.get_actions(sanitized=True)
    socketio.emit('actions_updated', {'actions': actions})

@socketio.on('disconnect')
def on_disconnect():
    logger.debug("Socket disconnected")

@socketio.on('message')
def handle_message(data):
    action = data.get("action")
    api_key = data.get("api_key")
    payload = data.get("payload", {})
    actions = utils.get_actions()
    # Handle pairing actions
    if api_key != API_KEY:
        match action:
            case "pair":
                session_id = str(uuid.uuid4())
                code = str(random.randint(100000, 999999))
                pairing_sessions[session_id] = {"code": code, "created": time.time()}
                subprocess.run(["notify-send", "-e", "-t", "8000", "-a", "Vellum Shell PhoneBridge", "PhoneBridge Pairing Code", f"Code: {code}"])
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
        case "get_actions":
            emit('actions', {'actions': actions})
        case "command":
            command_id = data.get("command")
            if command_id not in [a["id"] for a in actions]:
                logger.error(f"Invalid action requested: {command_id}")
                emit('error', {'error': 'Invalid action'})
                return
            command = [a for a in actions if a["id"] == command_id][0]
            logger.debug(f"Executing command: {command_id}")
            try:
                env = os.environ.copy()
                result = subprocess.run(command['command'], shell=True, capture_output=True, text=True, timeout=10, env=env)
                if result.returncode != 0:
                    logger.error(f"[!] Command returned non-zero exit code: {result.returncode}")
                    logger.debug(json.dumps(result.__dict__, indent=2))
                emit('command_result', {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'returncode': result.returncode
                })
            except subprocess.TimeoutExpired:
                emit('error', {'error': 'Command timed out'})
        case _:
            emit('error', {'error': 'Unknown action'})
            return
    emit('status', {'status': 'ok'})

def monitor_config_changes(poll_interval=1):
    last_mtime = utils.get_config_mtime()
    while True:
        eventlet.sleep(poll_interval)
        try:
            mtime = utils.get_config_mtime()
            if mtime is not None and mtime != last_mtime:
                last_mtime = mtime
                utils.config_changed()
                actions = utils.get_actions(sanitized=True)
                logger.debug("Config changed — broadcasting actions_updated")
                socketio.emit('actions_updated', {'actions': actions})
        except Exception as e:
            logger.error("Config watcher error: " + str(e))

if __name__ == "__main__":
    setproctitle.setproctitle("vellum-shell-phonebridge-server")
    hostname = socket.gethostname()
    utils.init_config()

    ip = utils.get_lan_ip()
    if ip is None:
        logger.fatal("Could not determine LAN IP")
        exit(1)
    zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
    info = ServiceInfo(
        "_phonebridge._tcp.local.",
        f"{hostname}._phonebridge._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=PORT,
        properties={"name": hostname},
    )
    info = ServiceInfo(
        "_phonebridge._tcp.local.",
        f"{DEVICE_ID}._phonebridge._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=PORT,
        properties={"name": hostname, "device_id": DEVICE_ID},
    )

    zeroconf.register_service(info)
    logger.info(f"Advertising service at {ip}:{PORT} as {hostname}")
    eventlet.spawn_n(monitor_config_changes)
    try:
        socketio.run(app, host='0.0.0.0', port=PORT)
    finally:
        zeroconf.unregister_service(info)
        zeroconf.close()
