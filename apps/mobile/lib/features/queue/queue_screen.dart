import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/queue_ws.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';

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
      setState(() => _error = e.toString());
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
    if (ev['status'] == 'completed' || _order?['status'] == 'completed') {
      final model = _order?['model'] as Map?;
      final uuid = model?['uuid']?.toString();
      if (uuid != null) {
        context.go('/home/models/$uuid');
      } else {
        _refresh();
      }
    }
  }

  Future<void> _refresh() async {
    if (widget.orderId == null) return;
    _order = await widget.api.getOrder(widget.orderId!);
    if (!mounted) return;
    setState(() {});
    final model = _order?['model'] as Map?;
    if (_order?['status'] == 'completed' && model?['uuid'] != null) {
      context.go('/home/models/${model!['uuid']}');
    }
  }

  Future<void> _cancel() async {
    if (widget.orderId == null) return;
    final status = _order?['status']?.toString();
    if (status == 'processing' || status == 'generating') {
      var ack = false;
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => StatefulBuilder(
          builder: (ctx, setLocal) => AlertDialog(
            title: const Text('Отмена генерации'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'Внимание! Отмена во время генерации не приводит к возврату средств, так как вычислительные ресурсы уже затрачены. Отменить?',
                ),
                CheckboxListTile(
                  value: ack,
                  onChanged: (v) => setLocal(() => ack = v ?? false),
                  title: const Text('Я понимаю'),
                ),
              ],
            ),
            actions: [
              TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Нет')),
              TextButton(
                onPressed: ack ? () => Navigator.pop(ctx, true) : null,
                child: const Text('Да'),
              ),
            ],
          ),
        ),
      );
      if (ok != true) return;
    }
    await widget.api.cancelOrder(widget.orderId!);
    await _refresh();
  }

  @override
  void dispose() {
    _ws.removeListener(_onWs);
    _ws.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final pos = _order?['queue_position'];
    final ewt = _order?['ewt_sec'];
    final status = _order?['status']?.toString() ?? '…';
    final ewtMin = ewt is num ? (ewt / 60).ceil() : null;

    return FScaffold(
      header: FHeader.nested(
        title: const Text('Генерация модели'),
        prefixes: [FHeaderAction.back(onPress: () => context.go('/home'))],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_error != null) Text(_error!, style: const TextStyle(color: AppColors.error)),
            Text('Статус: $status', style: context.theme.typography.lg),
            const SizedBox(height: 12),
            if (pos != null)
              Text(
                'Позиция в очереди: $pos. Примерное время ожидания: ${ewtMin ?? '—'} мин',
              ),
            const SizedBox(height: 16),
            LinearProgressIndicator(
              value: pos is int && pos > 0 ? (1 / (pos + 1)).clamp(0.05, 0.95) : null,
              color: AppColors.wbPrimary,
            ),
            const SizedBox(height: 8),
            Text(
              _ws.connected ? 'WebSocket: подключено' : 'WebSocket: …',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
            ),
            const Spacer(),
            FButton(variant: .outline, onPress: _refresh, child: const Text('Обновить')),
            const SizedBox(height: 8),
            FButton(
              variant: .destructive,
              onPress: widget.orderId == null ? null : _cancel,
              child: const Text('Отменить'),
            ),
          ],
        ),
      ),
    );
  }
}
