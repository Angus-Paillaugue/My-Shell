import 'package:flutter/material.dart';

class ActionCard extends StatelessWidget {
  final CardAction action;

  const ActionCard(this.action, {super.key});

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: action.isRunning
          ? null
          : () => action.onPressed?.call(action.id),
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.all(16),
        backgroundColor: action.isRunning
            ? Theme.of(context).colorScheme.onSurface
            : Theme.of(context).colorScheme.primary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            action.icon,
            size: 36,
            color: action.isRunning
                ? Theme.of(context).colorScheme.onSurfaceVariant
                : Theme.of(context).colorScheme.onPrimary,
          ),
          const SizedBox(height: 8),
          Text(
            action.title,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: action.isRunning
                  ? Theme.of(context).colorScheme.onSurfaceVariant
                  : Theme.of(context).colorScheme.onPrimary,
            ),
          ),
        ],
      ),
    );
  }
}

class CardAction {
  final String id;
  final String title;
  final Function(String)? onPressed;
  final IconData icon;
  final bool isRunning;

  CardAction({
    required this.id,
    required this.title,
    required this.icon,
    this.onPressed,
    this.isRunning = false,
  });

  CardAction copyWith({
    String? id,
    String? title,
    Function(String)? onPressed,
    IconData? icon,
    bool? isRunning,
  }) {
    return CardAction(
      id: id ?? this.id,
      title: title ?? this.title,
      onPressed: onPressed ?? this.onPressed,
      icon: icon ?? this.icon,
      isRunning: isRunning ?? this.isRunning,
    );
  }
}
