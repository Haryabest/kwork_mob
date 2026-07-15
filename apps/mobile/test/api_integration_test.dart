import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

/// CI smoke против живого backend (INTEGRATION_API=http://localhost:8000).
void main() {
  final base = const String.fromEnvironment('INTEGRATION_API');
  if (base.isEmpty) {
    test('integration api skipped without INTEGRATION_API', () {});
    return;
  }

  late Dio dio;

  setUp(() {
    dio = Dio(BaseOptions(baseUrl: base, connectTimeout: const Duration(seconds: 10)));
  });

  test('health', () async {
    final r = await dio.get('/health');
    expect(r.statusCode, 200);
  });

  test('well-known aasa', () async {
    final r = await dio.get('/.well-known/apple-app-site-association');
    expect(r.statusCode, 200);
    expect(r.data, isA<Map>());
    expect(r.data['applinks'], isNotNull);
    expect(r.data['_meta'], isNull);
  });

  test('well-known assetlinks', () async {
    final r = await dio.get('/.well-known/assetlinks.json');
    expect(r.statusCode, 200);
    expect(r.data, isA<List>());
  });

  test('auth register login devices analytics', () async {
    final email = 'ci_${DateTime.now().millisecondsSinceEpoch}@example.com';
    const password = 'secret123';

    final reg = await dio.post('/api/v1/auth/register', data: {
      'email': email,
      'password': password,
      'password_confirm': password,
      'consents': ['terms', 'privacy', 'offer', 'rights', 'nsfw_rules'],
    });
    expect(reg.statusCode, 201);

    final verify = await dio.post('/api/v1/auth/verify-email', data: {
      'email': email,
      'code': reg.data['dev_code'],
    });
    expect(verify.statusCode, 200);

    final login = await dio.post('/api/v1/auth/login', data: {
      'email': email,
      'password': password,
    });
    expect(login.statusCode, 200);
    final token = login.data['access_token'] as String;
    final headers = {'Authorization': 'Bearer $token'};

    final me = await dio.get('/api/v1/user/me', options: Options(headers: headers));
    expect(me.statusCode, 200);

    final device = await dio.post(
      '/api/v1/user/devices',
      data: {'token': 'f' * 140, 'platform': 'android', 'app_version': '0.1.0'},
      options: Options(headers: headers),
    );
    expect(device.statusCode, isIn([200, 201]));

    final banners = await dio.get(
      '/api/v1/user/campaign_banners',
      options: Options(headers: headers),
    );
    expect(banners.statusCode, 200);
    expect(banners.data['items'], isA<List>());

    final analytics = await dio.post(
      '/api/v1/user/analytics/events',
      data: {
        'events': [
          {'event': 'ci_smoke', 'ts': '2026-01-01T00:00:00Z'},
        ],
      },
      options: Options(headers: headers),
    );
    expect(analytics.statusCode, 200);
    expect(analytics.data['accepted'], 1);
  });
}
