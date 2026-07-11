import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class ApiClient {
  ApiClient({String? baseUrl})
      : _dio = Dio(
          BaseOptions(
            baseUrl: baseUrl ?? const String.fromEnvironment(
              'API_URL',
              defaultValue: 'http://10.0.2.2:8000/api/v1',
            ),
            connectTimeout: const Duration(seconds: 15),
            receiveTimeout: const Duration(seconds: 30),
          ),
        ) {
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          final token = await _storage.read(key: 'access_token');
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
          handler.next(options);
        },
      ),
    );
  }

  final Dio _dio;
  final _storage = const FlutterSecureStorage();

  Dio get dio => _dio;

  Future<void> saveTokens(String access, String refresh) async {
    await _storage.write(key: 'access_token', value: access);
    await _storage.write(key: 'refresh_token', value: refresh);
  }

  Future<void> clearTokens() async {
    await _storage.delete(key: 'access_token');
    await _storage.delete(key: 'refresh_token');
  }

  Future<bool> get hasToken async =>
      (await _storage.read(key: 'access_token')) != null;

  Future<Map<String, dynamic>> login(String email, String password) async {
    final res = await _dio.post('/auth/login', data: {
      'email': email,
      'password': password,
      'remember_me': true,
    });
    final data = Map<String, dynamic>.from(res.data as Map);
    await saveTokens(
      data['access_token'] as String,
      data['refresh_token'] as String,
    );
    return data;
  }

  Future<Map<String, dynamic>> me() async {
    final res = await _dio.get('/user/me');
    return Map<String, dynamic>.from(res.data as Map);
  }
}
