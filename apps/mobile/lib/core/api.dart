import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:kwork_mobile/domain/catalog.dart';

/// Человекочитаемая ошибка API (без простыни DioException).
String formatApiError(Object error) {
  if (error is DioException) {
    final code = error.response?.statusCode;
    final detail = error.response?.data;
    String? msg;
    if (detail is Map) {
      final d = detail['detail'];
      if (d is String) {
        msg = d;
      } else if (d is Map) {
        msg = d['message']?.toString() ?? d['code']?.toString();
      } else if (d is List && d.isNotEmpty) {
        final first = d.first;
        if (first is Map) {
          msg = first['msg']?.toString() ?? first.toString();
        } else {
          msg = first.toString();
        }
      }
      msg ??= detail['message']?.toString();
    } else if (detail is String) {
      msg = detail;
    }
    return switch (code) {
      401 => msg ?? 'Сессия истекла. Войдите снова.',
      403 => msg ?? 'Нет доступа для этой операции.',
      404 => msg ?? 'Не найдено.',
      402 => msg ?? 'Лимит или бюджет исчерпан.',
      429 => msg ?? 'Слишком много запросов. Подождите.',
      502 => msg ?? 'Ошибка внешнего сервиса. Попробуйте позже.',
      _ => msg ?? error.message ?? '$error',
    };
  }
  if (error is StateError) return error.message;
  return error.toString();
}

