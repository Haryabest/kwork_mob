import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
import 'package:kwork_mobile/services/company_access_policy.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';
import 'package:kwork_mobile/services/storage_space.dart';
import 'package:kwork_mobile/services/scale_calibration_service.dart';
import 'package:kwork_mobile/widgets/ghost_mesh.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/l10n/catalog_l10n.dart';
import 'package:kwork_mobile/widgets/order_limit_dialog.dart';

/// Выбор категории + чек-лист запрещённых (§3.5.4) + age-gate 18+ (§10.8.3).
class CategoryScreen extends StatefulWidget {
  const CategoryScreen({
    super.key,
    required this.api,
    required this.session,
  });

  final ApiClient api;
  final AppSession session;

  @override
  State<CategoryScreen> createState() => _CategoryScreenState();
}

class _CategoryScreenState extends State<CategoryScreen> {
  ProductCategory? _category;
  final _forbidden = <ForbiddenCategory>{};
  Tier _tier = Tier.small;
  final _scaleW = TextEditingController();
  final _scaleH = TextEditingController();
  final _scaleD = TextEditingController();
  final _birth = TextEditingController();
  final _modelName = TextEditingController();
  double _ghostScale = 1.0;
  CompanyAccessPolicy? _accessPolicy;

  @override
  void initState() {
    super.initState();
    AnalyticsService.instance.track('screen_view', {'screen': 'shoot_category'});
    if (widget.session.dateOfBirth != null) {
      _birth.text = widget.session.dateOfBirth!;
    }
    _loadAccessPolicy();
  }

  Future<void> _loadAccessPolicy() async {
    if (!widget.session.corporate) return;
    final policy = await CompanyAccessPolicy.load(widget.api, widget.session);
    if (!mounted) return;
    setState(() => _accessPolicy = policy);
  }

  @override
  void dispose() {
    _scaleW.dispose();
    _scaleH.dispose();
    _scaleD.dispose();
    _birth.dispose();
    _modelName.dispose();
    super.dispose();
  }

  int? _ageYears(String raw) {
    final parts = raw.trim().split('-');
    if (parts.length != 3) return null;
    final y = int.tryParse(parts[0]);
    final m = int.tryParse(parts[1]);
    final d = int.tryParse(parts[2]);
    if (y == null || m == null || d == null) return null;
    final dob = DateTime(y, m, d);
    final now = DateTime.now();
    var years = now.year - dob.year;
    if (now.month < dob.month || (now.month == dob.month && now.day < dob.day)) {
      years -= 1;
    }
    return years;
  }

