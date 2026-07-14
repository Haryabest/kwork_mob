import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/firebase_options.dart';
import 'package:shared_preferences/shared_preferences.dart';

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  debugPrint('FCM background: ${message.messageId}');
}

/// Push FCM + prefs типов уведомлений (§3.4.3). Deep link на заказ/модель.
class PushService {
  PushService(this._api);

  final ApiClient _api;
  bool available = false;
  String? token;
  GlobalKey<NavigatorState>? navigatorKey;
  GoRouter? router;

  void bindRouter(GoRouter router) {
    this.router = router;
  }

  Future<void> init() async {
    try {
      final opts = DefaultFirebaseOptions.currentPlatform;
      if (opts != null) {
        await Firebase.initializeApp(options: opts);
      } else {
        await Firebase.initializeApp();
      }
      available = true;
    } catch (e) {
      debugPrint('FCM: Firebase не сконфигурирован ($e) — push отключён');
      available = false;
      return;
    }

    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
    final messaging = FirebaseMessaging.instance;
    await messaging.requestPermission(alert: true, badge: true, sound: true);
    token = await messaging.getToken();
    if (token != null) {
      await _register(token!);
    }
    messaging.onTokenRefresh.listen(_register);

    FirebaseMessaging.onMessage.listen((msg) {
      debugPrint('FCM foreground: ${msg.notification?.title}');
      _handleData(msg.data, fromForeground: true);
    });
    FirebaseMessaging.onMessageOpenedApp.listen((msg) {
      _handleData(msg.data);
    });
    final initial = await messaging.getInitialMessage();
    if (initial != null) {
      _handleData(initial.data);
    }
  }

  void _handleData(Map<String, dynamic> data, {bool fromForeground = false}) {
    final orderId = data['order_id']?.toString();
    final modelUuid = data['model_uuid']?.toString();
    final type = data['type']?.toString() ?? data['event']?.toString();

    if (router == null) return;
    if (orderId != null && orderId.isNotEmpty) {
      router!.go('/home/queue/$orderId');
      return;
    }
    if (modelUuid != null && modelUuid.isNotEmpty) {
      router!.go('/home/models/$modelUuid');
      return;
    }
    if (type == 'support' || type == 'support_reply') {
      // seller web has /support; mobile FAQ
      router!.go('/home');
    }
    if (fromForeground) {
      debugPrint('FCM data: $data');
    }
  }

  Future<void> _register(String t) async {
    token = t;
    try {
      await _api.registerDevice(
        token: t,
        platform: Platform.isIOS ? 'ios' : 'android',
        appVersion: '0.1.0',
      );
    } catch (e) {
      debugPrint('FCM register failed: $e');
    }
  }

  Future<Map<String, bool>> loadPrefs() async {
    final p = await SharedPreferences.getInstance();
    return {
      'generation_done': p.getBool('push_generation_done') ?? true,
      'refund': p.getBool('push_refund') ?? true,
      'source_expire': p.getBool('push_source_expire') ?? true,
      'cleanup': p.getBool('push_cleanup') ?? false,
      'publish_reminder': p.getBool('push_publish_reminder') ?? true,
    };
  }

  Future<void> setPref(String key, bool value) async {
    final p = await SharedPreferences.getInstance();
    await p.setBool('push_$key', value);
  }
}
