import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';

/// Выбор категории + чек-лист запрещённых (§3.5.4).
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

  @override
  void dispose() {
    _scaleW.dispose();
    _scaleH.dispose();
    _scaleD.dispose();
    _birth.dispose();
    super.dispose();
  }

  Future<void> _next() async {
    if (_category == null) return;

    if (_forbidden.isNotEmpty) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Запрещённая категория'),
          content: const Text(
            'Вы выбрали запрещённую категорию. Заказ будет отклонён без возврата средств. Продолжить?',
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Продолжить')),
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

    if (_category!.requiresAgeGate && _birth.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Укажите дату рождения (YYYY-MM-DD) для 18+')),
      );
      return;
    }

    Map<String, dynamic>? scale;
    if (_category!.requiresScaleCalibration) {
      final w = double.tryParse(_scaleW.text.replaceAll(',', '.'));
      final h = double.tryParse(_scaleH.text.replaceAll(',', '.'));
      final d = double.tryParse(_scaleD.text.replaceAll(',', '.'));
      if (w == null || h == null || d == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Для мебели укажите длину, ширину и высоту (м)')),
        );
        return;
      }
      scale = {'width': w, 'height': h, 'depth': d};
    }

    final uuid = ShootStorage.instance.newUuid();
    final draft = ShootDraft(
      modelUuid: uuid,
      category: _category!,
      tier: _tier,
      companyId: widget.session.companyId,
      forbidden: _forbidden.toList(),
      scaleCalibration: scale,
      createdAt: DateTime.now(),
    );
    await ShootStorage.instance.writeMetadata(draft);

    if (!mounted) return;
    context.push('/home/shoot/dome', extra: uuid);
  }

  @override
  Widget build(BuildContext context) {
    final hidePrices = widget.session.hidePrices;
    return FScaffold(
      header: FHeader.nested(
        title: const Text('Категория товара'),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
      ),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Категория', style: context.theme.typography.lg),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: ProductCategory.values.map((c) {
              final selected = _category == c;
              return ChoiceChip(
                label: Text(c.label),
                selected: selected,
                selectedColor: AppColors.wbPrimary.withValues(alpha: 0.2),
                onSelected: (_) => setState(() => _category = c),
              );
            }).toList(),
          ),
          const SizedBox(height: 20),
          Text('Запрещённые категории', style: context.theme.typography.lg),
          const SizedBox(height: 4),
          Text(
            'Если отметите — заказ не создаётся, средства не списываются',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
          ),
          ...ForbiddenCategory.values.map(
            (f) => CheckboxListTile(
              value: _forbidden.contains(f),
              title: Text(f.label),
              onChanged: (v) => setState(() {
                if (v == true) {
                  _forbidden.add(f);
                } else {
                  _forbidden.remove(f);
                }
              }),
            ),
          ),
          if (_category?.requiresAgeGate == true) ...[
            const SizedBox(height: 8),
            TextField(
              controller: _birth,
              decoration: const InputDecoration(
                labelText: 'Дата рождения (YYYY-MM-DD)',
                border: OutlineInputBorder(),
              ),
            ),
          ],
          if (_category?.requiresScaleCalibration == true) ...[
            const SizedBox(height: 12),
            Text('Масштаб (м) — обязательно для мебели', style: context.theme.typography.sm),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(child: TextField(controller: _scaleW, decoration: const InputDecoration(labelText: 'Длина', border: OutlineInputBorder()))),
                const SizedBox(width: 8),
                Expanded(child: TextField(controller: _scaleH, decoration: const InputDecoration(labelText: 'Ширина', border: OutlineInputBorder()))),
                const SizedBox(width: 8),
                Expanded(child: TextField(controller: _scaleD, decoration: const InputDecoration(labelText: 'Высота', border: OutlineInputBorder()))),
              ],
            ),
          ],
          const SizedBox(height: 16),
          Text('Тариф', style: context.theme.typography.lg),
          const SizedBox(height: 8),
          ...Tier.values.map(
            (t) => RadioListTile<Tier>(
              value: t,
              groupValue: _tier,
              title: Text(hidePrices ? t.label : '${t.label} — ${t.priceRub} ₽'),
              onChanged: (v) => setState(() => _tier = v!),
            ),
          ),
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
