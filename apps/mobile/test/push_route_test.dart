import 'package:flutter_test/flutter_test.dart';
import 'package:kwork_mobile/core/push_route.dart';

void main() {
  test('FCM deeplink order', () {
    expect(
      routeFromPushData({'deeplink': 'https://3d.app/orders/42'}),
      '/home/queue/42',
    );
  });

  test('FCM order_id fallback', () {
    expect(routeFromPushData({'order_id': '7'}), '/home/queue/7');
  });

  test('FCM generation_done → notifications', () {
    expect(routeFromPushData({'type': 'generation_done'}), '/home/notifications');
  });

  test('FCM support ticket', () {
    expect(
      routeFromPushData({'type': 'support_reply', 'ticket_id': 't1'}),
      '/home?tab=support&supportTicket=t1',
    );
  });
}
