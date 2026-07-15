import 'dart:io' show Platform;

import 'package:app_links/app_links.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/widgets.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/deep_link_routes.dart';
import 'package:kwork_mobile/firebase_options.dart';
import 'package:kwork_mobile/services/notification_inbox.dart';
import 'package:kwork_mobile/services/push_deep_link.dart';
import 'package:shared_preferences/shared_preferences.dart';

@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    final opts = DefaultFirebaseOptions.currentPlatform;
    if (opts != null) {
      await Firebase.initializeApp(options: opts);
    } else {
      await Firebase.initializeApp();
    }
  } catch (_) {}
  await NotificationInbox.instance.add(
    title: message.notification?.title ?? 'Уведомление',
    body: message.notification?.body ?? '',
    orderId: message.data['order_id']?.toString(),
    modelUuid: message.data['model_uuid']?.toString(),
    type: message.data['type']?.toString() ?? message.data['event']?.toString(),
    id: message.messageId,
  );
}

/// Push FCM + deep link на заказ/модель (§3.4.3). Android + iOS.
class PushService {
  PushService(this._api);

  final ApiClient _api;
  bool available = false;
  String? token;
  GoRouter? router;
  GlobalKey<ScaffoldMessengerState>? messengerKey;
  Future<bool> Function()? canNavigate;
  void Function(String route, {String? title})? onForegroundNavigate;
  AppLinks? _appLinks;

  void bindRouter(GoRouter router) {
    this.router = router;
  }

  void bindMessenger(GlobalKey<ScaffoldMessengerState> key) {
    messengerKey = key;
  }

  void bindNavigationGuard(Future<bool> Function() guard) {
    canNavigate = guard;
  }

  void bindForegroundNavigate(void Function(String route, {String? title})? handler) {
    onForegroundNavigate = handler;
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
      await _bindAppLinks();
      return;
    }

    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
    final messaging = FirebaseMessaging.instance;
    await messaging.requestPermission(alert: true, badge: true, sound: true);
    if (!kIsWeb && Platform.isIOS) {
      await messaging.setForegroundNotificationPresentationOptions(
        alert: true,
        badge: true,
        sound: true,
      );
    }
    token = await messaging.getToken();
    if (token != null) {
      await _register(token!);
    }
    messaging.onTokenRefresh.listen(_register);

    FirebaseMessaging.onMessage.listen((msg) async {
      await _record(msg);
      await _handleData(msg.data, fromForeground: true, title: msg.notification?.title);
    });
    FirebaseMessaging.onMessageOpenedApp.listen((msg) async {
      await _record(msg);
      await _handleData(msg.data);
    });
    final initial = await messaging.getInitialMessage();
    if (initial != null) {
      await _record(initial);
      await _handleData(initial.data);
    }

