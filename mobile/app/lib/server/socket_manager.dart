import 'dart:async';
import 'package:flutter/material.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;

import '../components/IconsHelper.dart';
import '../components/action_card.dart';

class SocketManager {
  static final SocketManager _instance = SocketManager._internal();
  factory SocketManager() => _instance;
  SocketManager._internal();

  IO.Socket? _socket;
  String? _currentIp;
  String? _currentToken;

  final ValueNotifier<bool> isConnected = ValueNotifier<bool>(false);

  // Notifier that publishes action list updates pushed by the server.
  final ValueNotifier<List<CardAction>> actionsNotifier =
      ValueNotifier<List<CardAction>>([]);

  void _registerActionsUpdatedListener() {
    if (_socket == null) return;
    // Clear any existing handlers for this event to avoid duplicates.
    try {
      _socket!.off('actions_updated');
    } catch (_) {}

    _socket!.on('actions_updated', (data) {
      debugPrint('[+] Received actions_updated event from server: $data');
      try {
        final actions = (data as Map<String, dynamic>)['actions'] as List<dynamic>? ?? [];
        final cardActions = actions.map((action) {
          final actionMap = action as Map<String, dynamic>;
          return CardAction(
            id: actionMap['id'] as String,
            title: actionMap['title'] as String,
            icon: Icon(
              IconsHelper.iconMap[actionMap['icon']] ?? Icons.help_outline,
            ).icon ?? Icons.help_outline,
          );
        }).toList();
        actionsNotifier.value = cardActions;
      } catch (e) {
        debugPrint('Failed to parse actions_updated: $e');
      }
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
      if (!completer.isCompleted) completer.complete();
      isConnected.value = true;
      _registerActionsUpdatedListener();
    });
    _socket!.on('disconnect', (_) {
      isConnected.value = false;
    });
    _socket!.on('connect_error', (err) {
      if (!completer.isCompleted)
        completer.completeError(err ?? 'connect_error');
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
    isConnected.value = false;
    actionsNotifier.value = [];
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

    void onResult(data) {
      final success = (data['returncode'] as int) == 0;
      debugPrint('[+] Action "$action" completed with success: $success');
      if (!completer.isCompleted) completer.complete();
    }

    void onError(data) {
      if (!completer.isCompleted) completer.completeError(data ?? 'error');
    }

    _socket!.once('command_result', onResult);
    _socket!.once('error', onError);

    _socket!.emit('message', {
      'action': 'command',
      'command': action,
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
