import 'dart:io' show Platform;

import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/scale_calibration_service.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';
import 'package:kwork_mobile/widgets/order_limit_dialog.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:url_launcher/url_launcher.dart';

/// Оплата заказа физлица §19.8.1 — тариф, апсейлы, ФИО, ЮKassa / СБП.
class OrderCheckoutScreen extends StatefulWidget {
  const OrderCheckoutScreen({
    super.key,
    required this.api,
    required this.session,
    required this.modelUuid,
  });

  final ApiClient api;
  final AppSession session;
  final String modelUuid;

  @override
  State<OrderCheckoutScreen> createState() => _OrderCheckoutScreenState();
}

class _OrderCheckoutScreenState extends State<OrderCheckoutScreen> {
  ShootDraft? _draft;
  List<Map<String, dynamic>> _upsells = [];
  List<Map<String, dynamic>> _tariffs = [];
  final _selectedUpsells = <String>{};
  final _promo = TextEditingController();
  final _fio = TextEditingController();
  bool _loading = true;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _boot();
  }

  @override
  void dispose() {
    _promo.dispose();
    _fio.dispose();
    super.dispose();
  }

  Future<void> _boot() async {
    try {
      final draft = await ShootStorage.instance.loadDraft(widget.modelUuid);
      if (draft == null || !draft.photosUploaded) {
        throw StateError('Сначала загрузите 12 фото');
      }
      final cal = await ScaleCalibrationService.instance.scaleForOrder();
      if (cal != null && draft.scaleCalibration == null) {
        draft.scaleCalibration = cal;
        await ShootStorage.instance.writeMetadata(draft);
      }
      final ups = await widget.api.listUpsells();
      final tariffs = await widget.api.listTariffs();
      if (mounted) {
        setState(() {
          _draft = draft;
          _upsells = ups;
          _tariffs = tariffs;
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = formatApiError(e);
          _loading = false;
        });
      }
    }
  }

  int get _baseAmount {
    final draft = _draft;
    if (draft == null) return 0;
    for (final t in _tariffs) {
      if (t['code'] == draft.tier.api) {
        return (t['amount_rub'] as num?)?.toInt() ?? draft.tier.priceRub;
      }
    }
    return draft.tier.priceRub;
  }

  int get _upsellTotal {
    var sum = 0;
    for (final u in _upsells) {
      if (_selectedUpsells.contains(u['code'])) {
        sum += (u['amount_rub'] as num?)?.toInt() ?? 0;
      }
    }
    return sum;
  }

  int get _total => _baseAmount + _upsellTotal;

  Future<void> _submit({required String payMethod}) async {
    final draft = _draft;
    if (draft == null || _busy) return;

    if (_selectedUpsells.contains('real_scale')) {
      final cal = draft.scaleCalibration ??
          await ScaleCalibrationService.instance.scaleForOrder();
      if (cal == null) {
        final l10n = AppLocalizations.of(context)!;
        final ok = await showFDialog<bool>(
          context: context,
          builder: (ctx, style, animation) => FDialog(
            title: Text(l10n.checkoutNeedCalibration),
            body: Text(l10n.checkoutCalibrationBody),
            actions: [
              FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
              FButton(
                onPress: () => Navigator.pop(ctx, true),
                child: Text(l10n.checkoutCalibrate),
              ),
            ],
          ),
        );
        if (ok == true && mounted) {
          await context.push<bool>('/home/calibration');
          await _boot();
        }
        return;
      }
      draft.scaleCalibration = cal;
    }

    setState(() {
      _busy = true;
      _error = null;
    });

    try {
      final order = await widget.api.createOrder(
        taskUuid: draft.modelUuid,
        category: draft.category,
        tier: draft.tier,
        companyId: widget.session.companyId,
        promocode: _promo.text.trim().isEmpty ? null : _promo.text.trim(),
        forbidden: draft.forbidden,
        birthDate: draft.birthDate,
        scaleCalibration: draft.scaleCalibration,
        photosPrefix: draft.photosPrefix,
        zipSha256: draft.zipSha256,
        upsells: _selectedUpsells.toList(),
        customerName: _fio.text.trim().isEmpty ? null : _fio.text.trim(),
        modelDisplayName: draft.displayName,
        deviceModel: Platform.isIOS
            ? 'iOS'
            : (Platform.isAndroid ? 'Android' : Platform.operatingSystem),
        osVersion: Platform.operatingSystemVersion,
      );

      final orderId = order['id'] as int;
      final status = order['status']?.toString();

      if (status == 'queued' || order['paid_from_balance'] == true) {
        await ShootStorage.instance.clearActiveDraft();
        if (!mounted) return;
        context.go('/home/queue/$orderId');
        return;
      }

      if (widget.session.hidePrices) {
        await ShootStorage.instance.clearActiveDraft();
        if (!mounted) return;
        context.go('/home/queue/$orderId');
        return;
      }

      final pay = await widget.api.payOrder(
        orderId: orderId,
        paymentMethod: payMethod,
        customerName: _fio.text.trim().isEmpty ? null : _fio.text.trim(),
      );

      if (pay['paid_from_balance'] == true) {
        await ShootStorage.instance.clearActiveDraft();
        if (!mounted) return;
        context.go('/home/queue/$orderId');
        return;
      }

      if (payMethod == 'sbp_qr') {
        final qrData = pay['confirmation_data']?.toString();
        if (qrData != null && qrData.isNotEmpty && mounted) {
          await showFDialog<void>(
            context: context,
            builder: (ctx, style, animation) => FDialog(
              title: Text(AppLocalizations.of(context)!.checkoutSbpOrderTitle),
              body: SizedBox(
                width: 260,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    QrImageView(data: qrData, size: 220),
                    const SizedBox(height: 8),
                    Text('$_total ₽', style: context.theme.typography.lg),
                  ],
                ),
              ),
              actions: [
                FButton(onPress: () => Navigator.pop(ctx), child: Text(AppLocalizations.of(context)!.done)),
              ],
            ),
          );
        }
      } else {
        final url = pay['confirmation_url']?.toString();
        if (url != null && url.isNotEmpty) {
          await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
        }
      }

      await ShootStorage.instance.clearActiveDraft();
      if (!mounted) return;
      context.go('/home/queue/$orderId');
    } catch (e) {
      final msg = formatApiError(e);
      if (isOrderLimitError(msg) && mounted) {
        await showOrderLimitDialog(context);
      }
      if (mounted) setState(() => _error = msg);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final hidePrices = widget.session.hidePrices;
    if (_loading) {
      return const FScaffold(child: Center(child: CircularProgressIndicator()));
    }
    if (_error != null && _draft == null) {
      return FScaffold(
        header: FHeader.nested(title: Text(l10n.checkoutTitle)),
        child: Center(child: Text(_error!)),
      );
    }
    final draft = _draft!;
    return FScaffold(
      header: FHeader.nested(
        title: Text(hidePrices ? l10n.checkoutSubmitGeneration : l10n.checkoutPayTitle),
        prefixes: [FHeaderAction.back(onPress: _busy ? null : () => context.pop())],
      ),
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(l10n.checkoutCategory(draft.category.label), style: context.theme.typography.sm),
          Text(l10n.checkoutTier(draft.tier.label), style: context.theme.typography.sm),
          if (!hidePrices) ...[
            const SizedBox(height: 12),
            Text(l10n.checkoutBasePrice('$_baseAmount')),
            const SizedBox(height: 16),
            Text(l10n.checkoutUpsells, style: context.theme.typography.sm),
            ..._upsells.map((u) {
              final code = u['code']?.toString() ?? '';
              return Padding(
                padding: const EdgeInsets.only(top: 8),
                child: FSwitch(
                  label: Text('${u['title']} · ${u['amount_rub']} ₽'),
                  value: _selectedUpsells.contains(code),
                  onChange: (v) {
                    setState(() {
                      if (v) {
                        _selectedUpsells.add(code);
                      } else {
                        _selectedUpsells.remove(code);
                      }
                    });
                  },
                ),
              );
            }),
            const Divider(height: 24),
            Text(
              l10n.checkoutTotal('$_total'),
              style: context.theme.typography.lg.copyWith(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 16),
            FTextField(
              control: FTextFieldControl.managed(controller: _promo),
              label: Text(l10n.checkoutPromo),
              enabled: !_busy,
            ),
            const SizedBox(height: 12),
            FTextField(
              control: FTextFieldControl.managed(controller: _fio),
              label: Text(l10n.checkoutFioOptional),
              hint: l10n.checkoutFioHint,
              enabled: !_busy,
            ),
            const SizedBox(height: 8),
            Text(
              l10n.checkoutFioTaxHint,
              style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: AppColors.error)),
          ],
          const SizedBox(height: 24),
          if (hidePrices)
            FButton(
              onPress: _busy ? null : () => _submit(payMethod: 'redirect'),
              child: Text(_busy ? '…' : l10n.checkoutSubmitGeneration),
            )
          else ...[
            FButton(
              onPress: _busy ? null : () => _submit(payMethod: 'redirect'),
              child: Text(_busy ? '…' : l10n.checkoutPayCard),
            ),
            const SizedBox(height: 8),
            FButton(
              variant: .outline,
              onPress: _busy ? null : () => _submit(payMethod: 'sbp_qr'),
              child: Text(_busy ? '…' : l10n.checkoutPaySbp),
            ),
          ],
        ],
      ),
    );
  }
}
