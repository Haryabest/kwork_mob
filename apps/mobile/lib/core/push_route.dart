import 'package:kwork_mobile/core/deep_link_routes.dart';

/// Маршрут go_router из FCM data payload (§3.4.3).
String? routeFromPushData(Map<String, dynamic> data) {
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
