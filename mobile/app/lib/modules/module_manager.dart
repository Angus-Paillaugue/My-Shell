import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:vellum_shell_sync/modules/module_interface.dart';
import 'package:vellum_shell_sync/server/socket_manager.dart';
// Modules
import 'package:vellum_shell_sync/modules/actions/actions_module.dart';
import 'package:vellum_shell_sync/modules/file_system/file_system_module.dart';

class ModuleManager {
  static final ModuleManager _instance = ModuleManager._internal();
  factory ModuleManager() => _instance;

  late final List<VellumModule> _allModules;
  final ValueNotifier<List<VellumModule>> activeModules = ValueNotifier([]);
  final SocketManager _socketManager = SocketManager();

  ModuleManager._internal() {
    _allModules = [
      ActionsModule(),
      FileSystemModule(),
      // Future modules will be added here
    ];
  }

  List<VellumModule> get allModules => _allModules;

  Future<void> init() async {
    final prefs = await SharedPreferences.getInstance();
    List<VellumModule> newActiveModules = [];

    for (final module in _allModules) {
      final bool isCurrentlyActive = activeModules.value.contains(module);
      final bool shouldBeActive =
          prefs.getBool('module_${module.id}_active') ?? true;

      if (shouldBeActive) {
        if (!isCurrentlyActive) {
          module.init(_socketManager); // Init if not already active
        }
        newActiveModules.add(module);
      } else {
        if (isCurrentlyActive) {
          module.dispose(); // Dispose if it shouldn't be active
        }
      }
    }

    // Sort active modules to match the order in _allModules
    newActiveModules.sort(
      (a, b) => _allModules.indexOf(a).compareTo(_allModules.indexOf(b)),
    );

    activeModules.value = newActiveModules;
  }

  Future<void> setModuleActive(String moduleId, bool isActive) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('module_${moduleId}_active', isActive);

    final module = _allModules.firstWhere((m) => m.id == moduleId);
    if (isActive && !activeModules.value.contains(module)) {
      module.init(_socketManager);
      activeModules.value = [...activeModules.value, module];
    } else if (!isActive && activeModules.value.contains(module)) {
      // module.dispose();
      activeModules.value = activeModules.value
          .where((m) => m != module)
          .toList();
    }

    // Sort active modules to match the order in _allModules
    activeModules.value = activeModules.value
      ..sort(
        (a, b) => _allModules.indexOf(a).compareTo(_allModules.indexOf(b)),
      );
  }

  bool isModuleActive(String moduleId) {
    return activeModules.value.any((m) => m.id == moduleId);
  }

  void dispose() {
    for (final module in activeModules.value) {
      module.dispose();
    }
    activeModules.value = [];
  }
}
