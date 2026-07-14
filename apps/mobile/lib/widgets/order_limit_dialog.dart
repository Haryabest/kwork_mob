import 'package:flutter/material.dart';
import 'package:forui/forui.dart';

Future<void> showOrderLimitDialog(BuildContext context) {
  return showFDialog<void>(
    context: context,
    builder: (ctx, style, animation) => FDialog(
      title: const Text('Лимит активных заказов'),
      body: const Text(
        'Достигнут лимит одновременных заказов для вашей роли. '
        'Дождитесь завершения текущих генераций или обратитесь к Owner.',
      ),
      actions: [
        FButton(onPress: () => Navigator.pop(ctx), child: const Text('Понятно')),
      ],
    ),
  );
}

bool isOrderLimitError(Object? error) {
  final s = error.toString();
  return s.contains('Лимит одновременных заказов') || s.contains('403');
}
