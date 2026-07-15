import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

/// Баннер низкого баланса компании §20.3.5.
class LowBalanceBanner extends StatelessWidget {
  const LowBalanceBanner({
    super.key,
    required this.balance,
    required this.threshold,
    this.onTopup,
  });

  final double balance;
  final int threshold;
  final VoidCallback? onTopup;

  @override
  Widget build(BuildContext context) {
    if (balance >= threshold) return const SizedBox.shrink();
    final l10n = AppLocalizations.of(context)!;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.error.withValues(alpha: 0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.warning_amber_rounded, color: AppColors.error, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  l10n.lowBalanceBanner(
                    balance.toStringAsFixed(0),
                    threshold.toString(),
                  ),
                  style: const TextStyle(fontSize: 13),
                ),
              ),
            ],
          ),
          if (onTopup != null) ...[
            const SizedBox(height: 8),
            FButton(onPress: onTopup, child: Text(l10n.topup)),
          ],
        ],
      ),
    );
  }
}
