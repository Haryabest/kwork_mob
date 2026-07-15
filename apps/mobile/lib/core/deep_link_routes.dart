/// Маршрут go_router из URI (push / kworkmob:// / universal link path).
String? routeFromDeepLinkUri(Uri? uri) {
  if (uri == null) return null;
  if (uri.scheme == 'kworkmob' || uri.host == 'open') {
    final segs = uri.pathSegments.where((s) => s.isNotEmpty).toList();
    if (segs.isEmpty) return '/home';
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
        return '/home/support/ticket/${segs[2]}';
      }
      return '/home';
    }
    if (segs.first == 'shoot' && segs.length >= 2) {
      return '/shoot/${segs[1]}';
    }
  }
  if (uri.path.startsWith('/home/')) return uri.path;
  if (uri.path.startsWith('/shoot/')) return uri.path;
  return null;
}
