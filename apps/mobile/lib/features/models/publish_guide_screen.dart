import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

class PublishGuideScreen extends StatefulWidget {
  const PublishGuideScreen({super.key});

  @override
  State<PublishGuideScreen> createState() => _PublishGuideScreenState();
}

class _PublishGuideScreenState extends State<PublishGuideScreen> {
  @override
  void initState() {
    super.initState();
    AnalyticsService.instance.track('screen_view', {'screen': 'publish_guide'});
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return FScaffold(
      header: FHeader.nested(
        title: Text(l10n.publishGuideTitle),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
      ),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(l10n.publishGuideIntro),
          const SizedBox(height: 16),
          Text(l10n.publishGuideWbTitle, style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Text(l10n.publishGuideWb1),
          Text(l10n.publishGuideWb2),
          Text(l10n.publishGuideWb3),
          const SizedBox(height: 16),
          Text(l10n.publishGuideOzonTitle, style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          Text(l10n.publishGuideOzon1),
          Text(l10n.publishGuideOzon2),
          Text(l10n.publishGuideOzon3),
          const SizedBox(height: 24),
          FButton(
            onPress: () => context.go('/home?tab=models'),
            child: Text(l10n.publishGuideOpenModels),
          ),
        ],
      ),
    );
  }
}
