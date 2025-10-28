import 'package:flutter/material.dart';
import 'dart:async';
import 'pairing_page.dart';
import 'server/socket_manager.dart';
import 'server/database_provider.dart';
import 'components/action_card.dart';

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
  late List<CardAction> actions = [];
  final SocketManager _socket = SocketManager();
  late VoidCallback _connListener;
  late VoidCallback _actionsListener;

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
    _actionsListener = () {
      if (!mounted) return;
      // Map incoming actions to include the local onPressed callback.
      setState(() {
        actions = _socket.actionsNotifier.value.map((a) {
          return CardAction(
            id: a.id,
            title: a.title,
            icon: a.icon,
            onPressed: actionCallback,
          );
        }).toList();
      });
    };
    _socket.actionsNotifier.addListener(_actionsListener);
    _loadDevice();
  }

  Future<void> _loadDevice() async {
    final row = await DatabaseProvider.getFirstPairedDevice();
    if (row != null) {
      final id = row['device_id'] as String;
      final name = (row['name'] as String?) ?? id;
      final ip = row['last_ip'] as String?;
      final token = row['api_token'] as String?;

      setState(() {
        deviceId = id;
        deviceName = name;
        deviceIp = ip;
        apiToken = token;
      });

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
    _socket.actionsNotifier.removeListener(_actionsListener);
    _online = false;
    _socket.disconnect();
    super.dispose();
  }

  Future<void> _disconnect() async {
    if (deviceId != null) {
      await DatabaseProvider.removeLastIp(deviceId!);
    }
    _socket.disconnect();
    Navigator.pushReplacement(
      context,
      MaterialPageRoute(builder: (_) => const PairingPage()),
    );
  }

  Future<void> actionCallback(String id) async {
    try {
      await _ensureConnected();
      await _socket.sendAction(id, token: apiToken);
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

  @override
  Widget build(BuildContext context) {
    if (deviceId == null) {
      return const Center(child: CircularProgressIndicator());
    }

    return Scaffold(
      appBar: AppBar(
        title: Text("${_online ? "Connected" : "Connecting"} to $deviceName"),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: _disconnect,
            tooltip: "Disconnect",
          ),
        ],
      ),
      body: !_online
          ? const Center(child: CircularProgressIndicator())
          : GridView.builder(
              padding: const EdgeInsets.all(12.0),
              shrinkWrap: true,
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                mainAxisSpacing: 12.0,
                crossAxisSpacing: 12.0,
                childAspectRatio: 1.0,
              ),
              itemCount: actions.length,
              itemBuilder: (BuildContext context, int index) {
                final action = actions[index];
                return ActionCard(action);
              },
            ),
    );
  }
}
