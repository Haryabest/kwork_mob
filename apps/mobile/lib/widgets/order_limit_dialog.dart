import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

Future<void> showOrderLimitDialog(BuildContext context) {
  final l10n = AppLocalizations.of(context)!;
  return showFDialog<void>(
    context: context,
    builder: (ctx, style, animation) => FDialog(
      title: Text(l10n.orderLimitTitle),
      body: Text(l10n.orderLimitBody),
      actions: [
        FButton(onPress: () => Navigator.pop(ctx), child: Text(l10n.orderLimitOk)),
      ],
    ),
  );
}

bool isOrderLimitError(Object? error) {
  final s = error.toString();
  return s.contains('Лимит одновременных заказов') ||
      s.contains('concurrent order') ||
      s.contains('403');
}
