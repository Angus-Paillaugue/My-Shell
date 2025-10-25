import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'home_page.dart';
import 'pairing_page.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();
  final token = prefs.getString('api_token');
  final ip = prefs.getString('device_ip');
  runApp(MyApp(isPaired: token != null && ip != null));
}

class MyApp extends StatelessWidget {
  final bool isPaired;
  const MyApp({required this.isPaired, super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PhoneBridge',
      theme: ThemeData(primarySwatch: Colors.blue),
      home: isPaired ? const HomePage() : const PairingPage(),
    );
  }
}
