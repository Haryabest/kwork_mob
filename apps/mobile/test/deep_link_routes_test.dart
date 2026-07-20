import 'package:flutter_test/flutter_test.dart';
import 'package:kwork_mobile/core/deep_link_routes.dart';

void main() {
  test('https shoot link', () {
    expect(
      routeFromDeepLinkUri(Uri.parse('https://3d.app/shoot/abc123')),
      '/shoot/abc123',
    );
  });

  test('https order link', () {
    expect(
      routeFromDeepLinkUri(Uri.parse('https://3d.app/orders/42')),
      '/home/queue/42',
    );
  });

  test('kworkmob oauth callback', () {
    expect(
      routeFromDeepLinkUri(Uri.parse('kworkmob://open/oauth/callback?code=x&state=y')),
      '/auth',
    );
  });

  test('kworkmob scheme queue', () {
    expect(
      routeFromDeepLinkUri(Uri.parse('kworkmob://open/queue/99')),
      '/home/queue/99',
    );
  });

  test('kworkmob scheme model', () {
    expect(
      routeFromDeepLinkUri(Uri.parse('kworkmob://open/models/uuid-here')),
      '/home/models/uuid-here',
    );
  });
}
