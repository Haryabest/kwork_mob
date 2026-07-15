import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Очередь аналитики §19.20 — локально, flush при online.
class AnalyticsService {
  AnalyticsService._();
  static final instance = AnalyticsService._();

  static const _key = 'analytics_event_queue_v1';
  static const _max = 500;

  Future<void> track(String event, [Map<String, dynamic>? props]) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    final list = <Map<String, dynamic>>[];
    if (raw != null && raw.isNotEmpty) {
      try {
        list.addAll(
          (jsonDecode(raw) as List).map((e) => Map<String, dynamic>.from(e as Map)),
        );
      } catch (_) {}
    }
    list.add({
      'event': event,
      'ts': DateTime.now().toUtc().toIso8601String(),
      if (props != null) 'props': props,
    });
    while (list.length > _max) {
      list.removeAt(0);
    }
    await prefs.setString(_key, jsonEncode(list));
    if (kDebugMode) debugPrint('[analytics] $event $props');
  }

  Future<List<Map<String, dynamic>>> pending() async {
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

  Future<void> clearPending() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }

  Future<void> flush(ApiClient api) async {
    final events = await pending();
    if (events.isEmpty) return;
    try {
      await api.postAnalyticsEvents(events);
      await clearPending();
    } catch (_) {}
  }
}
