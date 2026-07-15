import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';
import 'package:kwork_mobile/services/storage_space.dart';
import 'package:kwork_mobile/services/scale_calibration_service.dart';
import 'package:kwork_mobile/widgets/ghost_mesh.dart';
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
  double _ghostScale = 1.0;

  @override
  void initState() {
    super.initState();
    if (widget.session.dateOfBirth != null) {
      _birth.text = widget.session.dateOfBirth!;
    }
  }

  @override
  void dispose() {
    _scaleW.dispose();
    _scaleH.dispose();
    _scaleD.dispose();
    _birth.dispose();
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
        final ctrl = TextEditingController(text: _birth.text);
        return FDialog(
          title: const Text('Подтвердите, что вам 18 лет'),
          body: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text('Введите дату рождения (YYYY-MM-DD).'),
              const SizedBox(height: 12),
              FTextField(
                control: FTextFieldControl.managed(controller: ctrl),
                label: const Text('Дата рождения'),
                hint: '1990-01-15',
                keyboardType: TextInputType.datetime,
              ),
            ],
          ),
          actions: [
            FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
            FButton(
              onPress: () {
                final years = _ageYears(ctrl.text);
                if (years == null) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Некорректная дата (YYYY-MM-DD)')),
                  );
                  return;
                }
                if (years < 18) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('Создание модели доступно только с 18 лет')),
                  );
                  Navigator.pop(ctx, false);
                  return;
                }
                _birth.text = ctrl.text.trim();
                Navigator.pop(ctx, true);
              },
              child: const Text('Подтвердить'),
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

    if (!await _checkOrderLimit()) return;

    final okSpace = await StorageSpaceGuard.instance.hasEnoughForShoot();
    if (!okSpace) {
      final mb = await StorageSpaceGuard.instance.freeMb();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            mb != null
                ? 'Освободите место на телефоне (нужно ${StorageSpaceGuard.minFreeMb} МБ, доступно ~$mb МБ)'
                : 'Освободите место на телефоне (нужно ${StorageSpaceGuard.minFreeMb} МБ)',
          ),
        ),
      );
      return;
    }

    if (_forbidden.isNotEmpty) {
      final ok = await showFDialog<bool>(
        context: context,
        builder: (ctx, style, animation) => FDialog(
          title: const Text('Запрещённая категория'),
          body: const Text(
            'Вы выбрали запрещённую категорию. Заказ будет отклонён без возврата средств. Продолжить?',
          ),
          actions: [
            FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
            FButton(
              variant: .destructive,
              onPress: () => Navigator.pop(ctx, true),
              child: const Text('Продолжить'),
            ),
          ],
        ),
      );
      if (ok != true) return;
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Заказ не будет создан — смените категорию')),
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
            const SnackBar(content: Text('Укажите дату рождения для 18+')),
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
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text(
                'Для мебели укажите размеры или выполните калибровку в профиле',
              ),
            ),
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
    );
    await ShootStorage.instance.writeMetadata(draft);

    if (!mounted) return;
    context.push('/home/shoot/dome', extra: uuid);
  }

  Map<String, ProductCategory> get _categoryItems => {
        for (final c in ProductCategory.values) c.label: c,
      };

  @override
  Widget build(BuildContext context) {
    final hidePrices = widget.session.hidePrices;
    final ageOk = widget.session.ageVerified;
    return FScaffold(
      header: FHeader.nested(
        title: const Text('Категория товара'),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
      ),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          FSelect<ProductCategory>(
            label: const Text('Категория'),
            control: FSelectControl.managed(
              initial: _category,
              onChange: (v) => _onCategoryChange(v),
            ),
            items: _categoryItems,
          ),
          const SizedBox(height: 20),
          Text('Запрещённые категории', style: context.theme.typography.lg),
          const SizedBox(height: 4),
          Text(
            'Если отметите — заказ не создаётся, средства не списываются',
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
                  label: Text(f.label),
                ),
            ],
          ),
          if (_category?.requiresAgeGate == true) ...[
            const SizedBox(height: 8),
            if (ageOk)
              FTile(
                title: const Text('Возраст подтверждён'),
                subtitle: const Text('Повторный ввод даты не требуется'),
                prefix: const Icon(FIcons.shieldCheck, color: AppColors.success),
              )
            else
              FTextField(
                control: FTextFieldControl.managed(controller: _birth),
                label: const Text('Дата рождения (YYYY-MM-DD)'),
                description: const Text('Сохраняется в профиле после успешной проверки'),
              ),
          ],
          if (_category?.requiresScaleCalibration == true) ...[
            const SizedBox(height: 12),
            Text('Масштаб (м) — обязательно для мебели', style: context.theme.typography.sm),
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
              child: const Text('Калибровка: карта / A4 / QR (§3.7)'),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(child: FTextField(control: FTextFieldControl.managed(controller: _scaleW), label: const Text('Длина'))),
                const SizedBox(width: 8),
                Expanded(child: FTextField(control: FTextFieldControl.managed(controller: _scaleH), label: const Text('Ширина'))),
                const SizedBox(width: 8),
                Expanded(child: FTextField(control: FTextFieldControl.managed(controller: _scaleD), label: const Text('Высота'))),
              ],
            ),
          ],
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
          if (_category != null) ...[
            const SizedBox(height: 16),
            Text('Ghost Mesh — масштаб двумя пальцами', style: context.theme.typography.sm),
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
            child: const Text('Далее к съёмке'),
          ),
        ],
      ),
    );
  }
}
