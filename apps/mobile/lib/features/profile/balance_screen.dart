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
  bool _loading = true;
  bool _busy = false;
  final _amount = TextEditingController(text: '1000');

  @override
  void dispose() {
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
      final me = await widget.api.me();
      widget.session.applyMe(me);
      _tx = await widget.api.listTransactions();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
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
      final res = await widget.api.topupBalance(amount: amount, paymentMethod: method);
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
        if (qrData != null && qrData.isNotEmpty && mounted) {
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

  @override
  Widget build(BuildContext context) {
    if (widget.session.hidePrices) {
      return const FScaffold(
        header: FHeader(title: Text('Баланс')),
        child: Center(child: Text('Баланс недоступен для вашей роли')),
      );
    }
    final balance = widget.session.balance ?? 0;
    return FScaffold(
      header: const FHeader(title: Text('Баланс')),
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
                  const SizedBox(height: 16),
                  FTextField(
                    control: FTextFieldControl.managed(controller: _amount),
                    label: const Text('Сумма пополнения'),
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
                  const SizedBox(height: 24),
                  Text('Транзакции', style: context.theme.typography.lg),
                  const SizedBox(height: 8),
                  if (_tx.isEmpty)
                    Text('Нет операций', style: TextStyle(color: context.theme.colors.mutedForeground))
                  else
                    FTileGroup(
                      children: [
                        for (final t in _tx)
                          FTile(
                            title: Text('${t['type']} · ${t['amount']} ₽'),
                            subtitle: Text(t['description']?.toString() ?? ''),
                            details: Text(
                              t['created_at']?.toString().substring(0, 10) ?? '',
                              style: context.theme.typography.xs,
                            ),
                          ),
                      ],
                    ),
                ],
              ),
            ),
    );
  }
}
