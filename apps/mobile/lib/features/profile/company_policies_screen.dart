import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

/// §19.14.2 — политики доступа компании (Owner).
class CompanyPoliciesScreen extends StatefulWidget {
  const CompanyPoliciesScreen({super.key, required this.api, required this.session});

  final ApiClient api;
  final AppSession session;

  @override
  State<CompanyPoliciesScreen> createState() => _CompanyPoliciesScreenState();
}

class _CompanyPoliciesScreenState extends State<CompanyPoliciesScreen> {
  bool _loading = true;
  bool _saving = false;
  bool _noMonthlyLimit = true;
  double? _balance;
  List<String> _categories = [];
  List<String> _selectedCategories = [];

  int _maxConcurrent = 5;
  int _monthlyLimit = 0;
  bool _allowDownload = true;
  bool _allowLinks = true;
  bool _require2fa = false;
  int _autoBlockDays = 90;
  int _lowBalanceThreshold = 5000;

  final _maxConcurrentCtrl = TextEditingController(text: '5');
  final _monthlyLimitCtrl = TextEditingController(text: '0');
  final _autoBlockCtrl = TextEditingController(text: '90');
  final _lowBalanceCtrl = TextEditingController(text: '5000');

  final Map<String, String> _routing = {
    'generation_done': 'owner_manager',
    'photographer_uploaded': 'owner_manager',
    'source_expire': 'all',
    'low_balance': 'owner_only',
  };

