import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

class Api {
  static Future<void> post(
    String deviceId,
    String endpoint, [
    Map<String, dynamic>? body,
  ]) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('api_token_$deviceId');
    final ip = prefs.getString('last_ip_$deviceId');

    if (token == null || ip == null) {
      throw Exception("Device not paired or IP unknown");
    }

    final res = await http.post(
      Uri.parse("http://$ip:5000$endpoint"),
      headers: {
        "Authorization": "Bearer $token",
        "Content-Type": "application/json",
      },
      body: body != null ? jsonEncode(body) : null,
    );

    if (res.statusCode != 200) {
      throw Exception("API request failed with status ${res.statusCode}");
    }
  }
}
