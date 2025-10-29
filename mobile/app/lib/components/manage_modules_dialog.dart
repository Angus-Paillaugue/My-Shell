import 'package:flutter/material.dart';
import 'package:vellum_shell_sync/modules/module_manager.dart';

class ManageModulesDialog extends StatefulWidget {
  const ManageModulesDialog({super.key});

  @override
  State<ManageModulesDialog> createState() => _ManageModulesDialogState();
}

class _ManageModulesDialogState extends State<ManageModulesDialog> {
  final ModuleManager _moduleManager = ModuleManager();

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Manage Modules'),
      content: SizedBox(
        width: double.maxFinite,
        child: ValueListenableBuilder(
          valueListenable: _moduleManager.activeModules, // Listen for changes
          builder: (context, activeModules, child) {
            return ListView.builder(
              shrinkWrap: true,
              itemCount: _moduleManager.allModules.length,
              itemBuilder: (context, index) {
                final module = _moduleManager.allModules[index];
                return SwitchListTile(
                  title: Text(module.name),
                  subtitle: Text(module.description),
                  secondary: Icon(module.icon),
                  value: _moduleManager.isModuleActive(module.id),
                  onChanged: (bool value) async {
                    _moduleManager.setModuleActive(module.id, value);
                  },
                );
              },
            );
          },
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Close'),
        ),
      ],
    );
  }
}
