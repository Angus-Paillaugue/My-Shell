import 'package:flutter/material.dart';
import 'package:vellum_shell_sync/modules/clipboard/clipboard_widget.dart';
import 'package:vellum_shell_sync/modules/module_interface.dart';
import 'package:vellum_shell_sync/server/socket_manager.dart';
import 'package:clipboard/clipboard.dart';

class ClipboardModule extends VellumModule {
  SocketManager? _socketManager;
  late ValueNotifier<List<String>> remoteClipboard;
  late ValueNotifier<String> localClipboard;
  late ValueNotifier<bool> isFetchingRemote;

  @override
  String get id => 'clipboard';

  @override
  String get name => 'Clipboard';

  @override
  String get description =>
      'Sync clipboard contents between your devices seamlessly.';

  @override
  IconData get icon => Icons.copy;

  @override
  void init(SocketManager socketManager) {
    _socketManager = socketManager;
    remoteClipboard = ValueNotifier([]);
    isFetchingRemote = ValueNotifier(false);
    localClipboard = ValueNotifier('');
    _socketManager?.off('clipboard_result'); // Remove any existing listener
    _socketManager?.on('clipboard_result', _onResult); // Add listener
    FlutterClipboard.addListener(_onLocalClipboardChange);
    FlutterClipboard.startMonitoring(interval: Duration(milliseconds: 500));
  }

  @override
  Widget buildWidget(BuildContext context) {
    return ClipboardWidget(module: this);
  }

  @override
  void dispose() {
    super.dispose();
    _socketManager?.disconnect();
    isFetchingRemote.dispose();
    remoteClipboard.dispose();
    localClipboard.dispose();
    FlutterClipboard.stopMonitoring();
    FlutterClipboard.removeListener(_onLocalClipboardChange);
  }

  void _onLocalClipboardChange(EnhancedClipboardData data) {
    localClipboard.value = data.text ?? '';
    debugPrint('[ClipboardModule] Local clipboard changed: ${localClipboard.value}');
  }

  Future<void> copyToClipboard(String content) async {
    try {
      await FlutterClipboard.copy(content);
    } on ClipboardException catch (e) {
      debugPrint('Copy failed: ${e.message}');
    }
  }

  void _onResult(dynamic data) {
    debugPrint(data.runtimeType.toString());
    isFetchingRemote.value = false;

    try {
      // Validate that 'data' is a Map and contains the expected keys
      if (data is Map<String, dynamic>) {
        final content = data['content'];
        final error = data['error'] as String?;
        final status = data['status'] as String?;

        if (error != null) {
          debugPrint('Error retrieving clipboard: $error');
          return;
        }

        if (content is List) {
          // Ensure content is a list of strings
          remoteClipboard.value = content.map((e) => e.toString()).toList();
          return;
        }

        if (status != null) {
          debugPrint('Text copied to remote clipboard: $status');
        }
      } else {
        debugPrint('Unexpected data format: $data');
      }
    } catch (e) {
      debugPrint('Error processing clipboard result: $e');
    }
  }

  Future<void> getRemoteClipboard() async {
    isFetchingRemote.value = true;
    try {
      _socketManager?.emit('clipboard', {'action': 'get'});
    } on ClipboardException catch (e) {
      debugPrint('Get remote failed: ${e.message}');
    }
  }

  void sendClipboardContent(String content) {
    try {
      _socketManager?.emit('clipboard', {
        'action': 'set',
        'content': content,
      });
    } on ClipboardException catch (e) {
      debugPrint('[ClipboardModule] Send clipboard failed: ${e.message}');
    }
  }

  Future<void> getLocalClipboard() async {
    try {
      localClipboard.value = await FlutterClipboard.paste();
      debugPrint('[ClipboardModule] Local clipboard fetched: ${localClipboard.value}');
    } on ClipboardException catch (e) {
      debugPrint('[ClipboardModule] Get local clipboard failed: ${e.message}');
    }
  }
}
