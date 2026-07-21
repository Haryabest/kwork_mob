import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
import 'package:kwork_mobile/core/queue_ws.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/core/ws_errors.dart';
import 'package:kwork_mobile/services/local_model_library.dart';

/// Экран очереди / генерации (§3.4.1–3.4.2).
class QueueScreen extends StatefulWidget {
  const QueueScreen({
    super.key,
    required this.api,
    required this.session,
    this.orderId,
  });

  final ApiClient api;
  final AppSession session;
  final int? orderId;

  @override
  State<QueueScreen> createState() => _QueueScreenState();
}

class _QueueScreenState extends State<QueueScreen> {
  late final QueueWsClient _ws;
  Map<String, dynamic>? _order;
  String? _error;

  @override
  void initState() {
    super.initState();
    AnalyticsService.instance.track('screen_view', {'screen': 'queue'});
    _ws = QueueWsClient(wsBaseUrl: widget.api.wsBaseUrl);
    _ws.addListener(_onWs);
    _boot();
  }

  Future<void> _boot() async {
    try {
      if (widget.orderId != null) {
        _order = await widget.api.getOrder(widget.orderId!);
      }
      final uid = widget.session.userId;
      final token = await widget.api.accessToken;
      if (uid != null && token != null) {
        await _ws.connect(userId: uid, token: token);
      }
      if (mounted) setState(() {});
    } catch (e) {
      setState(() => _error = formatApiError(e));
    }
  }

  void _onWs() {
    final ev = _ws.lastEvent;
    if (ev == null || !mounted) return;
    if (widget.orderId != null &&
        ev['order_id'] != null &&
        ev['order_id'] != widget.orderId) {
      return;
    }
    setState(() {
      _order = {
        ...?_order,
        'status': ev['status'] ?? _order?['status'],
        'queue_position': ev['queue_position'] ?? _order?['queue_position'],
        'ewt_sec': ev['ewt_sec'] ?? ev['estimated_wait_seconds'] ?? _order?['ewt_sec'],
      };
    });
    if (ev['status'] == 'cancelled' || _order?['status'] == 'cancelled') {
      context.go('/home');
      return;
    }
    if (ev['status'] == 'completed' || _order?['status'] == 'completed') {
      final model = _order?['model'] as Map?;
      final uuid = model?['uuid']?.toString();
      if (uuid != null) {
        LocalModelLibrary.instance.downloadIfNeeded(api: widget.api, modelUuid: uuid);
        context.go('/home/models/$uuid');
      } else {
        _refresh();
      }
    }
  }

  Future<void> _refresh() async {
    if (widget.orderId == null) return;
    AnalyticsService.instance.track('screen_view', {'screen': 'queue_refresh'});
    _order = await widget.api.getOrder(widget.orderId!);
    if (!mounted) return;
    setState(() {});
    final model = _order?['model'] as Map?;
    if (_order?['status'] == 'completed' && model?['uuid'] != null) {
      final uuid = model!['uuid'].toString();
      LocalModelLibrary.instance.downloadIfNeeded(api: widget.api, modelUuid: uuid);
      context.go('/home/models/$uuid');
    }
  }

  Future<void> _cancel() async {
    if (widget.orderId == null) return;
    final l10n = AppLocalizations.of(context)!;
    final status = _order?['status']?.toString();
    if (status == 'processing' || status == 'generating') {
      var ack = false;
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setLocal) => AlertDialog(
            title: Text(l10n.queueCancelTitle),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(l10n.queueCancelWarning),
                CheckboxListTile(
                  value: ack,
                  onChanged: (v) => setLocal(() => ack = v ?? false),
                  title: Text(l10n.queueUnderstand),
                ),
              ],
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(l10n.no)),
              TextButton(
                onPressed: ack ? () => Navigator.pop(ctx, true) : null,
                child: Text(l10n.yes),
              ),
            ],
          ),
        ),
      );
      if (ok != true) return;
      AnalyticsService.instance.track('screen_view', {'screen': 'queue_cancel_ack'});
    }
    AnalyticsService.instance.track('screen_view', {'screen': 'queue_cancel'});
    final processing = status == 'processing' || status == 'generating';
    await widget.api.cancelOrder(widget.orderId!, ackNoRefund: processing);
    if (!mounted) return;
    context.go('/home');
  }

  Future<void> _reconnectWs() async {
    AnalyticsService.instance.track('screen_view', {'screen': 'queue_reconnect_ws'});
    try {
      final uid = widget.session.userId;
      final token = await widget.api.accessToken;
      if (uid != null && token != null) {
        await _ws.connect(userId: uid, token: token);
      }
      if (mounted) setState(() {});
    } catch (e) {
      if (mounted) setState(() => _error = formatApiError(e));
    }
  }

  @override
  void dispose() {
    _ws.removeListener(_onWs);
    _ws.dispose();
    super.dispose();
  }

  String _statusLabel(AppLocalizations l10n, String status) {
    switch (status) {
      case 'blocked_nsfw':
        return l10n.orderStatusBlockedNsfw;
      case 'completed':
        return l10n.orderStatusCompleted;
      case 'failed':
        return l10n.orderStatusFailed;
      case 'processing':
        return l10n.orderStatusProcessing;
      case 'queued':
        return l10n.orderStatusQueued;
      case 'cancelled':
        return l10n.orderStatusCancelled;
      default:
        return status;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final pos = _order?['queue_position'];
    final ewt = _order?['ewt_sec'];
    final status = _order?['status']?.toString() ?? '…';
    final ewtMin = ewt is num ? (ewt / 60).ceil() : null;
    final isNsfwBlocked = status == 'blocked_nsfw';

    return FScaffold(
      header: FHeader.nested(
        title: Text(l10n.queueGenerationTitle),
        prefixes: [FHeaderAction.back(onPress: () => context.go('/home'))],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Text(_error!, style: const TextStyle(color: AppColors.error)),
              ),
            if (_ws.lastError != null) ...[
              Text(formatWsError(_ws.lastError!, l10n), style: const TextStyle(color: AppColors.error)),
              const SizedBox(height: 8),
              FButton(
                variant: .outline,
                onPress: _reconnectWs,
                child: Text(l10n.queueReconnectWs),
              ),
              const SizedBox(height: 12),
            ],
            if (isNsfwBlocked) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppColors.error.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.error.withValues(alpha: 0.35)),
                ),
                child: Text(
                  l10n.queueNsfwBlocked,
                  style: const TextStyle(color: AppColors.error),
                ),
              ),
              const SizedBox(height: 12),
            ],
            Text(l10n.queueStatus(_statusLabel(l10n, status)), style: context.theme.typography.lg),
            const SizedBox(height: 12),
            if (pos != null)
              Text(l10n.queuePosition('$pos', '${ewtMin ?? '—'}')),
            const SizedBox(height: 16),
            LinearProgressIndicator(
              value: pos is int && pos > 0 ? (1 / (pos + 1)).clamp(0.05, 0.95) : null,
              color: AppColors.accent,
            ),
            const SizedBox(height: 8),
            Text(
              _ws.connected
                  ? l10n.queueWsConnected
                  : (_ws.lastError != null ? l10n.queueWsErrorShort : l10n.queueWsConnecting),
              style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
            ),
            const Spacer(),
            FButton(variant: .outline, onPress: _refresh, child: Text(l10n.queueRefresh)),
            const SizedBox(height: 8),
            FButton(
              variant: .destructive,
              onPress: widget.orderId == null || isNsfwBlocked ? null : _cancel,
              child: Text(l10n.queueCancelOrder),
            ),
          ],
        ),
      ),
    );
  }
}
