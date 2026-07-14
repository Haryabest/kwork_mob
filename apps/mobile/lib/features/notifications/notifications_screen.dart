import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/services/notification_inbox.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key, required this.api});

  final ApiClient api;

  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  List<InboxNotification> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final orders = await widget.api.listOrders();
      await NotificationInbox.instance.syncFromOrders(orders);
    } catch (_) {}
    _items = await NotificationInbox.instance.load();
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _open(InboxNotification n) async {
    await NotificationInbox.instance.markRead(n.id);
    if (!mounted) return;
    if (n.orderId != null) {
      context.push('/home/queue/${n.orderId}');
    } else if (n.modelUuid != null) {
      context.push('/home/models/${n.modelUuid}');
    }
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    return FScaffold(
      header: FHeader.nested(
        title: const Text('Уведомления'),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
        suffixes: [
          FHeaderAction(
            icon: const Icon(FIcons.check),
            onPress: _items.isEmpty
                ? null
                : () async {
                    await NotificationInbox.instance.markAllRead();
                    await _load();
                  },
          ),
        ],
      ),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
              ? const Center(child: Text('Нет уведомлений'))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView.separated(
                    padding: const EdgeInsets.all(16),
                    itemCount: _items.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, i) {
                      final n = _items[i];
                      return FCard.raw(
                        style: FCardStyleDelta.delta(
                          decoration: DecorationDelta.boxDelta(
                            color: n.read ? AppColors.surface : AppColors.accent.withValues(alpha: 0.06),
                          ),
                        ),
                        child: FTile(
                          title: Text(
                            n.title,
                            style: TextStyle(
                              fontWeight: n.read ? FontWeight.normal : FontWeight.w600,
                            ),
                          ),
                          subtitle: Text(
                            '${n.body}\n${_fmt(n.createdAt)}',
                            style: const TextStyle(fontSize: 12),
                          ),
                          details: n.read ? null : const Icon(FIcons.circle, size: 10, color: AppColors.accent),
                          onPress: () => _open(n),
                        ),
                      );
                    },
                  ),
                ),
    );
  }

  String _fmt(DateTime d) {
    final l = d.toLocal();
    return '${l.day.toString().padLeft(2, '0')}.${l.month.toString().padLeft(2, '0')} '
        '${l.hour.toString().padLeft(2, '0')}:${l.minute.toString().padLeft(2, '0')}';
  }
}
