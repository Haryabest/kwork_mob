import 'dart:convert';

import 'package:kwork_mobile/core/api.dart';
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

  Map<String, dynamic> _fromServer(Map<String, dynamic> filters) {
    final author = filters['author_id'];
    return {
      'date_from': filters['date_from']?.toString() ?? '',
      'date_to': filters['date_to']?.toString() ?? '',
      'tx_type': filters['tx_type']?.toString() ?? 'all',
      'page_size': (filters['page_size'] as num?)?.toInt() ?? 20,
      'author_filter': author == null ? -1 : (author as num).toInt(),
    };
  }

  Map<String, dynamic> _toServer(Map<String, dynamic> local, {required bool company}) {
    final payload = <String, dynamic>{
      'date_from': local['date_from']?.toString() ?? '',
      'date_to': local['date_to']?.toString() ?? '',
      'tx_type': local['tx_type']?.toString() ?? 'all',
      'page_size': (local['page_size'] as num?)?.toInt() ?? 20,
    };
    if (company) {
      final author = (local['author_filter'] as num?)?.toInt() ?? -1;
      if (author >= 0) payload['author_id'] = author;
    }
    return payload;
  }

  /// Server saved views §20.3.4 with local fallback.
  Future<Map<String, dynamic>> loadSynced(ApiClient api, {required bool company}) async {
    try {
      final data = company ? await api.getCompanyBalanceFilters() : await api.getBalanceFilters();
      final filters = Map<String, dynamic>.from(data['filters'] as Map? ?? {});
      final mapped = _fromServer(filters);
      await save(
        dateFrom: mapped['date_from']?.toString(),
        dateTo: mapped['date_to']?.toString(),
        txType: mapped['tx_type']?.toString(),
        pageSize: mapped['page_size'] as int?,
        authorFilter: mapped['author_filter'] as int?,
      );
      return mapped;
    } catch (_) {
      return load();
    }
  }

  Future<void> saveSynced(
    ApiClient api, {
    required bool company,
    String? dateFrom,
    String? dateTo,
    String? txType,
    int? pageSize,
    int? authorFilter,
  }) async {
    await save(
      dateFrom: dateFrom,
      dateTo: dateTo,
      txType: txType,
      pageSize: pageSize,
      authorFilter: authorFilter,
    );
    try {
      final local = {
        'date_from': dateFrom ?? '',
        'date_to': dateTo ?? '',
        'tx_type': txType ?? 'all',
        'page_size': pageSize ?? 20,
        'author_filter': authorFilter ?? -1,
      };
      final payload = _toServer(local, company: company);
      if (company) {
        await api.putCompanyBalanceFilters(payload);
      } else {
        await api.putBalanceFilters(payload);
      }
    } catch (_) {}
  }
}
