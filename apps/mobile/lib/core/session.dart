import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Режим Личный / Компания (§3.14) + permissions из API (§2.5.3).
class AppSession extends ChangeNotifier {
  AppSession();

  int? _userId;
  String? _email;
  double? _balance;
  bool _corporate = false;
  int? _companyId;
  String? _companyName;
  String? _companyRole;
  Map<String, bool> _permissions = {};
  List<Map<String, dynamic>> _companies = [];

  int? get userId => _userId;
  String? get email => _email;
  double? get balance => _balance;
  bool get corporate => _corporate;
  int? get companyId => _corporate ? _companyId : null;
  String? get companyName => _companyName;
  String? get companyRole => _companyRole;
  Map<String, bool> get permissions => Map.unmodifiable(_permissions);
  List<Map<String, dynamic>> get companies => _companies;

  bool hasPermission(String key) {
    if (!_corporate) return true;
    return _permissions[key] == true;
  }

  bool get canCreateOrders => hasPermission('can_create_orders');

  bool get canManageTeam =>
      hasPermission('can_invite_members') || hasPermission('can_manage_roles');

  bool get canViewFinance => hasPermission('can_view_finance');

  /// Цены/баланс скрываем без can_view_finance (§2.5.3 photographer).
  bool get hidePrices => _corporate && !canViewFinance;

  @Deprecated('Use permissions / canCreateOrders')
  bool get isPhotographer =>
      _corporate && (_companyRole == 'photographer' || !canViewFinance);

  Map<String, bool> _parsePermissions(dynamic raw) {
    if (raw is! Map) return {};
    final out = <String, bool>{};
    raw.forEach((k, v) {
      out[k.toString()] = v == true;
    });
    return out;
  }

  Future<void> loadPersisted() async {
    final prefs = await SharedPreferences.getInstance();
    _corporate = prefs.getBool('mode_corporate') ?? false;
    _companyId = prefs.getInt('mode_company_id');
    _companyName = prefs.getString('mode_company_name');
    _companyRole = prefs.getString('mode_company_role');
    final permJson = prefs.getString('mode_company_permissions');
    if (permJson != null && permJson.isNotEmpty) {
      try {
        _permissions = _parsePermissions(jsonDecode(permJson));
      } catch (_) {
        _permissions = {};
      }
    }
    notifyListeners();
  }

  void applyMe(Map<String, dynamic> me) {
    _userId = me['id'] as int?;
    _email = me['email']?.toString();
    final b = me['balance'];
    _balance = b is num ? b.toDouble() : null;
    notifyListeners();
  }

  Future<void> setCompanies(List<Map<String, dynamic>> items) async {
    _companies = items;
    if (_companyId != null) {
      final match = items.where((e) => e['id'] == _companyId).toList();
      if (match.isEmpty) {
        await setPersonal();
      } else {
        await _applyCompanyMap(match.first, persist: true);
      }
    }
    notifyListeners();
  }

  Future<void> _applyCompanyMap(
    Map<String, dynamic> company, {
    required bool persist,
  }) async {
    _companyName = company['name']?.toString();
    _companyRole = company['role']?.toString();
    _permissions = _parsePermissions(company['permissions']);
    if (persist) {
      final prefs = await SharedPreferences.getInstance();
      if (_companyName != null) {
        await prefs.setString('mode_company_name', _companyName!);
      }
      if (_companyRole != null) {
        await prefs.setString('mode_company_role', _companyRole!);
      }
      await prefs.setString(
        'mode_company_permissions',
        jsonEncode(_permissions),
      );
    }
  }

  Future<void> setPersonal() async {
    _corporate = false;
    _companyId = null;
    _companyName = null;
    _companyRole = null;
    _permissions = {};
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('mode_corporate', false);
    await prefs.remove('mode_company_id');
    await prefs.remove('mode_company_name');
    await prefs.remove('mode_company_role');
    await prefs.remove('mode_company_permissions');
    notifyListeners();
  }

  Future<void> setCompany(Map<String, dynamic> company) async {
    _corporate = true;
    _companyId = company['id'] as int?;
    await _applyCompanyMap(company, persist: true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('mode_corporate', true);
    if (_companyId != null) await prefs.setInt('mode_company_id', _companyId!);
    notifyListeners();
  }
}
