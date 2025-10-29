import 'package:flutter/material.dart';
import 'package:vellum_shell_sync/server/socket_manager.dart';

abstract class VellumModule {
  /// A unique identifier for the module.
  String get id;

  /// The display name of the module.
  String get name;

  /// A brief description of what the module does.
  String get description;

  /// The icon representing the module in the management UI.
  IconData get icon;

  /// Builds the widget that represents this module's UI.
  Widget buildWidget(BuildContext context);

  /// Called when the module is initialized.
  void init(SocketManager socketManager) {}

  /// Called when the module is disposed.
  void dispose() {}
}
