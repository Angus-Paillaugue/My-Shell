import 'package:flutter/material.dart';
import 'package:multicast_dns/multicast_dns.dart';
import 'dart:async';
import 'home_page.dart';
import 'server/socket_manager.dart';
import 'server/database_provider.dart';

class PairingPage extends StatefulWidget {
  const PairingPage({super.key});

  @override
  State<PairingPage> createState() => _PairingPageState();
}

class _PairingPageState extends State<PairingPage> {
  List<_DiscoveredDevice> devices = [];
  bool scanning = false;
  late MDnsClient _mdns;
  Map<String, _DiscoveredDevice> pairedDevices = {};

  @override
  void initState() {
    super.initState();
    _loadPairedDevices();
    _startDiscovery();
  }

  Future<void> _loadPairedDevices() async {
    final rows = await DatabaseProvider.getAllPairedDevices();
    for (var row in rows) {
      final deviceId = row['device_id'] as String;
      final ip = row['last_ip'] as String?;
      final name = (row['name'] as String?) ?? deviceId;
      if (ip != null) {
        pairedDevices[deviceId] = _DiscoveredDevice(
          name: name,
          ip: ip,
          port: 5000,
          deviceId: deviceId,
        );
      }
    }
  }

  Future<void> _startDiscovery() async {
    debugPrint('[mDNS] Starting mDNS discovery...');
    setState(() => scanning = true);
    devices.clear();

    try {
      _mdns = MDnsClient();
      await _mdns.start(
        onError: (e) {
          debugPrint('[mDNS] mDNS Error: $e');
          if (context.mounted) {
            ScaffoldMessenger.of(
              context,
            ).showSnackBar(SnackBar(content: Text('mDNS Error: $e')));
          }
        },
      );
      debugPrint('[mDNS] mDNS started successfully.');

      await for (final PtrResourceRecord ptr in _mdns.lookup<PtrResourceRecord>(
        ResourceRecordQuery.serverPointer('_phonebridge._tcp.local'),
      )) {
        debugPrint('[mDNS] Discovered PTR: ${ptr.domainName}');
        await for (final SrvResourceRecord srv
            in _mdns.lookup<SrvResourceRecord>(
              ResourceRecordQuery.service(ptr.domainName),
            )) {
          debugPrint('[mDNS] Discovered SRV: ${srv.target}:${srv.port}');
          await for (final IPAddressResourceRecord ip
              in _mdns.lookup<IPAddressResourceRecord>(
                ResourceRecordQuery.addressIPv4(srv.target),
              )) {
            debugPrint('[mDNS] Discovered IP: ${ip.address.address}');
            String deviceId = '';
            String name = ptr.domainName.split('._').first;
            await for (final TxtResourceRecord txt
                in _mdns.lookup<TxtResourceRecord>(
                  ResourceRecordQuery.text(ptr.domainName),
                )) {
              debugPrint('[mDNS] Discovered TXT: ${txt.text}');
              List<String> entries = txt.text.split('\n');

              for (var item in entries) {
                if (item.startsWith('device_id=')) {
                  deviceId = item.replaceFirst('device_id=', '');
                }
                if (item.startsWith('name=')) {
                  name = item.replaceFirst('name=', '');
                }
              }
            }

            final device = _DiscoveredDevice(
              name: name,
              ip: ip.address.address,
              port: srv.port,
              deviceId: deviceId,
            );

            if (!devices.any((d) => d.deviceId == device.deviceId)) {
              setState(() => devices.add(device));
            }
          }
        }
      }
    } catch (e) {
      debugPrint('[mDNS] Discovery error: $e');
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Discovery error: $e')));
      }
    } finally {
      _mdns.stop();
      debugPrint('[mDNS] mDNS stopped.');
      setState(() => scanning = false);
    }
  }

  Future<void> _pairDevice(_DiscoveredDevice device) async {
    try {
      final existing = await DatabaseProvider.getDevice(device.deviceId);
      if (existing != null && existing['api_token'] != null) {
        await DatabaseProvider.updateLastIp(device.deviceId, device.ip);
        if (context.mounted) {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(builder: (_) => const HomePage()),
          );
        }
        return;
      }

      final socket = SocketManager();
      await socket.connect(device.ip);

      final sessionId = await socket.pair();

      final code = await _showCodeDialog(context, device, sessionId);
      if (code == null) return;

      final apiToken = await socket.verifyPair(sessionId, code);

      await DatabaseProvider.savePairing(
        deviceId: device.deviceId,
        name: device.name,
        ip: device.ip,
        token: apiToken,
      );

      if (context.mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => const HomePage()),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('Error: $e')));
      }
    }
  }

  Future<String?> _showCodeDialog(
    BuildContext context,
    _DiscoveredDevice device,
    String sessionId,
  ) async {
    final controller = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('Enter Code for ${device.name}'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          maxLength: 6,
          decoration: const InputDecoration(labelText: '6-digit code'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, controller.text),
            child: const Text('Verify'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Pair a Laptop'),
        actions: scanning
            ? null
            : [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: _startDiscovery,
          ),
        ],
      ),
      body: scanning
          ? const Center(child: CircularProgressIndicator())
          : devices.isEmpty
          ? const Center(child: Text('No devices found'))
          : ListView.builder(
              itemCount: devices.length,
              itemBuilder: (context, index) {
                final d = devices[index];
                return ListTile(
                  title: Text(d.name),
                  subtitle: Text('${d.ip}:${d.port}'),
                  trailing: ElevatedButton(
                    onPressed: () => _pairDevice(d),
                    child: const Text('Pair'),
                  ),
                );
              },
            ),
    );
  }
}

class _DiscoveredDevice {
  final String name;
  final String ip;
  final int port;
  final String deviceId;
  _DiscoveredDevice({
    required this.name,
    required this.ip,
    required this.port,
    required this.deviceId,
  });
}
