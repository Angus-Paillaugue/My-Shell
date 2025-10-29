import 'package:flutter/material.dart';
import 'home_page.dart';
import 'pairing_page.dart';
import 'server/database_provider.dart';
import 'modules/module_manager.dart';

void main() async {
  FlutterError.onError = (FlutterErrorDetails details) {
    debugPrint('Flutter Error: ${details.exception}');
  };
  WidgetsFlutterBinding.ensureInitialized();
  await DatabaseProvider.init();
  await ModuleManager().init();
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
      title: 'Vellum Shell Sync',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.purple,
          brightness: MediaQuery.of(context).platformBrightness,
        ),
      ),
      home: isPaired ? const HomePage() : const PairingPage(),
    );
  }
}
