import 'package:kwork_mobile/services/oauth_pending.dart';

/// Маршрут go_router из URI (push / kworkmob:// / universal link path).
String? routeFromDeepLinkUri(Uri? uri) {
  if (uri == null) return null;
  if (uri.scheme == 'kworkmob' || uri.host == 'open') {
    final segs = uri.pathSegments.where((s) => s.isNotEmpty).toList();
    if (segs.isEmpty) return '/home';
    if (segs.first == 'oauth' && segs.length >= 2 && segs[1] == 'callback') {
      final code = uri.queryParameters['code'];
      final state = uri.queryParameters['state'];
      final isLink = OAuthPending.instance.pendingFlow == OAuthFlow.link;
      if (code != null && state != null) {
        OAuthPending.instance.deliver(code, state);
      }
      if (isLink) return '/home?tab=profile';
      return '/auth';
    }
    if (segs.first == 'queue' && segs.length >= 2) {
      return '/home/queue/${segs[1]}';
    }
    if (segs.first == 'models' && segs.length >= 2) {
      return '/home/models/${segs[1]}';
    }
    if (segs.first == 'notifications') {
      return '/home/notifications';
    }
    if (segs.first == 'support') {
      if (segs.length >= 3 && segs[1] == 'ticket') {
        return '/home?tab=support&supportTicket=${segs[2]}';
      }
      return '/home?tab=support';
    }
    if (segs.first == 'shoot' && segs.length >= 2) {
      return '/shoot/${segs[1]}';
    }
  }
  if (uri.path.startsWith('/home/')) return uri.path;
  if (uri.path == '/home' && uri.queryParameters.isNotEmpty) {
    return '${uri.path}?${uri.query}';
  }
  if (uri.path.startsWith('/shoot/')) return uri.path;
  if (uri.path.startsWith('/orders/')) {
    final segs = uri.pathSegments.where((s) => s.isNotEmpty).toList();
    if (segs.length >= 2 && segs[0] == 'orders') {
      return '/home/queue/${segs[1]}';
    }
  }
  return null;
}
