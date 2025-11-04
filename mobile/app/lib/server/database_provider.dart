import 'dart:async';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

class DatabaseProvider {
  static Database? _db;

  static Future<void> init() async {
    if (_db != null) return;
    final dbPath = await getDatabasesPath();
    final path = join(dbPath, 'phonebridge.db');
    _db = await openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE paired_devices(
            device_id TEXT PRIMARY KEY,
            name TEXT,
            last_ip TEXT,
            api_token TEXT
          )
        ''');
      },
    );
  }

  static Future<Map<String, dynamic>?> getFirstPairedDevice() async {
    await init();
    final res = await _db!.query(
      'paired_devices',
      where: 'api_token IS NOT NULL AND last_ip IS NOT NULL',
      limit: 1,
    );
    return res.isEmpty ? null : res.first;
  }

  static Future<List<Map<String, dynamic>>> getAllPairedDevices() async {
    await init();
    return await _db!.query('paired_devices');
  }

  static Future<Map<String, dynamic>?> getDevice(String deviceId) async {
    await init();
    final res = await _db!.query(
      'paired_devices',
      where: 'device_id = ?',
      whereArgs: [deviceId],
      limit: 1,
    );
    return res.isEmpty ? null : res.first;
  }

  static Future<void> savePairing({
    required String deviceId,
    required String name,
    required String ip,
    String? token,
  }) async {
    await init();
    await _db!.insert('paired_devices', {
      'device_id': deviceId,
      'name': name,
      'last_ip': ip,
      'api_token': token,
    }, conflictAlgorithm: ConflictAlgorithm.replace);
  }

  static Future<void> updateLastIp(String deviceId, String ip) async {
    await init();
    await _db!.update(
      'paired_devices',
      {'last_ip': ip},
      where: 'device_id = ?',
      whereArgs: [deviceId],
    );
  }

  static Future<void> saveApiToken(String deviceId, String token) async {
    await init();
    await _db!.update(
      'paired_devices',
      {'api_token': token},
      where: 'device_id = ?',
      whereArgs: [deviceId],
    );
  }
}