    await _bindAppLinks();
  }

  Future<void> _bindAppLinks() async {
    if (kIsWeb) return;
    try {
      _appLinks ??= AppLinks();
      final initial = await _appLinks!.getInitialLink();
      if (initial != null) {
        await _handleExternalUri(initial);
      }
      _appLinks!.uriLinkStream.listen((uri) {
        _handleExternalUri(uri);
      });
    } catch (e) {
      debugPrint('Deep link listener: $e');
    }
  }

  /// После login / splash — применить отложенный deep link.
  Future<bool> applyPendingRoute(GoRouter router) async {
    final pending = await PushDeepLink.take();
    if (pending == null) return false;
    router.go(pending);
    return true;
  }

  Future<void> _record(RemoteMessage msg) async {
    await NotificationInbox.instance.add(
      title: msg.notification?.title ?? 'Уведомление',
      body: msg.notification?.body ?? '',
      orderId: msg.data['order_id']?.toString(),
      modelUuid: msg.data['model_uuid']?.toString(),
      type: msg.data['type']?.toString() ?? msg.data['event']?.toString(),
      id: msg.messageId,
    );
  }

  String? _routeFromData(Map<String, dynamic> data) {
    final deeplink = data['deeplink']?.toString() ?? data['link']?.toString();
    if (deeplink != null && deeplink.isNotEmpty) {
      return routeFromDeepLinkUri(Uri.tryParse(deeplink));
    }
    final orderId = data['order_id']?.toString();
    final modelUuid = data['model_uuid']?.toString();
    final type = data['type']?.toString() ?? data['event']?.toString();

    if (orderId != null && orderId.isNotEmpty) {
      return '/home/queue/$orderId';
    }
    if (modelUuid != null && modelUuid.isNotEmpty) {
      return '/home/models/$modelUuid';
    }
    if (type == 'nsfw_blocked' ||
        type == 'refund' ||
        type == 'generation_done' ||
        type == 'generation_failed' ||
        type == 'cancelled') {
      return '/home/notifications';
    }
    if (type == 'topup_failed') {
      return '/home/balance';
    }
    final ticketId = data['ticket_id']?.toString() ?? data['support_id']?.toString();
    if (type == 'support' || type == 'support_reply') {
      if (ticketId != null && ticketId.isNotEmpty) {
        return '/home?tab=support&supportTicket=$ticketId';
      }
      return '/home?tab=support';
    }
    return null;
  }

  Future<void> _handleExternalUri(Uri uri) async {
    final route = routeFromDeepLinkUri(uri);
    if (route == null) return;
    await _navigateToRoute(route);
  }

  Future<void> _handleData(
    Map<String, dynamic> data, {
    bool fromForeground = false,
    String? title,
  }) async {
    final route = _routeFromData(data);
    if (route == null) {
      if (fromForeground) debugPrint('FCM data без маршрута: $data');
      return;
    }
    await _navigateToRoute(route, fromForeground: fromForeground, title: title);
  }

  Future<void> _navigateToRoute(
    String route, {
    bool fromForeground = false,
    String? title,
  }) async {
    final allowed = canNavigate == null ? await _api.hasToken : await canNavigate!();
    if (!allowed) {
      await PushDeepLink.save(route);
      return;
    }

    if (fromForeground) {
      if (onForegroundNavigate != null &&
          (route.startsWith('/home?') || route == '/home' || route.startsWith('/home/support'))) {
        onForegroundNavigate!(route, title: title);
        return;
      }
      _showForegroundSnack(title ?? 'Уведомление', route);
      return;
    }

    // Cold start / background tap — сразу на экран заказа / модели / inbox §19.16
    final r = router;
    if (r != null) {
      r.go(route);
      return;
    }
    await PushDeepLink.save(route);
  }

  void _showForegroundSnack(String title, String route) {
    final messenger = messengerKey?.currentState;
    if (messenger == null) return;
    messenger.showSnackBar(
      SnackBar(
        content: Text(title),
        action: SnackBarAction(
          label: 'Открыть',
          onPressed: () => router?.go(route),
        ),
        duration: const Duration(seconds: 5),
      ),
    );
  }

  Future<void> _register(String t) async {
    token = t;
    try {
      await _api.registerDevice(
        token: t,
        platform: _devicePlatform(),
        appVersion: const String.fromEnvironment('APP_VERSION', defaultValue: '0.1.0'),
      );
    } catch (e) {
      debugPrint('FCM register failed: $e');
    }
  }

  String _devicePlatform() {
    if (kIsWeb) return 'web';
    if (Platform.isIOS) return 'ios';
    if (Platform.isAndroid) return 'android';
    return 'unknown';
  }

  Future<Map<String, bool>> loadPrefs() async {
    final defaults = {
      'push_enabled': true,
      'email_enabled': true,
      'generation_done': true,
      'refund': true,
      'nsfw_blocked': true,
      'source_expire': true,
      'cleanup': false,
      'publish_reminder': true,
      'topup_failed': true,
    };
    try {
      final me = await _api.me();
      final np = me['notification_prefs'];
      if (np is Map) {
        final p = await SharedPreferences.getInstance();
        final out = <String, bool>{};
        for (final k in defaults.keys) {
          final v = np[k];
          final boolVal = v is bool ? v : defaults[k]!;
          out[k] = boolVal;
          await p.setBool('push_$k', boolVal);
        }
        return out;
      }
    } catch (e) {
      debugPrint('FCM prefs sync from server failed: $e');
    }
    final p = await SharedPreferences.getInstance();
    return {
      for (final e in defaults.entries) e.key: p.getBool('push_${e.key}') ?? e.value,
    };
  }

  Future<void> setPref(String key, bool value) async {
    final p = await SharedPreferences.getInstance();
    await p.setBool('push_$key', value);
    try {
      await _api.patchMe({
        'notification_prefs': {key: value},
      });
    } catch (e) {
      debugPrint('FCM prefs sync to server failed: $e');
    }
  }
}
