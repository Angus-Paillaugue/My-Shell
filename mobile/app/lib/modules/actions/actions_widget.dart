import 'dart:async';
import 'package:flutter/material.dart';
import 'action_card.dart';
import 'package:vellum_shell_sync/modules/actions/actions_module.dart';

class ActionsWidget extends StatefulWidget {
  final ActionsModule module;
  const ActionsWidget({required this.module, super.key});

  @override
  State<ActionsWidget> createState() => _ActionsWidgetState();
}

class _ActionsWidgetState extends State<ActionsWidget> {
  @override
  void initState() {
    super.initState();
  }

  Future<void> actionCallback(String id) async {
    try {
      await widget.module.sendAction(id);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text("Action failed: $e")));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async {
        widget.module.fetchActions();
        // Wait until isRefreshing is false
        while (widget.module.isRefreshing) {
          await Future.delayed(const Duration(milliseconds: 100));
        }
      },
      child: ValueListenableBuilder<List<CardAction>>(
        valueListenable: widget.module.actionsNotifier,
        builder: (context, actions, child) {
          if (actions.isEmpty) {
            // Wrap the "No actions available" message in a scrollable widget
            return SingleChildScrollView(
              physics: const AlwaysScrollableScrollPhysics(),
              child: SizedBox(
                height:
                    MediaQuery.of(context).size.height *
                    0.8, // Ensure enough space for pull-to-refresh
                child: const Center(
                  child: Padding(
                    padding: EdgeInsets.all(16.0),
                    child: Text("No actions available."),
                  ),
                ),
              ),
            );
          }

          return GridView.builder(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(12.0),
            shrinkWrap: true,
            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: 2,
              mainAxisSpacing: 12.0,
              crossAxisSpacing: 12.0,
              childAspectRatio: 1.0,
            ),
            itemCount: actions.length,
            itemBuilder: (BuildContext context, int index) {
              final action = actions[index];
              return ActionCard(action.copyWith(onPressed: actionCallback));
            },
          );
        },
      ),
    );
  }
}
