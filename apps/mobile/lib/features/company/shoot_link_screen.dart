import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/catalog.dart';
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

  Map<String, ProductCategory> get _categoryItems => {
        for (final c in ProductCategory.values) c.label: c,
      };

  Future<void> _create() async {
    final companyId = widget.session.companyId;
    if (companyId == null) {
      setState(() => _error = 'Выберите корпоративный режим');
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
    final url = _link?['url']?.toString();
    final hidePrices = widget.session.hidePrices;
    return FScaffold(
      header: FHeader.nested(
        title: const Text('Съёмка по ссылке'),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
      ),
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          FSelect<ProductCategory>(
            label: const Text('Категория'),
            control: FSelectControl.managed(
              initial: _category,
              onChange: (v) {
                if (v != null) setState(() => _category = v);
              },
            ),
            items: _categoryItems,
          ),
          const SizedBox(height: 16),
          Text('Тариф', style: context.theme.typography.lg),
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
                  label: Text(hidePrices ? t.label : '${t.label} — ${t.priceRub} ₽'),
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
                : const Text('Создать ссылку и QR'),
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
                    const SnackBar(content: Text('Ссылка скопирована')),
                  );
                }
              },
              child: const Text('Копировать'),
            ),
          ],
        ],
      ),
    );
  }
}
