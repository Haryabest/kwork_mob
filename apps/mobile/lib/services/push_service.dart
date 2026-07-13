import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/firebase_options.dart';
import 'package:shared_preferences/shared_preferences.dart';

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  debugPrint('FCM background: ${message.messageId}');
}

/// Push FCM + prefs типов уведомлений (§3.4.3). Fallback email — на бэке.
class PushService {
  PushService(this._api);

  final ApiClient _api;
  bool available = false;
  String? token;

  Future<void> init() async {
    try {
      final opts = DefaultFirebaseOptions.currentPlatform;
      if (opts != null) {
        await Firebase.initializeApp(options: opts);
      } else {
        // native google-services.json / GoogleService-Info.plist
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
    });
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
