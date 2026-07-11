import 'package:flutter/material.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

/// Заглушка экрана (будет заполняться по §19).
class PlaceholderScreen extends StatelessWidget {
  const PlaceholderScreen({super.key, required this.titleKey});

  final String titleKey;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final title = switch (titleKey) {
      'queue' => l10n.queue,
      'orders' => l10n.orders,
      'support' => l10n.support,
      'profile' => l10n.profile,
      _ => titleKey,
    };
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: Center(child: Text(l10n.comingSoon)),
    );
  }
}
