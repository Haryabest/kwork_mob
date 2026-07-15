import 'package:kwork_mobile/l10n/app_localizations.dart';

/// Человекочитаемые ошибки WebSocket очереди (§3.4.1).
String formatWsError(Object error, [AppLocalizations? l]) {
  final s = error.toString().toLowerCase();
  if (s.contains('401') || s.contains('403') || s.contains('unauthorized')) {
    return l?.wsSessionExpired ?? 'Session expired. Sign in again.';
  }
  if (s.contains('connection refused') || s.contains('failed host lookup')) {
    return l?.wsServerUnavailable ?? 'Server unavailable. Check API_URL and network.';
  }
  if (s.contains('websocket') || s.contains('socket')) {
    return l?.wsQueueFailed ?? 'Could not connect to queue. Try again later.';
  }
  return l?.wsQueueError ?? 'Queue connection error';
}

String paymentStatusLabel(AppLocalizations l, String? status) {
  switch (status?.toLowerCase()) {
    case 'pending':
      return l.paymentStatusPending;
    case 'succeeded':
    case 'success':
      return l.paymentStatusSucceeded;
    case 'canceled':
    case 'cancelled':
      return l.paymentStatusCanceled;
    default:
      return l.balSuccess;
  }
}
