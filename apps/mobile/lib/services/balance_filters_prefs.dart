import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// Сохранение фильтров баланса / CSV export §20.3.4.
class BalanceFiltersPrefs {
  BalanceFiltersPrefs._();
  static final instance = BalanceFiltersPrefs._();

  static const _key = 'balance_tx_filters_v1';

  Future<Map<String, dynamic>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return {};
    try {
      return Map<String, dynamic>.from(jsonDecode(raw) as Map);
    } catch (_) {
      return {};
    }
  }

  Future<void> save({
    String? dateFrom,
    String? dateTo,
    String? txType,
    int? pageSize,
    int? authorFilter,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      _key,
      jsonEncode({
        'date_from': dateFrom ?? '',
        'date_to': dateTo ?? '',
        'tx_type': txType ?? 'all',
        'page_size': pageSize ?? 20,
        'author_filter': authorFilter ?? -1,
      }),
    );
  }
}
