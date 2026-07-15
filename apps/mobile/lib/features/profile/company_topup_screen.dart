import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/features/profile/low_balance_banner.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

/// §19.14.2 — пополнение корпоративного счёта (Owner).
class CompanyTopupScreen extends StatefulWidget {
  const CompanyTopupScreen({super.key, required this.api, required this.session});

  final ApiClient api;
  final AppSession session;

  @override
  State<CompanyTopupScreen> createState() => _CompanyTopupScreenState();
}

class _CompanyTopupScreenState extends State<CompanyTopupScreen> {
  double? _companyBalance;
  int _lowBalanceThreshold = 5000;
  bool _loading = true;
  bool _busy = false;
  final _amount = TextEditingController(text: '1000');
  Timer? _pollTimer;
  String? _pollPaymentId;

  @override
  void dispose() {
    _pollTimer?.cancel();
    _amount.dispose();
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
      final companies = await widget.api.listCompanyMine();
      final cid = widget.session.companyId;
      final match = companies.where((c) => c['id'] == cid).toList();
        if (match.isNotEmpty) {
          final b = match.first['balance'];
          _companyBalance = b is num ? b.toDouble() : null;
        }
        try {
          final settings = await widget.api.getCompanySettings();
          final pol = settings['policies'];
          if (pol is Map) {
            final thr = pol['low_balance_threshold'];
            if (thr is num) _lowBalanceThreshold = thr.toInt();
          }
        } catch (_) {}
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  void _startPaymentPoll(String paymentId) {
    _pollTimer?.cancel();
    _pollPaymentId = paymentId;
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) async {
      if (_pollPaymentId == null) return;
      try {
        final st = await widget.api.pollTopupPayment(_pollPaymentId!, company: true);
        final status = st['status']?.toString();
        if (status == 'succeeded') {
          _pollTimer?.cancel();
          _pollPaymentId = null;
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(AppLocalizations.of(context)!.companyTopupSuccess)),
            );
            await _load();
          }
        } else if (status == 'canceled') {
          _pollTimer?.cancel();
          _pollPaymentId = null;
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(AppLocalizations.of(context)!.paymentCanceled)),
            );
          }
        }
      } catch (_) {}
    });
  }

  Future<void> _topup({String method = 'redirect'}) async {
    final l10n = AppLocalizations.of(context)!;
    final amount = int.tryParse(_amount.text.trim());
    if (amount == null || amount < 100) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.topupMinAmount)),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final res = await widget.api.topupCompanyBalance(amount: amount, paymentMethod: method);
      if (method == 'sbp_qr') {
        final qrData = res['confirmation_data']?.toString();
        final paymentId = res['payment_id']?.toString() ?? res['id']?.toString();
        if (qrData != null && qrData.isNotEmpty && mounted) {
          if (paymentId != null) _startPaymentPoll(paymentId);
          await showFDialog<void>(
            context: context,
            builder: (ctx, style, animation) => FDialog(
              title: Text(l10n.sbpQrTitle),
              body: SizedBox(
                width: 260,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    QrImageView(data: qrData, size: 220),
                    const SizedBox(height: 8),
                    Text('${amount.toStringAsFixed(0)} ₽', style: context.theme.typography.lg),
                  ],
                ),
              ),
              actions: [
                FButton(onPress: () => Navigator.pop(ctx), child: Text(l10n.done)),
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

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    if (!widget.session.isOwner) {
      return FScaffold(
        header: FHeader.nested(
          title: Text(l10n.companyTopupTitle),
          prefixes: [FHeaderAction.back(onPress: () => context.pop())],
        ),
        child: Center(child: Text(l10n.balanceUnavailable)),
      );
    }

    final balance = _companyBalance ?? 0;
    return FScaffold(
      header: FHeader.nested(
        title: Text(l10n.companyTopupScreenTitle),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
      ),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  '${balance.toStringAsFixed(0)} ₽',
                  style: context.theme.typography.xl.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 4),
                Text(
                  widget.session.companyName ?? l10n.companyDefaultName,
                  style: TextStyle(color: AppColors.textSecondary),
                ),
                const SizedBox(height: 12),
                LowBalanceBanner(
                  balance: balance,
                  threshold: _lowBalanceThreshold,
                ),
                const SizedBox(height: 12),
                FTextField(
                  control: FTextFieldControl.managed(controller: _amount),
                  label: Text(l10n.topupAmount),
                  keyboardType: TextInputType.number,
                  inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                ),
                const SizedBox(height: 16),
                FButton(
                  onPress: _busy ? null : () => _topup(method: 'redirect'),
                  child: Text(_busy ? '…' : l10n.topup),
                ),
                const SizedBox(height: 8),
                FButton(
                  variant: .outline,
                  onPress: _busy ? null : () => _topup(method: 'sbp_qr'),
                  child: Text(_busy ? '…' : l10n.topupSbpQr),
                ),
                const SizedBox(height: 16),
                Text(
                  l10n.companyTopupScreenHint,
                  style: TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
              ],
            ),
    );
  }
}
