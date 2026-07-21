import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Офлайн-очередь действий §19.18 / §19.20 — flush при восстановлении сети.
class OfflineSyncService {
  OfflineSyncService._();
  static final instance = OfflineSyncService._();

  static const _key = 'offline_action_queue_v1';
  static const _max = 100;

  bool isOnline = true;
  final listeners = <VoidCallback>[];

  void addListener(VoidCallback fn) => listeners.add(fn);
  void removeListener(VoidCallback fn) => listeners.remove(fn);

  void _notify() {
    for (final fn in List<VoidCallback>.from(listeners)) {
      fn();
    }
  }

  Future<bool> probe(ApiClient api) async {
    final ok = await api.pingHealth();
    if (ok != isOnline) {
      isOnline = ok;
      _notify();
    }
    return ok;
  }

  Future<List<Map<String, dynamic>>> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return [];
    try {
      return (jsonDecode(raw) as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> _save(List<Map<String, dynamic>> items) async {
    final prefs = await SharedPreferences.getInstance();
    while (items.length > _max) {
      items.removeAt(0);
    }
    await prefs.setString(_key, jsonEncode(items));
  }

  Future<void> enqueue(String type, Map<String, dynamic> payload) async {
    final items = await _load();
    items.add({
      'type': type,
      'payload': payload,
      'ts': DateTime.now().toUtc().toIso8601String(),
    });
    await _save(items);
  }

  Future<int> pendingCount() async => (await _load()).length;

  Future<void> queueNotificationRead(int notificationId) async {
    await enqueue('notification_read', {'notification_id': notificationId});
  }

  Future<void> flush(ApiClient api) async {
    if (!await probe(api)) return;

    await AnalyticsService.instance.flush(api);

    var items = await _load();
    if (items.isEmpty) return;

    final remaining = <Map<String, dynamic>>[];
    for (final item in items) {
      final type = item['type']?.toString() ?? '';
      final payload = Map<String, dynamic>.from(item['payload'] as Map? ?? {});
      try {
        switch (type) {
          case 'notification_read':
            final id = (payload['notification_id'] as num?)?.toInt();
            if (id != null) await api.markNotificationRead(id);
            break;
          default:
            break;
        }
      } catch (e) {
        if (isNetworkError(e)) {
          remaining.add(item);
          break;
        }
      }
    }
    if (remaining.length != items.length) {
      await _save(remaining);
    }
  }
}