class ApiClient {
  ApiClient({String? baseUrl})
      : _baseUrl = baseUrl ??
            const String.fromEnvironment(
              'API_URL',
              defaultValue: 'http://10.0.2.2:8000/api/v1',
            ),
        _dio = Dio(
          BaseOptions(
            baseUrl: baseUrl ??
                const String.fromEnvironment(
                  'API_URL',
                  defaultValue: 'http://10.0.2.2:8000/api/v1',
                ),
            connectTimeout: const Duration(seconds: 20),
            receiveTimeout: const Duration(seconds: 60),
            sendTimeout: const Duration(seconds: 120),
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
        onError: (error, handler) async {
          final status = error.response?.statusCode;
          final path = error.requestOptions.path;
          if (status == 401 &&
              !path.contains('/auth/refresh') &&
              error.requestOptions.extra['auth_retry'] != true) {
            final refresh = await _storage.read(key: 'refresh_token');
            if (refresh != null) {
              try {
                final res = await _dio.post(
                  '/auth/refresh',
                  data: {'refresh_token': refresh},
                  options: Options(extra: {'auth_retry': true}),
                );
                final data = Map<String, dynamic>.from(res.data as Map);
                await saveTokens(
                  data['access_token'] as String,
                  data['refresh_token'] as String,
                );
                error.requestOptions.headers['Authorization'] =
                    'Bearer ${data['access_token']}';
                error.requestOptions.extra['auth_retry'] = true;
                final retry = await _dio.fetch(error.requestOptions);
                return handler.resolve(retry);
              } catch (_) {
                await clearTokens();
              }
            }
          }
          handler.next(error);
        },
      ),
    );
  }

  final String _baseUrl;
  final Dio _dio;
  final _storage = const FlutterSecureStorage();

  Dio get dio => _dio;

  String get wsBaseUrl {
    final uri = Uri.parse(_baseUrl.replaceAll('/api/v1', ''));
    final scheme = uri.scheme == 'https' ? 'wss' : 'ws';
    return '$scheme://${uri.host}${uri.hasPort ? ':${uri.port}' : ''}';
  }

  Future<String?> get accessToken => _storage.read(key: 'access_token');

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

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String passwordConfirm,
    List<String> consents = const [
      'terms',
      'privacy',
      'offer',
      'rights',
      'nsfw_rules',
    ],
  }) async {
    final res = await _dio.post('/auth/register', data: {
      'email': email,
      'password': password,
      'password_confirm': passwordConfirm,
      'consents': consents,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> verifyEmail({
    required String email,
    required String code,
  }) async {
    final res = await _dio.post('/auth/verify-email', data: {
      'email': email,
      'code': code,
    });
    final data = Map<String, dynamic>.from(res.data as Map);
    final access = data['access_token'] as String?;
    final refresh = data['refresh_token'] as String?;
    if (access != null && refresh != null) {
      await saveTokens(access, refresh);
    }
    return data;
  }

  Future<Map<String, dynamic>> setAccountType({
    required String accountType,
    String? fullName,
    String? companyName,
    String? inn,
    String? ogrn,
    String? legalAddress,
    String? directorName,
    String? bankName,
    String? bik,
    String? checkingAccount,
  }) async {
    final res = await _dio.post('/auth/account-type', data: {
      'account_type': accountType,
      if (fullName != null && fullName.isNotEmpty) 'full_name': fullName,
      if (companyName != null && companyName.isNotEmpty) 'company_name': companyName,
      if (inn != null && inn.isNotEmpty) 'inn': inn,
      if (ogrn != null && ogrn.isNotEmpty) 'ogrn': ogrn,
      if (legalAddress != null && legalAddress.isNotEmpty) 'legal_address': legalAddress,
      if (directorName != null && directorName.isNotEmpty) 'director_name': directorName,
      if (bankName != null && bankName.isNotEmpty) 'bank_name': bankName,
      if (bik != null && bik.isNotEmpty) 'bik': bik,
      if (checkingAccount != null && checkingAccount.isNotEmpty) 'checking_account': checkingAccount,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> requestPasswordReset(String email) async {
    final res = await _dio.post('/auth/password/forgot', data: {'email': email});
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> confirmPasswordReset({
    required String token,
    required String newPassword,
    required String passwordConfirm,
  }) async {
    final res = await _dio.post('/auth/password/confirm', data: {
      'token': token,
      'new_password': newPassword,
      'password_confirm': passwordConfirm,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> login(
    String email,
    String password, {
    bool rememberMe = true,
  }) async {
    final res = await _dio.post('/auth/login', data: {
      'email': email,
      'password': password,
      'remember_me': rememberMe,
    });
    final data = Map<String, dynamic>.from(res.data as Map);
    if (data['requires_2fa'] == true) {
      return data;
    }
    await saveTokens(
      data['access_token'] as String,
      data['refresh_token'] as String,
    );
    return data;
  }

  Future<Map<String, dynamic>> verifyLogin2fa({
    required String challengeToken,
    required String code,
  }) async {
    final res = await _dio.post('/auth/2fa/verify-login', data: {
      'challenge_token': challengeToken,
      'code': code,
    });
    final data = Map<String, dynamic>.from(res.data as Map);
    await saveTokens(
      data['access_token'] as String,
      data['refresh_token'] as String,
    );
    return data;
  }

  Future<Map<String, dynamic>> twoFaStatus() async {
    final res = await _dio.get('/auth/2fa/status');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> twoFaSetup() async {
    final res = await _dio.post('/auth/2fa/setup');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> twoFaConfirm({
    required String code,
    String? challengeToken,
  }) async {
    final res = await _dio.post('/auth/2fa/confirm', data: {
      'code': code,
      if (challengeToken != null) 'challenge_token': challengeToken,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<List<Map<String, dynamic>>> legalPending() async {
    final res = await _dio.get('/legal/pending');
    final items = (res.data as Map)['pending'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> legalDocument(String slug) async {
    final res = await _dio.get('/legal/$slug');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<void> legalAccept(List<String> slugs) async {
    await _dio.post('/legal/accept', data: {'slugs': slugs});
  }

  Future<Map<String, dynamic>> me() async {
    final res = await _dio.get('/user/me');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> updateProfile(Map<String, dynamic> data) async {
    final res = await _dio.patch('/user/me', data: data);
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<List<Map<String, dynamic>>> listDraftBackups() async {
    final res = await _dio.get('/user/draft-backups');
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> prepareDraftBackup({
    required String modelUuid,
    String? category,
    int capturedCount = 0,
    String? tier,
  }) async {
    final res = await _dio.post('/user/draft-backups/prepare', data: {
      'model_uuid': modelUuid,
      if (category != null) 'category': category,
      'captured_count': capturedCount,
      if (tier != null) 'tier': tier,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> restoreDraftBackup(String modelUuid) async {
    final res = await _dio.get('/user/draft-backups/$modelUuid/restore');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> patchMe(Map<String, dynamic> payload) async {
    final res = await _dio.patch('/user/me', data: payload);
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> createShareLink({
    required String modelUuid,
    int ttlDays = 7,
  }) async {
    final res = await _dio.post('/models/$modelUuid/share', data: {
      'ttl_days': ttlDays,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> inviteMember({
    required String email,
    String role = 'photographer',
    int? companyId,
    int maxConcurrentOrders = 3,
    int? monthlySpendingLimit,
  }) async {
    final res = await _dio.post('/company/invite', data: {
      'email': email,
      'role': role,
      if (companyId != null) 'company_id': companyId,
      'max_concurrent_orders': maxConcurrentOrders,
      if (monthlySpendingLimit != null) 'monthly_spending_limit': monthlySpendingLimit,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<List<Map<String, dynamic>>> listInvitations() async {
    final res = await _dio.get('/company/invitations');
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> changeMemberRole({
    required int userId,
    required String role,
  }) async {
    final res = await _dio.patch('/company/members/$userId/role', data: {
      'role': role,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> changeMemberLimits({
    required int userId,
    int? maxConcurrentOrders,
    int? monthlySpendingLimit,
  }) async {
    final res = await _dio.patch('/company/members/$userId/limits', data: {
      if (maxConcurrentOrders != null) 'max_concurrent_orders': maxConcurrentOrders,
      if (monthlySpendingLimit != null) 'monthly_spending_limit': monthlySpendingLimit,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<List<Map<String, dynamic>>> listAuditLog() async {
    final res = await _dio.get('/company/audit');
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  int countActiveOrders(List<Map<String, dynamic>> orders, {int? companyId}) {
    const active = {'queued', 'processing', 'awaiting_payment', 'pending'};
    return orders.where((o) {
      if (companyId != null && o['company_id'] != companyId) return false;
      return active.contains(o['status']?.toString());
    }).length;
  }

  Future<List<Map<String, dynamic>>> myCompanies() async {
    final res = await _dio.get('/company/mine');
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> preparePhotos({
    String? taskUuid,
    int? companyId,
  }) async {
    final res = await _dio.post('/orders/photos/prepare', data: {
      if (taskUuid != null) 'task_uuid': taskUuid,
      if (companyId != null) 'company_id': companyId,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<void> registerPhotoEncryptionKey({
    required String taskUuid,
    required String keyB64,
  }) async {
    await _dio.post('/orders/photos/encryption-key', data: {
      'task_uuid': taskUuid,
      'key_b64': keyB64,
      'algorithm': 'aes-256-gcm',
    });
  }

  /// Presigned PUT каждого JPEG (resumable по файлу).
  Future<void> uploadPhotoPresigned({
    required String uploadUrl,
    required File file,
    String contentType = 'image/jpeg',
    Uint8List? bytesOverride,
    void Function(int sent, int total)? onProgress,
  }) async {
    final bytes = bytesOverride ?? await file.readAsBytes();
    final req = http.StreamedRequest('PUT', Uri.parse(uploadUrl));
    req.headers['Content-Type'] = contentType;
    req.contentLength = bytes.length;
    var sent = 0;
    const chunk = 64 * 1024;
    for (var i = 0; i < bytes.length; i += chunk) {
      final end = (i + chunk > bytes.length) ? bytes.length : i + chunk;
      req.sink.add(bytes.sublist(i, end));
      sent = end;
      onProgress?.call(sent, bytes.length);
    }
    await req.sink.close();
    final res = await req.send();
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw DioException(
        requestOptions: RequestOptions(path: uploadUrl),
        message: 'Presigned upload failed: ${res.statusCode}',
      );
    }
  }

  /// Fallback: multipart всех 12 файлов.
  Future<Map<String, dynamic>> uploadPhotosMultipart({
    required String taskUuid,
    required List<File> files,
    void Function(int, int)? onSendProgress,
  }) async {
    final form = FormData();
    for (final f in files) {
      form.files.add(
        MapEntry(
          'files',
          await MultipartFile.fromFile(f.path, filename: f.uri.pathSegments.last),
        ),
      );
    }
    final res = await _dio.post(
      '/orders/photos/upload',
      queryParameters: {'task_uuid': taskUuid},
      data: form,
      onSendProgress: onSendProgress,
    );
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> createOrder({
    required String taskUuid,
    required ProductCategory category,
    required Tier tier,
    int? companyId,
    String? promocode,
    List<ForbiddenCategory> forbidden = const [],
    String? birthDate,
    Map<String, dynamic>? scaleCalibration,
    List<String> upsells = const [],
    String? photosPrefix,
    String? zipSha256,
    String? customerName,
    String? modelDisplayName,
    String? deviceModel,
    String? osVersion,
  }) async {
    final res = await _dio.post('/orders/create', data: {
      'task_uuid': taskUuid,
      'category': category.api,
      'tier': tier.api,
      if (companyId != null) 'company_id': companyId,
      if (promocode != null && promocode.isNotEmpty) 'promocode': promocode,
      'forbidden_categories': forbidden.map((e) => e.api).toList(),
      if (birthDate != null) 'birth_date': birthDate,
      if (scaleCalibration != null) 'scale_calibration': scaleCalibration,
      'upsell_options': upsells,
      if (photosPrefix != null) 'photos_prefix': photosPrefix,
      if (zipSha256 != null) 'zip_sha256': zipSha256,
      if (customerName != null && customerName.isNotEmpty) 'customer_name': customerName,
      if (modelDisplayName != null && modelDisplayName.isNotEmpty)
        'model_display_name': modelDisplayName,
      if (deviceModel != null) 'device_model': deviceModel,
      if (osVersion != null) 'os_version': osVersion,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<void> changePassword({
    required String oldPassword,
    required String newPassword,
  }) async {
    await _dio.post('/auth/password/change', data: {
      'old_password': oldPassword,
      'new_password': newPassword,
    });
  }

  Future<Map<String, dynamic>> requestAccountDeletion() async {
    final res = await _dio.post('/user/me/delete-request');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> renameModel({
    required String modelUuid,
    required String displayName,
  }) async {
    final res = await _dio.patch('/models/$modelUuid', data: {
      'display_name': displayName,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<String?> modelThumbnailUrl(String modelUuid) async {
    try {
      final res = await _dio.get('/models/$modelUuid/thumbnail');
      return (res.data as Map)['thumbnail_url']?.toString();
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<List<Map<String, dynamic>>> listUpsells() async {
    final res = await _dio.get('/orders/upsells');
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<List<Map<String, dynamic>>> listTariffs() async {
    final res = await _dio.get('/orders/tariffs');
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> payOrder({
    required int orderId,
    String paymentMethod = 'redirect',
    String? customerName,
  }) async {
    final res = await _dio.post('/orders/$orderId/pay', data: {
      'payment_method': paymentMethod,
      if (customerName != null && customerName.isNotEmpty) 'customer_name': customerName,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> getOrder(int orderId) async {
    final res = await _dio.get('/orders/$orderId');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> cancelOrder(int orderId) async {
    final res = await _dio.post('/orders/$orderId/cancel');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<List<Map<String, dynamic>>> listOrders({int? companyId, int? userId}) async {
    final res = await _dio.get('/orders', queryParameters: {
      if (companyId != null) 'company_id': companyId,
      if (userId != null) 'user_id': userId,
    });
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<List<Map<String, dynamic>>> listModels({int? companyId}) async {
    final res = await _dio.get('/user/models', queryParameters: {
      if (companyId != null) 'company_id': companyId,
    });
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> rateModel({
    required String modelUuid,
    required int rating,
    List<String> reasons = const [],
  }) async {
    final res = await _dio.post('/models/$modelUuid/rate', data: {
      'rating': rating,
      'reasons': reasons,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> downloadModel({
    required String modelUuid,
    String format = 'glb',
    String? marketplace,
  }) async {
    final res = await _dio.get('/models/$modelUuid/download', queryParameters: {
      'format': format,
      if (marketplace != null) 'marketplace': marketplace,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> getModel(String modelUuid) async {
    final res = await _dio.get('/models/$modelUuid');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> restoreSources({required String modelUuid}) async {
    final res = await _dio.post('/models/$modelUuid/restore-sources');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> extendStorage({required String modelUuid}) async {
    final res = await _dio.post('/models/$modelUuid/extend-storage');
    return Map<String, dynamic>.from(res.data as Map);
  }

  /// §6.10 — стоимость импорта GLB (tariff import_glb).
  Future<Map<String, dynamic>> importModelPrice() async {
    final res = await _dio.get('/models/import/price');
    return Map<String, dynamic>.from(res.data as Map);
  }

  /// §6.10 — presigned PUT для imports/{uuid}/model.glb (Owner).
  Future<Map<String, dynamic>> prepareModelImport() async {
    final res = await _dio.post('/models/import/prepare');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> importModel({
    required String glbKey,
    required int companyId,
    required String category,
    String? displayName,
    String? modelUuid,
  }) async {
    final res = await _dio.post('/models/import', data: {
      'glb_key': glbKey,
      'company_id': companyId,
      'category': category,
      if (displayName != null && displayName.isNotEmpty) 'display_name': displayName,
      if (modelUuid != null) 'model_uuid': modelUuid,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  /// §9.1.2 — Owner: продлить хранение исходников всех моделей компании.
  Future<Map<String, dynamic>> massExtendCompanyStorage() async {
    final res = await _dio.post('/company/models/mass-extend-storage');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> trashModel({required String modelUuid}) async {
    final res = await _dio.post('/models/$modelUuid/trash');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<List<Map<String, dynamic>>> listTrashModels() async {
    final res = await _dio.get('/models/trash');
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> getBalance() async {
    final res = await _dio.get('/user/balance');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<List<Map<String, dynamic>>> listTransactions({
    String? dateFrom,
    String? dateTo,
    String? type,
    int limit = 20,
    int offset = 0,
  }) async {
    final res = await _dio.get('/user/transactions', queryParameters: {
      if (dateFrom != null && dateFrom.isNotEmpty) 'from': dateFrom,
      if (dateTo != null && dateTo.isNotEmpty) 'to': dateTo,
      if (type != null && type.isNotEmpty && type != 'all') 'type': type,
      'limit': limit,
      'offset': offset,
    });
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> listTransactionsPage({
    String? dateFrom,
    String? dateTo,
    String? type,
    int limit = 20,
    int offset = 0,
  }) async {
    final res = await _dio.get('/user/transactions', queryParameters: {
      if (dateFrom != null && dateFrom.isNotEmpty) 'from': dateFrom,
      if (dateTo != null && dateTo.isNotEmpty) 'to': dateTo,
      if (type != null && type.isNotEmpty && type != 'all') 'type': type,
      'limit': limit,
      'offset': offset,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> topupCompanyBalance({
    required int amount,
    String paymentMethod = 'redirect',
  }) async {
    final res = await _dio.post('/company/balance/topup', data: {
      'amount': amount,
      'payment_method': paymentMethod,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> topupBalance({
    required int amount,
    String paymentMethod = 'redirect',
  }) async {
    final res = await _dio.post('/user/balance/topup', data: {
      'amount': amount,
      'payment_method': paymentMethod,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  /// §8 — транзакции компании (Owner/Manager + can_view_finance).
  Future<List<Map<String, dynamic>>> listCompanyMine() async {
    final res = await _dio.get('/company/mine');
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> listCompanyTransactionsPage({
    int? userId,
    String? dateFrom,
    String? dateTo,
    String? type,
    int limit = 20,
    int offset = 0,
  }) async {
    final res = await _dio.get('/company/transactions', queryParameters: {
      if (userId != null) 'user_id': userId,
      if (dateFrom != null && dateFrom.isNotEmpty) 'from': dateFrom,
      if (dateTo != null && dateTo.isNotEmpty) 'to': dateTo,
      if (type != null && type.isNotEmpty && type != 'all') 'type': type,
      'limit': limit,
      'offset': offset,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<List<Map<String, dynamic>>> listCompanyTransactions({
    int? userId,
    String? dateFrom,
    String? dateTo,
    String? type,
    int limit = 20,
    int offset = 0,
  }) async {
    final page = await listCompanyTransactionsPage(
      userId: userId,
      dateFrom: dateFrom,
      dateTo: dateTo,
      type: type,
      limit: limit,
      offset: offset,
    );
    final items = page['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> pollTopupPayment(String paymentId, {bool company = false}) async {
    final path = company
        ? '/company/balance/payment/$paymentId'
        : '/user/balance/payment/$paymentId';
    final res = await _dio.get(path);
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> listNotifications({int limit = 50, int offset = 0}) async {
    final res = await _dio.get('/user/notifications', queryParameters: {
      'limit': limit,
      'offset': offset,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<void> markAllNotificationsRead() async {
    await _dio.post('/user/notifications/read-all');
  }

  Future<void> markNotificationRead(int id) async {
    await _dio.post('/user/notifications/$id/read');
  }

  Future<void> clearNotifications() async {
    await _dio.delete('/user/notifications');
  }

  Future<List<int>> exportCompanyTransactionsCsv({
    int? userId,
    String? dateFrom,
    String? dateTo,
    String? type,
  }) async {
    final res = await _dio.get<List<int>>(
      '/company/transactions/export',
      queryParameters: {
        if (userId != null) 'user_id': userId,
        if (dateFrom != null && dateFrom.isNotEmpty) 'from': dateFrom,
        if (dateTo != null && dateTo.isNotEmpty) 'to': dateTo,
        if (type != null && type.isNotEmpty && type != 'all') 'type': type,
      },
      options: Options(responseType: ResponseType.bytes),
    );
    return res.data ?? [];
  }

  Future<Map<String, dynamic>> listCompanyMembers() async {
    final res = await _dio.get('/company/members');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> restoreFromTrash({required String modelUuid}) async {
    final res = await _dio.post('/models/$modelUuid/restore-from-trash');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> markPublished({
    required String modelUuid,
    required String marketplace,
  }) async {
    final res = await _dio.post('/models/$modelUuid/publish/mark', data: {
      'marketplace': marketplace,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> addPublicationLink({
    required String modelUuid,
    required String url,
  }) async {
    final res = await _dio.post('/models/$modelUuid/publication/links', data: {
      'url': url,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> marketplaceUpload({
    required String modelUuid,
    required String marketplace,
    required String sku,
  }) async {
    final res = await _dio.post('/models/$modelUuid/marketplace-upload', data: {
      'marketplace': marketplace,
      'sku': sku,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<String?> previewUrl(String modelUuid) async {
    final res = await _dio.get('/models/$modelUuid/preview');
    return (res.data as Map)['preview_url']?.toString();
  }

  Future<Map<String, dynamic>> createShootLink({
    required int companyId,
    required String category,
    required String tier,
    int ttlHours = 24,
    int maxUses = 3,
  }) async {
    final res = await _dio.post('/company/shoot_link', data: {
      'company_id': companyId,
      'category': category,
      'tier': tier,
      'ttl_hours': ttlHours,
      'max_uses': maxUses,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> getShootByToken(String token) async {
    final res = await _dio.get('/shoot/$token');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> completeShootByToken(String token) async {
    final res = await _dio.post('/shoot/$token/complete');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<void> registerDevice({
    required String token,
    required String platform,
    String? appVersion,
  }) async {
    await _dio.post('/user/devices', data: {
      'token': token,
      'platform': platform,
      if (appVersion != null) 'app_version': appVersion,
    });
  }

  Future<List<Map<String, dynamic>>> getFaq() async {
    final res = await _dio.get('/faq');
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<List<Map<String, dynamic>>> listSupportQuestions() async {
    final res = await _dio.get('/support/questions');
    final items = (res.data as Map)['items'] as List? ?? [];
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  Future<Map<String, dynamic>> getSupportQuestion(int id) async {
    final res = await _dio.get('/support/questions/$id');
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<Map<String, dynamic>> askSupport({
    required String subject,
    required String message,
    String category = 'general',
  }) async {
    final res = await _dio.post('/support/questions', data: {
      'subject': subject,
      'message': message,
      'category': category,
    });
    return Map<String, dynamic>.from(res.data as Map);
  }

  Future<void> replySupport(int id, String message) async {
    await _dio.post('/support/questions/$id/messages', data: {'message': message});
  }

  Future<void> closeSupport(int id) async {
    await _dio.post('/support/questions/$id/close');
  }
}
