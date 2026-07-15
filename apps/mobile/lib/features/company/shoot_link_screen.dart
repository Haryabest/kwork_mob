import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/l10n/catalog_l10n.dart';
import 'package:qr_flutter/qr_flutter.dart';

/// Создание shoot-link + QR (§3.15).
class ShootLinkScreen extends StatefulWidget {
  const ShootLinkScreen({
    super.key,
    required this.api,
    required this.session,
  });

  final ApiClient api;
  final AppSession session;

  @override
  State<ShootLinkScreen> createState() => _ShootLinkScreenState();
}

class _ShootLinkScreenState extends State<ShootLinkScreen> {
  ProductCategory _category = ProductCategory.other;
  Tier _tier = Tier.small;
  Map<String, dynamic>? _link;
  bool _loading = false;
  String? _error;

  Future<void> _create() async {
    final l10n = AppLocalizations.of(context)!;
    final companyId = widget.session.companyId;
    if (companyId == null) {
      setState(() => _error = l10n.shootLinkCorpMode);
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      _link = await widget.api.createShootLink(
        companyId: companyId,
        category: _category.api,
        tier: _tier.api,
      );
    } catch (e) {
      _error = formatApiError(e);
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final url = _link?['url']?.toString();
    final hidePrices = widget.session.hidePrices;
    return FScaffold(
      header: FHeader.nested(
        title: Text(l10n.shootLinkTitle),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
      ),
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          FSelect<ProductCategory>(
            label: Text(l10n.shootCategoryLabel),
            control: FSelectControl.managed(
              initial: _category,
              onChange: (v) {
                if (v != null) setState(() => _category = v);
              },
            ),
            items: productCategorySelectItems(l10n),
          ),
          const SizedBox(height: 16),
          Text(l10n.shootLinkTier, style: context.theme.typography.lg),
          const SizedBox(height: 8),
          FSelectGroup<Tier>(
            control: FMultiValueControl.managedRadio(
              initial: _tier,
              onChange: (v) {
                if (v.isNotEmpty) setState(() => _tier = v.first);
              },
            ),
            children: [
              for (final t in Tier.values)
                FSelectGroupItemMixin.radio(
                  value: t,
                  label: Text(
                    hidePrices
                        ? t.localized(l10n)
                        : '${t.localized(l10n)} — ${t.priceRub} ₽',
                  ),
                ),
            ],
          ),
          const SizedBox(height: 16),
          FButton(
            onPress: _loading ? null : _create,
            child: _loading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(l10n.shootLinkCreate),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: AppColors.error)),
          ],
          if (url != null) ...[
            const SizedBox(height: 24),
            Center(
              child: QrImageView(
                data: url,
                size: 220,
                backgroundColor: Colors.white,
              ),
            ),
            const SizedBox(height: 12),
            SelectableText(url, style: const TextStyle(fontSize: 13)),
            const SizedBox(height: 8),
            FButton(
              variant: .outline,
              onPress: () async {
                await Clipboard.setData(ClipboardData(text: url));
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text(l10n.shootLinkCopied)),
                  );
                }
              },
              child: Text(l10n.shootLinkCopy),
            ),
          ],
        ],
      ),
    );
  }
}
