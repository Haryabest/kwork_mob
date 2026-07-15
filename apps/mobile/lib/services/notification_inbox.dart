import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

class InboxNotification {
  InboxNotification({
    required this.id,
    required this.title,
    required this.body,
    required this.createdAt,
    this.orderId,
    this.modelUuid,
    this.type,
    this.read = false,
  });

  final String id;
  final String title;
  final String body;
  final DateTime createdAt;
  final String? orderId;
  final String? modelUuid;
  final String? type;
  final bool read;

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'body': body,
        'created_at': createdAt.toIso8601String(),
        if (orderId != null) 'order_id': orderId,
        if (modelUuid != null) 'model_uuid': modelUuid,
        if (type != null) 'type': type,
        'read': read,
      };

  static InboxNotification fromJson(Map<String, dynamic> j) => InboxNotification(
        id: j['id']?.toString() ?? '',
        title: j['title']?.toString() ?? '',
        body: j['body']?.toString() ?? '',
        createdAt: DateTime.tryParse(j['created_at']?.toString() ?? '') ?? DateTime.now(),
        orderId: j['order_id']?.toString(),
        modelUuid: j['model_uuid']?.toString(),
        type: j['type']?.toString(),
        read: j['read'] == true,
      );

  InboxNotification copyWith({bool? read}) => InboxNotification(
        id: id,
        title: title,
        body: body,
        createdAt: createdAt,
        orderId: orderId,
        modelUuid: modelUuid,
        type: type,
        read: read ?? this.read,
      );
}

/// Локальная история push / событий (§19.4.2).
class NotificationInbox {
  NotificationInbox._();
  static final instance = NotificationInbox._();

  static const _key = 'notification_inbox_v1';
  static const _max = 100;

  Future<List<InboxNotification>> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];
    try {
      final list = jsonDecode(raw) as List;
      return list
          .map((e) => InboxNotification.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList()
        ..sort((a, b) => b.createdAt.compareTo(a.createdAt));
    } catch (_) {
      return [];
    }
  }

  Future<int> unreadCount() async {
    final items = await load();
    return items.where((e) => !e.read).length;
  }

  Future<void> _save(List<InboxNotification> items) async {
    final prefs = await SharedPreferences.getInstance();
    final trimmed = items.take(_max).toList();
    await prefs.setString(
      _key,
      jsonEncode(trimmed.map((e) => e.toJson()).toList()),
    );
  }

  Future<void> add({
    required String title,
    required String body,
    String? orderId,
    String? modelUuid,
    String? type,
    String? id,
  }) async {
    final items = await load();
    final nid = id ?? '${DateTime.now().millisecondsSinceEpoch}_${orderId ?? modelUuid ?? type ?? 'n'}';
    if (items.any((e) => e.id == nid)) return;
    items.insert(
      0,
      InboxNotification(
        id: nid,
        title: title,
        body: body,
        createdAt: DateTime.now(),
        orderId: orderId,
        modelUuid: modelUuid,
        type: type,
      ),
    );
    await _save(items);
  }

  Future<void> markRead(String id) async {
    final items = await load();
    final i = items.indexWhere((e) => e.id == id);
    if (i < 0) return;
    items[i] = items[i].copyWith(read: true);
    await _save(items);
  }

  Future<void> markAllRead() async {
    final items = await load();
    await _save(items.map((e) => e.copyWith(read: true)).toList());
  }

  Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }

  Future<void> syncFromOrders(List<Map<String, dynamic>> orders) async {
    for (final o in orders) {
      final status = o['status']?.toString();
      final id = o['id']?.toString();
      if (id == null) continue;
      if (status == 'completed') {
        final model = o['model'] as Map?;
        await add(
          id: 'order_completed_$id',
          title: 'Генерация завершена',
          body: 'Заказ #$id готов к просмотру',
          orderId: id,
          modelUuid: model?['uuid']?.toString(),
          type: 'generation_done',
        );
      } else if (status == 'blocked_nsfw') {
        await add(
          id: 'order_nsfw_$id',
          title: 'NSFW-блокировка',
          body:
              'Заказ #$id отклонён. Средства возвращены. Аккаунт на проверке до 24 ч.',
          orderId: id,
          type: 'nsfw_blocked',
        );
      } else if (status == 'failed') {
        await add(
          id: 'order_failed_$id',
          title: 'Ошибка генерации',
          body: o['failure_reason']?.toString() ?? 'Заказ #$id не выполнен',
          orderId: id,
          type: 'generation_failed',
        );
        if ((o['amount'] as num?) != null && (o['amount'] as num) > 0) {
          await add(
            id: 'order_refund_$id',
            title: 'Возврат средств',
            body: 'По заказу #$id средства возвращены',
            orderId: id,
            type: 'refund',
          );
        }
      } else if (status == 'cancelled') {
        await add(
          id: 'order_cancelled_$id',
          title: 'Заказ отменён',
          body: 'Заказ #$id отменён',
          orderId: id,
          type: 'cancelled',
        );
      }
    }
  }
}
