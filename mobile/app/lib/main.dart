import 'package:flutter/material.dart';
import 'home_page.dart';
import 'pairing_page.dart';
import 'server/database_provider.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await DatabaseProvider.init();
  final first = await DatabaseProvider.getFirstPairedDevice();
  final isPaired = first != null;
  runApp(MyApp(isPaired: isPaired));
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
