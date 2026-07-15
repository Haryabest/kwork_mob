import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

class CampaignBanner extends StatelessWidget {
  const CampaignBanner({
    super.key,
    required this.title,
    required this.body,
    required this.onDismiss,
  });

  final String title;
  final String body;
  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Material(
      color: AppColors.accent.withValues(alpha: 0.1),
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(FIcons.gift, color: AppColors.accent, size: 20),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w600)),
                  if (body.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(body, style: const TextStyle(fontSize: 13)),
                  ],
                ],
              ),
            ),
            IconButton(
              icon: const Icon(FIcons.x, size: 18),
              tooltip: l10n.campaignBannerDismiss,
              onPressed: onDismiss,
            ),
          ],
        ),
      ),
    );
  }
}
