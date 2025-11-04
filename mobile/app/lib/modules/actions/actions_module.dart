import 'dart:async';

import 'package:flutter/material.dart';
import 'package:vellum_shell_sync/components/IconsHelper.dart';
import 'action_card.dart';
import 'package:vellum_shell_sync/modules/actions/actions_widget.dart';
import 'package:vellum_shell_sync/modules/module_interface.dart';
import 'package:vellum_shell_sync/server/socket_manager.dart';

class ActionsModule extends VellumModule {
  SocketManager? _socketManager;
  var isRefreshing = false;
  final ValueNotifier<List<CardAction>> actionsNotifier = ValueNotifier([]);
  final Map<String, Completer<void>> _actionCompleters = {};

  @override
  String get id => 'actions';

  @override
  String get name => 'Action';

  @override
  String get description =>
      'Displays a grid of executable actions from the server.';

  @override
  IconData get icon => Icons.grid_view_rounded;

  @override
  void init(SocketManager socketManager) {
    _socketManager = socketManager;
    _socketManager?.off('actions_updated');
    _socketManager?.off('command_result');
    _socketManager?.on('actions_updated', _onActionsUpdated);
    _socketManager?.on('command_result', _onActionResult);
    fetchActions();
  }

  void fetchActions() {
    isRefreshing = true;
    _socketManager?.emit('get_actions');
  }

  void _onActionsUpdated(dynamic data) {
    debugPrint('[ActionsModule] Received actions_updated event');
    isRefreshing = false;
    try {
      final actions =
          (data as Map<String, dynamic>)['actions'] as List<dynamic>? ?? [];
      final cardActions = actions.map((action) {
        final actionMap = action as Map<String, dynamic>;
        return CardAction(
          id: actionMap['id'] as String,
          title: actionMap['title'] as String,
          icon:
              Icon(
                IconsHelper.iconMap[actionMap['icon']] ?? Icons.help_outline,
              ).icon ??
              Icons.help_outline,
        );
      }).toList();
      actionsNotifier.value = cardActions;
    } catch (e) {
      debugPrint('[ActionsModule] Failed to parse actions_updated: $e');
    }
  }

  void _onActionResult(dynamic data) {
    final actionId = data['action_id'] as String?;
    final error = data['error'] as String?;

    if (actionId != null && _actionCompleters.containsKey(actionId)) {
      final completer = _actionCompleters.remove(actionId)!;
      if (error != null) {
        completer.completeError(error);
      } else {
        completer.complete();
      }
    }
  }

  Future<void> sendAction(String actionId) async {
    final completer = Completer<void>();
    _actionCompleters[actionId] = completer;

    // Update the action to set isRunning to true
    final currentActions = actionsNotifier.value;
    final updatedActions = currentActions.map((action) {
      if (action.id == actionId) {
        return action.copyWith(isRunning: true);
      }
      return action;
    }).toList();
    actionsNotifier.value = updatedActions;

    _socketManager?.emit('command', {'command': actionId});

    try {
      await completer.future.timeout(const Duration(seconds: 10));
    } catch (e) {
      rethrow; // Rethrow to be caught by the UI
    } finally {
      // Update the action to set isRunning to false
      final resetActions = actionsNotifier.value.map((action) {
        if (action.id == actionId) {
          return action.copyWith(isRunning: false);
        }
        return action;
      }).toList();
      actionsNotifier.value = resetActions;

      _actionCompleters.remove(actionId); // Clean up on timeout
    }
  }

  @override
  Widget buildWidget(BuildContext context) {
    return ActionsWidget(module: this);
  }

  @override
  void dispose() {
    _socketManager?.off('actions_updated'); // Remove listener
    _socketManager?.off('action_result');
    actionsNotifier.value = [];
    // Clean up any pending completers
    for (final completer in _actionCompleters.values) {
      if (!completer.isCompleted) {
        completer.completeError('Module disposed');
      }
    }
    _actionCompleters.clear();
  }
}
