import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

class BalanceScreen extends StatefulWidget {
  const BalanceScreen({super.key, required this.api, required this.session});

  final ApiClient api;
  final AppSession session;

  @override
  State<BalanceScreen> createState() => _BalanceScreenState();
}

class _BalanceScreenState extends State<BalanceScreen> {
  List<Map<String, dynamic>> _tx = [];
  List<Map<String, dynamic>> _members = [];
  double? _companyBalance;
  int _authorFilter = -1;
  bool _loading = true;
  bool _busy = false;
  final _amount = TextEditingController(text: '1000');
  final _dateFrom = TextEditingController();
  final _dateTo = TextEditingController();
  String _txType = 'all';
  int _pageSize = 20;
  int _page = 1;
  int _total = 0;
  Timer? _pollTimer;
  String? _pollPaymentId;
  bool _pollCompany = false;

  bool get _corporateFinance =>
      widget.session.corporate && widget.session.canViewFinance;

  @override
  void dispose() {
    _pollTimer?.cancel();
    _amount.dispose();
    _dateFrom.dispose();
    _dateTo.dispose();
    super.dispose();
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _authorLabel(int? userId) {
    if (userId == null) return '';
    for (final m in _members) {
      if (m['user_id'] == userId) {
        return m['full_name']?.toString() ?? m['email']?.toString() ?? '#$userId';
      }
    }
    return '#$userId';
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final offset = (_page - 1) * _pageSize;
      if (_corporateFinance) {
        final companies = await widget.api.listCompanyMine();
        final cid = widget.session.companyId;
        final match = companies.where((c) => c['id'] == cid).toList();
        if (match.isNotEmpty) {
          final b = match.first['balance'];
          _companyBalance = b is num ? b.toDouble() : null;
        }
        if (widget.session.canFilterCompanyOrders) {
          final m = await widget.api.listCompanyMembers();
          final raw = m['items'] as List? ?? [];
          _members = raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        }
        final page = await widget.api.listCompanyTransactionsPage(
          userId: _authorFilter >= 0 ? _authorFilter : null,
          dateFrom: _dateFrom.text.trim().isEmpty ? null : _dateFrom.text.trim(),
          dateTo: _dateTo.text.trim().isEmpty ? null : _dateTo.text.trim(),
          type: _txType,
          limit: _pageSize,
          offset: offset,
        );
        _total = (page['total'] as num?)?.toInt() ?? 0;
        final items = page['items'] as List? ?? [];
        _tx = items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      } else {
        final me = await widget.api.me();
        widget.session.applyMe(me);
        final page = await widget.api.listTransactionsPage(
          dateFrom: _dateFrom.text.trim().isEmpty ? null : _dateFrom.text.trim(),
          dateTo: _dateTo.text.trim().isEmpty ? null : _dateTo.text.trim(),
          type: _txType,
          limit: _pageSize,
          offset: offset,
        );
        _total = (page['total'] as num?)?.toInt() ?? 0;
        final items = page['items'] as List? ?? [];
        _tx = items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        _companyBalance = null;
      }
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  void _resetPageAndLoad() {
    _page = 1;
    _load();
  }

  Future<void> _pickDate(TextEditingController ctrl) async {
    final now = DateTime.now();
    final initial = DateTime.tryParse(ctrl.text.trim()) ?? now;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial.isAfter(now) ? now : initial,
      firstDate: DateTime(2020),
      lastDate: now,
    );
    if (picked == null) return;
    ctrl.text =
        '${picked.year.toString().padLeft(4, '0')}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}';
  }

  bool get _canTopup => !_corporateFinance || widget.session.isOwner;

  void _startPaymentPoll(String paymentId, {required bool company}) {
    _pollTimer?.cancel();
    _pollPaymentId = paymentId;
    _pollCompany = company;
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) async {
      if (_pollPaymentId == null) return;
      try {
        final st = await widget.api.pollTopupPayment(
          _pollPaymentId!,
          company: _pollCompany,
        );
        final status = st['status']?.toString();
        if (status == 'succeeded') {
          _pollTimer?.cancel();
          _pollPaymentId = null;
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Баланс пополнен')),
            );
            await _load();
          }
        } else if (status == 'canceled') {
          _pollTimer?.cancel();
          _pollPaymentId = null;
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Платёж отменён')),
            );
          }
        }
      } catch (_) {}
    });
  }

  Future<void> _topup({String method = 'redirect'}) async {
    final amount = int.tryParse(_amount.text.trim());
    if (amount == null || amount < 100) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Минимум 100 ₽')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final companyTopup = _corporateFinance && widget.session.isOwner;
      final res = companyTopup
          ? await widget.api.topupCompanyBalance(amount: amount, paymentMethod: method)
          : await widget.api.topupBalance(amount: amount, paymentMethod: method);
      if (res['dev_mock'] == true) {
        await _load();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Баланс: ${res['balance']} ₽')),
          );
        }
        return;
      }
      if (method == 'sbp_qr') {
        final qrData = res['confirmation_data']?.toString();
        final paymentId = res['payment_id']?.toString() ?? res['id']?.toString();
        if (qrData != null && qrData.isNotEmpty && mounted) {
          if (paymentId != null) {
            _startPaymentPoll(paymentId, company: companyTopup);
          }
          await showFDialog<void>(
            context: context,
            builder: (ctx, style, animation) => FDialog(
              title: const Text('СБП — отсканируйте QR'),
              body: SizedBox(
                width: 260,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    QrImageView(data: qrData, size: 220),
                    const SizedBox(height: 8),
                    Text('${amount.toStringAsFixed(0)} ₽', style: context.theme.typography.lg),
                    const SizedBox(height: 4),
                    const Text(
                      'Статус обновится автоматически',
                      style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
                    ),
                  ],
                ),
              ),
              actions: [
                FButton(
                  variant: .outline,
                  onPress: () {
                    Clipboard.setData(ClipboardData(text: qrData));
                    Navigator.pop(ctx);
                  },
                  child: const Text('Скопировать payload'),
                ),
                FButton(onPress: () => Navigator.pop(ctx), child: const Text('Готово')),
              ],
            ),
          );
        }
        return;
      }
      final url = res['confirmation_url']?.toString();
      if (url != null && url.isNotEmpty) {
        await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  int get _totalPages => _total <= 0 ? 1 : ((_total + _pageSize - 1) ~/ _pageSize);

  @override
  Widget build(BuildContext context) {
    if (widget.session.hidePrices) {
      return const FScaffold(
        header: FHeader(title: Text('Баланс')),
        child: Center(child: Text('Баланс недоступен для вашей роли')),
      );
    }
    final balance = _corporateFinance
        ? (_companyBalance ?? 0)
        : (widget.session.balance ?? 0);
    return FScaffold(
      header: FHeader(
        title: Text(_corporateFinance ? 'Баланс компании' : 'Баланс'),
      ),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  Text(
                    '${balance.toStringAsFixed(0)} ₽',
                    style: context.theme.typography.xl.copyWith(fontWeight: FontWeight.bold),
                  ),
                  if (_corporateFinance) ...[
                    const SizedBox(height: 8),
                    Text(
                      widget.session.companyName ?? 'Компания',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                  ],
                  if (_canTopup) ...[
                    const SizedBox(height: 16),
                    FTextField(
                      control: FTextFieldControl.managed(controller: _amount),
                      label: Text(_corporateFinance ? 'Пополнение компании §19.14.2' : 'Сумма пополнения'),
                      keyboardType: TextInputType.number,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    ),
                    const SizedBox(height: 12),
                    FButton(
                      onPress: _busy ? null : () => _topup(method: 'redirect'),
                      child: Text(_busy ? '…' : 'Пополнить картой'),
                    ),
                    const SizedBox(height: 8),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : () => _topup(method: 'sbp_qr'),
                      child: Text(_busy ? '…' : 'СБП QR'),
                    ),
                  ],
                  const SizedBox(height: 16),
                  GestureDetector(
                    onTap: () => _pickDate(_dateFrom),
                    child: AbsorbPointer(
                      child: FTextField(
                        control: FTextFieldControl.managed(controller: _dateFrom),
                        label: const Text('Дата от'),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  GestureDetector(
                    onTap: () => _pickDate(_dateTo),
                    child: AbsorbPointer(
                      child: FTextField(
                        control: FTextFieldControl.managed(controller: _dateTo),
                        label: const Text('Дата до'),
                      ),
                    ),
                  ),
                  const SizedBox(height: 8),
                  FSelect<String>(
                    label: const Text('Тип операции'),
                    control: FSelectControl.managed(
                      initial: _txType,
                      onChange: (v) {
                        if (v == null) return;
                        setState(() => _txType = v);
                        _resetPageAndLoad();
                      },
                    ),
                    items: const {
                      'Все': 'all',
                      'Пополнения': 'topup',
                      'Списания': 'charge',
                      'Возвраты': 'refund',
                    },
                  ),
                  const SizedBox(height: 8),
                  FSelect<int>(
                    label: const Text('На странице §20.3.4'),
                    control: FSelectControl.managed(
                      initial: _pageSize,
                      onChange: (v) {
                        if (v == null) return;
                        setState(() => _pageSize = v);
                        _resetPageAndLoad();
                      },
                    ),
                    items: const {'20': 20, '50': 50, '100': 100},
                  ),
                  const SizedBox(height: 8),
                  FButton(
                    variant: .outline,
                    onPress: _resetPageAndLoad,
                    child: const Text('Применить фильтры'),
                  ),
                  const SizedBox(height: 16),
                  if (_corporateFinance &&
                      widget.session.canFilterCompanyOrders &&
                      _members.isNotEmpty) ...[
                    FSelect<int>(
                      label: const Text('Сотрудник §8'),
                      control: FSelectControl.managed(
                        initial: _authorFilter,
                        onChange: (v) {
                          setState(() => _authorFilter = v ?? -1);
                          _resetPageAndLoad();
                        },
                      ),
                      items: {
                        'Все': -1,
                        for (final m in _members)
                          _authorLabel(m['user_id'] as int?): m['user_id'] as int,
                      },
                    ),
                    const SizedBox(height: 16),
                  ],
                  Text('Транзакции', style: context.theme.typography.lg),
                  Text(
                    'Всего: $_total',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                  ),
                  const SizedBox(height: 8),
                  if (_tx.isEmpty)
                    Text('Нет операций', style: TextStyle(color: context.theme.colors.mutedForeground))
                  else
                    FTileGroup(
                      children: [
                        for (final t in _tx)
                          FTile(
                            title: Text('${t['type']} · ${t['amount']} ₽'),
                            subtitle: Text(
                              [
                                t['status_label']?.toString() ?? 'Успешно',
                                t['description']?.toString() ?? '',
                              ].where((s) => s.isNotEmpty).join(' · '),
                            ),
                            details: Text(
                              [
                                if (_corporateFinance && t['user_id'] != null)
                                  _authorLabel(t['user_id'] as int?),
                                t['created_at']?.toString().substring(0, 10) ?? '',
                              ].where((s) => s.isNotEmpty).join(' · '),
                              style: context.theme.typography.xs,
                            ),
                          ),
                      ],
                    ),
                  if (_totalPages > 1) ...[
                    const SizedBox(height: 12),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        FButton(
                          variant: .outline,
                          onPress: _page > 1
                              ? () {
                                  setState(() => _page -= 1);
                                  _load();
                                }
                              : null,
                          child: const Text('←'),
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          child: Text('$_page / $_totalPages'),
                        ),
                        FButton(
                          variant: .outline,
                          onPress: _page < _totalPages
                              ? () {
                                  setState(() => _page += 1);
                                  _load();
                                }
                              : null,
                          child: const Text('→'),
                        ),
                      ],
                    ),
                  ],
                ],
              ),
            ),
    );
  }
}
