import 'package:flutter/material.dart';

class ActionCard extends StatelessWidget {
  final CardAction action;

  const ActionCard(this.action, {super.key});

  @override
  Widget build(BuildContext context) {
    return ElevatedButton(
      onPressed: () => {
        if (action.onPressed != null) {action.onPressed!(action.id)},
      },
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.all(16),
        backgroundColor: Theme.of(context).colorScheme.primary,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            action.icon,
            size: 36,
            color: Theme.of(context).colorScheme.onPrimary,
          ),
          const SizedBox(height: 8),
          Text(
            action.title,
            textAlign: TextAlign.center,
            style: TextStyle(color: Theme.of(context).colorScheme.onPrimary),
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

  CardAction({
    required this.id,
    required this.title,
    required this.icon,
    this.onPressed,
  });
}
