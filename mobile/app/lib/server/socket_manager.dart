import 'dart:async';
import 'package:flutter/material.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;

/// Simple Socket.IO client wrapper for the PhoneBridge protocol.
class SocketManager {
  static final SocketManager _instance = SocketManager._internal();
  factory SocketManager() => _instance;
  SocketManager._internal();

  IO.Socket? _socket;
  String? _currentIp;
  String? _currentToken;

  // NEW: exposes connection state to UI
  final ValueNotifier<bool> isConnected = ValueNotifier<bool>(false);

  Future<void> connect(
    String ip, {
    String? token,
    Duration timeout = const Duration(seconds: 5),
  }) async {
    if (_socket != null && _currentIp == ip && _socket!.connected) {
      _currentToken = token ?? _currentToken;
      isConnected.value = true;
      return;
    }
    disconnect();

    _currentIp = ip;
    _currentToken = token;

    final uri = 'http://$ip:5000';

    _socket = IO.io(
      uri,
      IO.OptionBuilder()
          .setTransports(['websocket'])
          .disableAutoConnect()
          .build(),
    );

    final completer = Completer<void>();
    _socket!.on('connect', (_) {
      if (!completer.isCompleted) completer.complete();
      // update connection state
      isConnected.value = true;
    });
    _socket!.on('disconnect', (_) {
      // update connection state
      isConnected.value = false;
    });
    _socket!.on('connect_error', (err) {
      if (!completer.isCompleted)
        completer.completeError(err ?? 'connect_error');
      // ensure state updated
      isConnected.value = false;
    });
    _socket!.connect();

    return completer.future.timeout(timeout);
  }

  void disconnect() {
    if (_socket != null) {
      try {
        _socket!.disconnect();
        _socket!.destroy();
      } catch (_) {}
    }
    _socket = null;
    _currentIp = null;
    _currentToken = null;
    // update connection state
    isConnected.value = false;
  }

  Future<String> pair() async {
    if (_socket == null) throw Exception('Socket not connected');
    final completer = Completer<String>();

    void onPaired(data) {
      _socket!.off('paired', onPaired);
      completer.complete(data['session_id'] as String);
    }

    void onError(data) {
      _socket!.off('error', onError);
      if (!completer.isCompleted) completer.completeError(data ?? 'error');
    }

    _socket!.on('paired', onPaired);
    _socket!.on('error', onError);

    _socket!.emit('message', {
      'action': 'pair',
      'api_key': null,
      'payload': {},
    });

    return completer.future.timeout(const Duration(seconds: 10));
  }

  Future<String> verifyPair(String sessionId, String code) async {
    if (_socket == null) throw Exception('Socket not connected');
    final completer = Completer<String>();

    void onVerified(data) {
      _socket!.off('verified', onVerified);
      completer.complete(data['api_token'] as String);
    }

    void onError(data) {
      _socket!.off('error', onError);
      if (!completer.isCompleted) completer.completeError(data ?? 'error');
    }

    _socket!.on('verified', onVerified);
    _socket!.on('error', onError);

    _socket!.emit('message', {
      'action': 'verify_pair',
      'api_key': null,
      'payload': {'session_id': sessionId, 'code': code},
    });

    return completer.future.timeout(const Duration(seconds: 10));
  }

  Future<void> sendAction(
    String action, {
    Map<String, dynamic>? payload,
    String? token,
  }) async {
    if (_socket == null) {
      throw Exception('Socket not connected');
    }

    final completer = Completer<void>();

    void onStatus(data) {
      if (!completer.isCompleted) completer.complete();
    }

    void onError(data) {
      if (!completer.isCompleted) completer.completeError(data ?? 'error');
    }

    _socket!.once('status', onStatus);
    _socket!.once('error', onError);

    _socket!.emit('message', {
      'action': action,
      'api_key': token ?? _currentToken,
      'payload': payload ?? {},
    });

    return completer.future.timeout(
      const Duration(seconds: 5),
      onTimeout: () {
        // If no response, still resolve to allow the app to continue but throw if needed.
        if (!completer.isCompleted) completer.complete();
        debugPrint('[!] Action "$action" timed out');
        return;
      },
    );
  }
}
