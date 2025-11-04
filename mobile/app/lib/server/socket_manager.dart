import 'dart:async';
import 'package:flutter/material.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;

class SocketManager {
  static final SocketManager _instance = SocketManager._internal();
  factory SocketManager() => _instance;
  SocketManager._internal();

  IO.Socket? _socket;
  String? _currentIp;
  String? _currentToken;

  final ValueNotifier<bool> isConnected = ValueNotifier<bool>(false);
  final Map<String, Function(dynamic)> _eventHandlers = {};

  void _handleMessage(dynamic data) {
    if (data is! Map<String, dynamic> || data['event'] == null) {
      debugPrint('[SocketManager] Received malformed message: $data');
      return;
    }

    final String event = data['event'];
    final payload = data['payload'];

    if (_eventHandlers.containsKey(event)) {
      debugPrint('[SocketManager] Dispatching event "$event"');
      _eventHandlers[event]!(payload);
    } else {
      debugPrint('[SocketManager] No handler for event "$event"');
    }
  }

  void on(String event, Function(dynamic) handler) {
    debugPrint('[SocketManager] Subscribing to event: $event');
    _eventHandlers[event] = handler;
  }

  void off(String event) {
    debugPrint('[SocketManager] Unsubscribing from event: $event');
    _eventHandlers.remove(event);
  }

  void emit(String event, [dynamic data]) {
    debugPrint('[SocketManager] Emitting event: $event with data: $data');
    _socket?.emit('message', {
      'action': event,
      'payload': data,
      'api_key': _currentToken,
    });
  }

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
      debugPrint('[SocketManager] Connected to $uri');
      if (!completer.isCompleted) completer.complete();

      // Force notification to listeners
      isConnected.value = false; // Temporarily set to false
      isConnected.value = true; // Then set to true to ensure notification
    });

    _socket!.on('disconnect', (_) {
      debugPrint('[SocketManager] Disconnected from $uri');
      isConnected.value = false; // Notify listeners of the disconnection
    });

    _socket!.on('connect_error', (err) {
      debugPrint('[SocketManager] Connection error to $uri: $err');
      if (!completer.isCompleted) {
        completer.completeError(err ?? 'connect_error');
      }
      isConnected.value = false; // Notify listeners of the error
    });
    _socket!.on('message', _handleMessage);
    _socket!.connect();

    return completer.future.timeout(timeout);
  }

  void disconnect() {
    if (_socket != null) {
      try {
        _socket!.off('connect');
        _socket!.off('disconnect');
        _socket!.off('connect_error');
        _socket!.off('message');
        _socket!.clearListeners(); // Clear all listeners
        _socket!.disconnect();
        _socket!.destroy();
      } catch (_) {}
    }
    _socket = null;
    _currentIp = null;
    _currentToken = null;
    isConnected.value = false;
  }

  Future<String> pair() async {
    if (_socket == null) throw Exception('Socket not connected');
    final completer = Completer<String>();

    void onPaired(data) {
      _socket!.off('paired', onPaired);
      if (!completer.isCompleted) {
        completer.complete(data['session_id'] as String);
      }
    }

    void onError(data) {
      _socket!.off('error', onError);
      if (!completer.isCompleted) {
        completer.completeError(data ?? 'error');
      }
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
      _currentToken = data['api_token'] as String;
      completer.complete(data['api_token'] as String);
    }

    void onError(data) {
      _socket!.off('error', onError);
      if (!completer.isCompleted) completer.completeError(data['error'] ?? 'error');
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

}
