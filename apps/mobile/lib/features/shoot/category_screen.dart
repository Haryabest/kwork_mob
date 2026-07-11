import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/theme.dart';

/// Выбор категории + чек-лист запрещённых (§3.5.4) — каркас.
class CategoryScreen extends StatefulWidget {
  const CategoryScreen({super.key});

  @override
  State<CategoryScreen> createState() => _CategoryScreenState();
}

class _CategoryScreenState extends State<CategoryScreen> {
  String? _category;
  final _forbidden = <String>{};

  static const _categories = [
    'Одежда',
    'Обувь',
    'Аксессуары',
    'Электроника',
    'Косметика',
    'Другое',
  ];

  static const _forbiddenOptions = [
    'Оружие',
    'Наркотики',
    'NSFW / 18+',
    'Контрафакт',
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Категория товара')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Категория', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _categories
                .map(
                  (c) => ChoiceChip(
                    label: Text(c),
                    selected: _category == c,
                    onSelected: (_) => setState(() => _category = c),
                  ),
                )
                .toList(),
          ),
          const SizedBox(height: 24),
          Text('Запрещённые категории', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          Text(
            'Если отметите — заказ не создаётся, средства не списываются',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
          ),
          ..._forbiddenOptions.map(
            (f) => CheckboxListTile(
              value: _forbidden.contains(f),
              title: Text(f),
              onChanged: (v) => setState(() {
                if (v == true) {
                  _forbidden.add(f);
                } else {
                  _forbidden.remove(f);
                }
              }),
            ),
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _category == null
                ? null
                : () {
                    if (_forbidden.isNotEmpty) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Запрещённая категория отмечена — заказ не будет создан'),
                        ),
                      );
                      return;
                    }
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(content: Text('Категория: $_category. AR-съёмка — следующий этап.')),
                    );
                    context.pop();
                  },
            child: const Text('Далее к съёмке'),
          ),
        ],
      ),
    );
  }
}
