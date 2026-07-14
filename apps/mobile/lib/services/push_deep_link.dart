import 'package:shared_preferences/shared_preferences.dart';

/// Отложенная навигация из push (cold start / до login).
class PushDeepLink {
  PushDeepLink._();

  static const _key = 'pending_push_route_v1';

  static Future<void> save(String route) async {
    if (route.isEmpty) return;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, route);
  }

  static Future<String?> take() async {
    final prefs = await SharedPreferences.getInstance();
    final route = prefs.getString(_key);
    if (route != null && route.isNotEmpty) {
      await prefs.remove(_key);
      return route;
    }
    return null;
  }
}
