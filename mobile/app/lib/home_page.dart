import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:async';
import '../pairing_page.dart';
import 'server/socket_manager.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  String? deviceName;
  String? deviceId;
  String? deviceIp;
  String? apiToken;
  bool _online = false;

  final SocketManager _socket = SocketManager();
  late VoidCallback _connListener;

  @override
  void initState() {
    super.initState();
    _connListener = () {
      if (!mounted) return;
      setState(() {
        _online = _socket.isConnected.value;
      });
    };
    _socket.isConnected.addListener(_connListener);
    _loadDevice();
  }

  Future<void> _loadDevice() async {
    final prefs = await SharedPreferences.getInstance();

    // Find any paired device
    final keys = prefs.getKeys();
    String? device_id;
    for (var key in keys) {
      if (key.startsWith('api_token_')) {
        device_id = key.replaceFirst('api_token_', '');
        break;
      }
    }

    if (device_id != null) {
      final name = prefs.getString('device_name_$device_id') ?? device_id;
      final ip = prefs.getString('last_ip_$device_id');
      final token = prefs.getString('api_token_$device_id');

      setState(() {
        deviceId = device_id;
        deviceName = name;
        deviceIp = ip;
        apiToken = token;
      });

      // Try to connect the socket (ignore failure; status checks will retry)
      if (deviceIp != null) {
        try {
          await _socket.connect(deviceIp!, token: apiToken);
        } catch (_) {}
      }
    }
  }

  @override
  void dispose() {
    _socket.isConnected.removeListener(_connListener);
    _online = false;
    _socket.disconnect();
    super.dispose();
  }

  Future<void> _disconnect() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('last_ip_$deviceId');
    _socket.disconnect();
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => const PairingPage()),
    );
  }

  Future<void> action(String name) async {
    try {
      switch (name) {
        case "lock":
          await _ensureConnected();
          await _socket.sendAction("lock", token: apiToken);
          break;
        case "unlock":
          await _ensureConnected();
          await _socket.sendAction("unlock", token: apiToken);
          break;
        case "notify":
          await _ensureConnected();
          await _socket.sendAction(
            "notify",
            token: apiToken,
            payload: {
              "title": "Hello from Phone",
              "text": "This is a test notification",
            },
          );
          break;
        default:
          throw Exception("Unknown action: $name");
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text("Action failed: $e")));
      }
    }
  }

  Future<void> _ensureConnected() async {
    if (deviceIp == null) throw Exception("Device IP unknown");
    try {
      await _socket.connect(deviceIp!, token: apiToken);
    } catch (e) {
      // connect may throw, let caller handle subsequent sendAction errors
    }
  }

  Widget _actionTile({
    required IconData icon,
    required String label,
    required VoidCallback onPressed,
  }) {
    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.all(16),
        backgroundColor: Theme.of(context).colorScheme.primary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(icon, size: 36, color: Theme.of(context).colorScheme.onPrimary),
          const SizedBox(height: 8),
          Text(
            label,
            textAlign: TextAlign.center,
            style: TextStyle(color: Theme.of(context).colorScheme.onPrimary),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (deviceId == null)
      return const Center(child: CircularProgressIndicator());

    return Scaffold(
      appBar: AppBar(
        title: Text("Connected to $deviceName"),
        actions: [
          // status indicator: small green/red dot with tooltip (now real)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12.0),
            child: Tooltip(
              message: _online ? 'Online' : 'Offline',
              child: Icon(
                Icons.circle,
                color: _online ? Colors.green : Colors.red,
                size: 14,
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: _disconnect,
            tooltip: "Disconnect",
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: GridView.count(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          crossAxisCount: 2,
          crossAxisSpacing: 12,
          mainAxisSpacing: 12,
          childAspectRatio: 1,
          children: [
            _actionTile(
              icon: Icons.lock,
              label: "Lock",
              onPressed: () => action("lock"),
            ),
            _actionTile(
              icon: Icons.lock_open,
              label: "Unlock",
              onPressed: () => action("unlock"),
            ),
            _actionTile(
              icon: Icons.notifications,
              label: "Notify",
              onPressed: () => action("notify"),
            ),
          ],
        ),
      ),
    );
  }
}