  @override
  void dispose() {
    _maxConcurrentCtrl.dispose();
    _monthlyLimitCtrl.dispose();
    _autoBlockCtrl.dispose();
    _lowBalanceCtrl.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await widget.api.getCompanySettings();
      final pol = data['policies'];
      if (pol is Map) {
        _maxConcurrent = (pol['default_max_concurrent_orders'] as num?)?.toInt() ?? 5;
        final monthly = pol['default_monthly_spending_limit'];
        _noMonthlyLimit = monthly == null;
        _monthlyLimit = (monthly as num?)?.toInt() ?? 0;
        final cats = pol['default_allowed_categories'];
        if (cats is List) {
          _selectedCategories = cats.map((e) => e.toString()).toList();
        }
        _allowDownload = pol['allow_photographer_download'] != false;
        _allowLinks = pol['allow_photographer_add_links'] != false;
        _require2fa = pol['require_2fa_for_all'] == true;
        _autoBlockDays = (pol['auto_block_inactive_days'] as num?)?.toInt() ?? 90;
        _lowBalanceThreshold = (pol['low_balance_threshold'] as num?)?.toInt() ?? 5000;
      }
      final routing = data['notification_routing'];
      if (routing is Map) {
        for (final e in _routing.keys) {
          final v = routing[e]?.toString();
          if (v != null && v.isNotEmpty) _routing[e] = v;
        }
      }
      final cats = data['available_categories'];
      if (cats is List) {
        _categories = cats.map((e) => e.toString()).toList();
      }
      final b = data['balance'];
      _balance = b is num ? b.toDouble() : null;

      _maxConcurrentCtrl.text = '$_maxConcurrent';
      _monthlyLimitCtrl.text = '$_monthlyLimit';
      _autoBlockCtrl.text = '$_autoBlockDays';
      _lowBalanceCtrl.text = '$_lowBalanceThreshold';
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _save() async {
    final l10n = AppLocalizations.of(context)!;
    final maxC = int.tryParse(_maxConcurrentCtrl.text.trim());
    if (maxC == null || maxC < 1 || maxC > 20) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.policiesInvalidConcurrent)),
      );
      return;
    }
    final autoBlock = int.tryParse(_autoBlockCtrl.text.trim());
    if (autoBlock == null || autoBlock < 1) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.policiesInvalidAutoBlock)),
      );
      return;
    }
    final lowBal = int.tryParse(_lowBalanceCtrl.text.trim());
    if (lowBal == null || lowBal < 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.policiesInvalidThreshold)),
      );
      return;
    }
    int? monthly;
    if (!_noMonthlyLimit) {
      monthly = int.tryParse(_monthlyLimitCtrl.text.trim());
      if (monthly == null || monthly < 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.policiesInvalidMonthly)),
        );
        return;
      }
    }

    setState(() => _saving = true);
    try {
      await widget.api.patchCompanySettings({
        'policies': {
          'default_max_concurrent_orders': maxC,
          'default_monthly_spending_limit': _noMonthlyLimit ? null : monthly,
          'default_allowed_categories': _selectedCategories,
          'allow_photographer_download': _allowDownload,
          'allow_photographer_add_links': _allowLinks,
          'require_2fa_for_all': _require2fa,
          'auto_block_inactive_days': autoBlock,
          'low_balance_threshold': lowBal,
        },
        'notification_routing': _routing,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.policiesSaved)),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  String _eventLabel(AppLocalizations l10n, String key) {
    return switch (key) {
      'generation_done' => l10n.notifyGenerationDone,
      'photographer_uploaded' => l10n.notifyPhotographerUploaded,
      'source_expire' => l10n.notifySourceExpire,
      'low_balance' => l10n.notifyLowBalance,
      _ => key,
    };
  }

  String _audienceLabel(AppLocalizations l10n, String value) {
    return switch (value) {
      'owner_only' => l10n.audienceOwnerOnly,
      'owner_manager' => l10n.audienceOwnerManager,
      'all' => l10n.audienceAll,
      _ => value,
    };
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return FScaffold(
      header: FHeader(title: Text(l10n.companyPoliciesTitle)),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  l10n.companyBalanceLabel(_balance?.toStringAsFixed(0) ?? '—'),
                  style: TextStyle(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 16),
                FTextField(
                  control: FTextFieldControl.managed(controller: _maxConcurrentCtrl),
                  label: Text(l10n.policiesMaxConcurrent),
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                ),
                const SizedBox(height: 12),
                FSwitch(
                  label: Text(l10n.policiesNoMonthlyLimit),
                  value: _noMonthlyLimit,
                  onChange: (v) => setState(() => _noMonthlyLimit = v),
                ),
                if (!_noMonthlyLimit) ...[
                  const SizedBox(height: 8),
                  FTextField(
                    control: FTextFieldControl.managed(controller: _monthlyLimitCtrl),
                    label: Text(l10n.policiesMonthlyLimit),
                    keyboardType: TextInputType.number,
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                  ),
                ],
                const SizedBox(height: 12),
                Text(l10n.policiesAllowedCategories, style: context.theme.typography.sm),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _categories.map((c) {
                    final selected = _selectedCategories.contains(c);
                    return FilterChip(
                      label: Text(c),
                      selected: selected,
                      onSelected: (v) {
                        setState(() {
                          if (v) {
                            _selectedCategories = [..._selectedCategories, c];
                          } else {
                            _selectedCategories = _selectedCategories.where((x) => x != c).toList();
                          }
                        });
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 12),
                FSwitch(
                  label: Text(l10n.policiesAllowDownload),
                  value: _allowDownload,
                  onChange: (v) => setState(() => _allowDownload = v),
                ),
                const SizedBox(height: 8),
                FSwitch(
                  label: Text(l10n.policiesAllowLinks),
                  value: _allowLinks,
                  onChange: (v) => setState(() => _allowLinks = v),
                ),
                const SizedBox(height: 8),
                FSwitch(
                  label: Text(l10n.policiesRequire2fa),
                  value: _require2fa,
                  onChange: (v) => setState(() => _require2fa = v),
                ),
                const SizedBox(height: 12),
                FTextField(
                  control: FTextFieldControl.managed(controller: _autoBlockCtrl),
                  label: Text(l10n.policiesAutoBlock),
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                ),
                const SizedBox(height: 12),
                FTextField(
                  control: FTextFieldControl.managed(controller: _lowBalanceCtrl),
                  label: Text(l10n.policiesLowBalanceThreshold),
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                ),
                const SizedBox(height: 20),
                Text(l10n.policiesNotifySection, style: context.theme.typography.sm),
                const SizedBox(height: 4),
                Text(
                  l10n.policiesNotifyHint,
                  style: context.theme.typography.xs.copyWith(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 12),
                ..._routing.keys.map((event) {
                  return Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: FSelect<String>(
                      label: Text(_eventLabel(l10n, event)),
                      control: FSelectControl.managed(
                        initial: _routing[event]!,
                        onChange: (v) {
                          if (v == null) return;
                          setState(() => _routing[event] = v);
                        },
                      ),
                      items: {
                        _audienceLabel(l10n, 'owner_only'): 'owner_only',
                        _audienceLabel(l10n, 'owner_manager'): 'owner_manager',
                        _audienceLabel(l10n, 'all'): 'all',
                      },
                    ),
                  );
                }),
                const SizedBox(height: 16),
                FButton(
                  onPress: _saving ? null : _save,
                  child: Text(_saving ? '…' : l10n.save),
                ),
              ],
            ),
    );
  }
}
