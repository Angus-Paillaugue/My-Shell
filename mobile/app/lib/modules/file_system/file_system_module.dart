import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:vellum_shell_sync/modules/module_interface.dart';
import 'package:vellum_shell_sync/server/socket_manager.dart';
import 'package:vellum_shell_sync/modules/file_system/file_system_widget.dart';
import 'package:path/path.dart' as p;

class FileSystemModule extends ChangeNotifier implements VellumModule {
  SocketManager? _socketManager;

  late ValueNotifier<String> currentPathNotifier;
  late ValueNotifier<List<FileSystemEntry>> entriesNotifier;
  late ValueNotifier<bool> isNavigatingNotifier;
  late ValueNotifier<FileContent?> fileContentNotifier;

  @override
  String get id => 'file_system';

  @override
  String get name => 'File System';

  @override
  String get description => 'Explore the remote file system.';

  @override
  IconData get icon => Icons.folder;

  @override
  void init(SocketManager socketManager) {
    // Re-initialize the notifiers
    currentPathNotifier = ValueNotifier('~');
    entriesNotifier = ValueNotifier([]);
    isNavigatingNotifier = ValueNotifier(false);
    fileContentNotifier = ValueNotifier(null);

    isNavigatingNotifier.value = false;
    _socketManager = socketManager;
    _socketManager?.off('file_system_result'); // Remove any existing listener
    _socketManager?.on('file_system_result', _fileSystemResult); // Add listener
    fetchPath();
  }

  void _fileSystemResult(data) {
    debugPrint('[FileSystemModule] Received file_system_result event');
    isNavigatingNotifier.value = false;
    if (data['items'] != null) {
      final entries = (data['items'] as List<dynamic>).map((entry) {
        final entryName = entry['name'] as String;
        // Use path package for robust joining.
        // It correctly handles cases like currentPath = '/'
        final absolutePath = p.join(currentPathNotifier.value, entryName);

        return FileSystemEntry(
          name: entryName,
          absPath: absolutePath,
          isDirectory: entry['is_dir'] as bool,
          size: (entry['size'] as num).toDouble(),
          modified: (entry['modified'] as num).toDouble(),
        );
      }).toList();
      entries.sort((FileSystemEntry a, FileSystemEntry b) {
        // Directories first
        if (a.isDirectory && !b.isDirectory) return -1;
        if (!a.isDirectory && b.isDirectory) return 1;
        // Then by name
        return a.name.toLowerCase().compareTo(b.name.toLowerCase());
      });
      entriesNotifier.value = entries;
    } else if (data['content'] != null) {
      debugPrint('[FileSystemModule] Received file content');
      final path = data['path'] as String;
      final content = data['content'] as Uint8List;
      debugPrint("[FileSystemModule] Received content for path $path with ${content.length} bytes");
      // The content is expected to be base64 encoded
      fileContentNotifier.value = FileContent(
        path: path,
        bytes: content,
      );
    } else {
      final errorMsg = data['error'] as String;
      debugPrint('[FileSystemModule] Error: $errorMsg');
    }
  }

  Future<void> fetchPath() async {
    isNavigatingNotifier.value = true;
    _socketManager?.emit('file_system', {'path': currentPathNotifier.value, 'action': 'list'});
  }

  Future<void> navigateTo(String path) async {
    currentPathNotifier.value = path;
    await fetchPath();
  }

  Future<void> fetchFileContent(String path) async {
    isNavigatingNotifier.value = true;
    fileContentNotifier.value = null; // Clear previous content
    _socketManager?.emit('file_system', {'path': path, 'action': 'send'});
  }

  Future<bool> requestPermission(Permission permission) async {
    if (await permission.isGranted) {
      return true;
    } else {
      var result = await permission.request();
      if (result == PermissionStatus.granted) {
        return true;
      }
    }
    return false;
  }


  Future<String?> downloadFile(String path) async {
    notifyListeners();

    try {
      var permissionOk = await requestPermission(Permission.manageExternalStorage);
      if (!permissionOk) {
        debugPrint('[FileSystemModule] Storage permission denied');
        return null;
      }

      final Directory? downloadsDir = await getDownloadsDirectory();
      if (downloadsDir == null) {
        return null;
      }

      // Fetch file content first
      debugPrint("[FileSystemModule] Requesting file content for download: $path");
      _socketManager?.emit('file_system', {'path': path, 'action': 'send'});

      // Wait for the content to be received
      await fileContentNotifier.toFuture((value) => value?.path == path);

      final fileContent = fileContentNotifier.value;
      debugPrint(fileContent.toString());
      if (fileContent == null) {
        debugPrint(
          '[FileSystemModule] Failed to receive file content for download',
        );
        return null;
      }

      final fileName = p.basename(path);
      final filePath = '${downloadsDir.path}/$fileName';
      debugPrint("[FileSystemModule] Saving file to $filePath");
      final fileOnDisk = File(filePath);
      await fileOnDisk.writeAsBytes(fileContent.bytes);

      return filePath;
    } catch (e) {
      debugPrint('Error downloading file: $e');
      return null;
    } finally {
      notifyListeners();
    }
  }

  @override
  Widget buildWidget(BuildContext context) {
    return FileSystemWidget(module: this);
  }

  @override
  void dispose() {
    super.dispose();
    _socketManager?.off('file_system_result');
    currentPathNotifier.dispose();
    entriesNotifier.dispose();
    isNavigatingNotifier.dispose();
    fileContentNotifier.dispose();
  }
}

class FileContent {
  final String path;
  final Uint8List bytes;

  FileContent({required this.path, required this.bytes});
}

extension<T> on ValueNotifier<T> {
  Future<T> toFuture(bool Function(T value) condition) {
    final completer = Completer<T>();
    void listener() {
      if (condition(value)) {
        removeListener(listener);
        completer.complete(value);
      }
    }

    addListener(listener);
    return completer.future;
  }
}

class FileSystemEntry {
  final String name;
  final String absPath;
  final bool isDirectory;
  final double size;
  final double modified;

  FileSystemEntry({
    required this.name,
    required this.absPath,
    required this.isDirectory,
    required this.size,
    required this.modified
  });
}