  Future<bool> _confirmAgeGate() async {
    if (widget.session.ageVerified) return true;
    final ok = await showFDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx, style, animation) {
        final dlg = AppLocalizations.of(ctx)!;
        final ctrl = TextEditingController(text: _birth.text);
        return FDialog(
          title: Text(dlg.shootAgeConfirmTitle),
          body: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(dlg.shootAgeConfirmBody),
              const SizedBox(height: 12),
              FTextField(
                control: FTextFieldControl.managed(controller: ctrl),
                label: Text(dlg.shootBirthDate),
                hint: '1990-01-15',
                keyboardType: TextInputType.datetime,
              ),
            ],
          ),
          actions: [
            FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(dlg.cancel)),
            FButton(
              onPress: () {
                final years = _ageYears(ctrl.text);
                if (years == null) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text(dlg.shootInvalidDate)),
                  );
                  return;
                }
                if (years < 18) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text(dlg.shootAgeOnly18)),
                  );
                  Navigator.pop(ctx, false);
                  return;
                }
                _birth.text = ctrl.text.trim();
                Navigator.pop(ctx, true);
              },
              child: Text(dlg.confirm),
            ),
          ],
        );
      },
    );
    return ok == true;
  }

  Future<bool> _checkOrderLimit() async {
    if (!widget.session.corporate) return true;
    final companyId = widget.session.companyId;
    if (companyId == null) return true;
    final isOwner = widget.session.companies.any(
      (c) => c['id'] == companyId && c['is_owner'] == true,
    );
    if (isOwner) return true;
    try {
      final membersData = await widget.api.listCompanyMembers();
      final members = (membersData['items'] as List?)?.cast<Map>() ?? [];
      final myId = widget.session.userId;
      Map? me;
      for (final m in members) {
        if (m['user_id'] == myId) {
          me = m;
          break;
        }
      }
      final max = (me?['max_concurrent_orders'] as num?)?.toInt() ?? 5;
      final orders = await widget.api.listOrders();
      final active = widget.api.countActiveOrders(
        orders,
        companyId: companyId,
      );
      if (active >= max) {
        if (mounted) await showOrderLimitDialog(context);
        return false;
      }
    } catch (_) {}
    return true;
  }

  Future<void> _onCategoryChange(ProductCategory? c) async {
    if (c == null) return;
    setState(() => _category = c);
    if (c.requiresAgeGate && !widget.session.ageVerified) {
      await _confirmAgeGate();
      if (mounted) setState(() {});
    }
  }

  Future<void> _next() async {
    if (_category == null) return;

    if (_accessPolicy != null && !_accessPolicy!.isCategoryAllowed(_category!.api)) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context)!.shootCategoryRestricted)),
      );
      return;
    }

    if (!await _checkOrderLimit()) return;

    final okSpace = await StorageSpaceGuard.instance.hasEnoughForShoot();
    if (!okSpace) {
      final mb = await StorageSpaceGuard.instance.freeMb();
      if (!mounted) return;
      final l10n = AppLocalizations.of(context)!;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            mb != null
                ? l10n.shootStorageFree('${StorageSpaceGuard.minFreeMb}', '$mb')
                : l10n.shootStorageFreeUnknown('${StorageSpaceGuard.minFreeMb}'),
          ),
        ),
      );
      return;
    }

    if (_forbidden.isNotEmpty) {
      final l10n = AppLocalizations.of(context)!;
      final ok = await showFDialog<bool>(
        context: context,
        builder: (ctx, style, animation) => FDialog(
          title: Text(l10n.shootForbiddenTitle),
          body: Text(l10n.shootForbiddenBody),
          actions: [
            FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
            FButton(
              variant: .destructive,
              onPress: () => Navigator.pop(ctx, true),
              child: Text(l10n.continueBtn),
            ),
          ],
        ),
      );
      if (ok != true) return;
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.shootOrderBlocked)),
      );
      return;
    }

    if (_category!.requiresAgeGate) {
      if (!widget.session.ageVerified) {
        final confirmed = await _confirmAgeGate();
        if (!confirmed) return;
        if (_birth.text.trim().isEmpty) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(AppLocalizations.of(context)!.shootBirthRequired)),
          );
          return;
        }
      }
    }

    Map<String, dynamic>? scale;
    if (_category!.requiresScaleCalibration) {
      final saved = await ScaleCalibrationService.instance.scaleForOrder();
      if (saved != null) {
        scale = saved;
      } else {
        final w = double.tryParse(_scaleW.text.replaceAll(',', '.'));
        final h = double.tryParse(_scaleH.text.replaceAll(',', '.'));
        final d = double.tryParse(_scaleD.text.replaceAll(',', '.'));
        if (w == null || h == null || d == null) {
          final l10n = AppLocalizations.of(context)!;
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(l10n.calIntro)),
          );
          return;
        }
        scale = {'width': w, 'height': h, 'depth': d};
      }
    } else {
      scale = await ScaleCalibrationService.instance.scaleForOrder();
    }

    final uuid = ShootStorage.instance.newUuid();
    final birth = _category!.requiresAgeGate
        ? (widget.session.ageVerified
            ? widget.session.dateOfBirth
            : (_birth.text.trim().isEmpty ? null : _birth.text.trim()))
        : null;
    final draft = ShootDraft(
      modelUuid: uuid,
      category: _category!,
      tier: _tier,
      companyId: widget.session.companyId,
      forbidden: _forbidden.toList(),
      scaleCalibration: scale,
      birthDate: birth,
      createdAt: DateTime.now(),
      ghostScale: _ghostScale,
      displayName: _modelName.text.trim().isEmpty ? null : _modelName.text.trim(),
    );
    await ShootStorage.instance.writeMetadata(draft);

    if (!mounted) return;
    context.push('/home/shoot/dome', extra: uuid);
  }

  Map<String, ProductCategory> _categoryItems(AppLocalizations l) {
    final all = productCategorySelectItems(l);
    final policy = _accessPolicy;
    if (policy == null || !policy.restrictsCategories) return all;
    return Map.fromEntries(
      all.entries.where((e) => policy.isCategoryAllowed(e.key.api)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final hidePrices = widget.session.hidePrices;
    final ageOk = widget.session.ageVerified;
    return FScaffold(
      header: FHeader.nested(
        title: Text(l10n.shootCategoryTitle),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
      ),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          FSelect<ProductCategory>(
            label: Text(l10n.shootCategoryLabel),
            control: FSelectControl.managed(
              initial: _category,
              onChange: (v) => _onCategoryChange(v),
            ),
            items: _categoryItems(l10n),
          ),
          const SizedBox(height: 20),
          Text(l10n.shootForbiddenCategories, style: context.theme.typography.lg),
          const SizedBox(height: 4),
          Text(
            l10n.shootForbiddenHint,
            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
          ),
          const SizedBox(height: 8),
          FSelectGroup<ForbiddenCategory>(
            control: FMultiValueControl.lifted(
              value: _forbidden,
              onChange: (v) => setState(() {
                _forbidden
                  ..clear()
                  ..addAll(v);
              }),
            ),
            children: [
              for (final f in ForbiddenCategory.values)
                FSelectGroupItemMixin.checkbox(
                  value: f,
                  label: Text(f.localized(l10n)),
                ),
            ],
          ),
          if (_category?.requiresAgeGate == true) ...[
            const SizedBox(height: 8),
            if (ageOk)
              FTile(
                title: Text(l10n.shootAgeConfirmed),
                subtitle: Text(l10n.shootAgeConfirmedSub),
                prefix: const Icon(FIcons.shieldCheck, color: AppColors.success),
              )
            else
              FTextField(
                control: FTextFieldControl.managed(controller: _birth),
                label: Text(l10n.shootBirthDate),
                description: Text(l10n.shootBirthDateHint),
              ),
          ],
          if (_category?.requiresScaleCalibration == true) ...[
            const SizedBox(height: 12),
            Text(l10n.shootScaleRequired, style: context.theme.typography.sm),
            const SizedBox(height: 8),
            FButton(
              variant: .outline,
              onPress: () async {
                await context.push<bool>('/home/calibration');
                final cal = await ScaleCalibrationService.instance.scaleForOrder();
                if (!mounted || cal == null) return;
                setState(() {
                  _scaleW.text = cal['width']?.toString() ?? '';
                  _scaleH.text = cal['height']?.toString() ?? '';
                  _scaleD.text = cal['depth']?.toString() ?? '';
                });
              },
              child: Text(l10n.shootCalibrationBtn),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(child: FTextField(control: FTextFieldControl.managed(controller: _scaleW), label: Text(l10n.shootLength))),
                const SizedBox(width: 8),
                Expanded(child: FTextField(control: FTextFieldControl.managed(controller: _scaleH), label: Text(l10n.shootWidth))),
                const SizedBox(width: 8),
                Expanded(child: FTextField(control: FTextFieldControl.managed(controller: _scaleD), label: Text(l10n.shootHeight))),
              ],
            ),
          ],
          const SizedBox(height: 16),
          FTextField(
            control: FTextFieldControl.managed(controller: _modelName),
            label: Text(l10n.shootModelName),
            hint: l10n.shootModelNameHint,
          ),
          const SizedBox(height: 16),
          Text(l10n.shootTier, style: context.theme.typography.lg),
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
                  label: Text(hidePrices ? t.localized(l10n) : '${t.localized(l10n)} — ${t.priceRub} ₽'),
                ),
            ],
          ),
          if (_category != null) ...[
            const SizedBox(height: 16),
            Text(l10n.shootGhostMeshHint, style: context.theme.typography.sm),
            const SizedBox(height: 8),
            SizedBox(
              height: 180,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: AppColors.surface,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: GhostMeshOverlay(
                  category: _category!,
                  scale: _ghostScale,
                  aligned: true,
                  onScaleUpdate: (s) => setState(() => _ghostScale = s),
                ),
              ),
            ),
          ],
          const SizedBox(height: 16),
          FButton(
            onPress: _category == null ? null : _next,
            child: Text(l10n.shootNext),
          ),
        ],
      ),
    );
  }
}
