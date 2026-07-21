import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Прогресс загрузки 12 фото §3.4.1 — persist для resume после kill app.
class UploadProgressService {
  UploadProgressService._();
  static final instance = UploadProgressService._();

  static const _keyPrefix = 'upload_progress_';
  static const _encKeyPrefix = 'upload_enc_key_';
  final _secure = const FlutterSecureStorage();

  Future<Map<String, dynamic>?> load(String modelUuid) async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('$_keyPrefix$modelUuid');
    if (raw == null || raw.isEmpty) return null;
    try {
      return Map<String, dynamic>.from(jsonDecode(raw) as Map);
    } catch (_) {
      return null;
    }
  }

  Future<void> save(String modelUuid, Map<String, dynamic> data) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('$_keyPrefix$modelUuid', jsonEncode(data));
  }

  Future<void> clear(String modelUuid) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('$_keyPrefix$modelUuid');
    await _secure.delete(key: '$_encKeyPrefix$modelUuid');
  }

  Future<String?> loadEncKey(String modelUuid) async {
    return _secure.read(key: '$_encKeyPrefix$modelUuid');
  }

  Future<void> saveEncKey(String modelUuid, String keyB64) async {
    await _secure.write(key: '$_encKeyPrefix$modelUuid', value: keyB64);
  }

  /// Индексы 0..11 уже загруженные на сервер (presigned path).
  List<int> uploadedIndices(Map<String, dynamic>? progress) {
    if (progress == null) return [];
    final raw = progress['uploaded_indices'];
    if (raw is! List) return [];
    return raw.map((e) => (e as num).toInt()).toList();
  }

  /// Индексы чанков ZIP (multipart path §3.4.1).
  List<int> uploadedZipParts(Map<String, dynamic>? progress) {
    if (progress == null) return [];
    final raw = progress['uploaded_parts'];
    if (raw is! List) return [];
    return raw.map((e) => (e as num).toInt()).toList();
  }

  bool usesZipMode(Map<String, dynamic>? progress) =>
      progress?['upload_mode'] == 'zip' || progress?['upload_id'] != null;

  Future<Map<String, dynamic>?> findPending() async {
    final prefs = await SharedPreferences.getInstance();
    for (final k in prefs.getKeys()) {
      if (!k.startsWith(_keyPrefix)) continue;
      final raw = prefs.getString(k);
      if (raw == null) continue;
      try {
        final j = Map<String, dynamic>.from(jsonDecode(raw) as Map);
        if (j['completed'] != true) {
          j['_model_uuid'] = k.substring(_keyPrefix.length);
          return j;
        }
      } catch (_) {}
    }
    return null;
  }

  /// Краткая сводка для баннера на Home (§3.4.1 resume).
  Future<({String modelUuid, int uploaded, int total})?> pendingSummary() async {
    final p = await findPending();
    if (p == null) return null;
    final uuid = p['_model_uuid']?.toString();
    if (uuid == null || uuid.isEmpty) return null;
    return (
      modelUuid: uuid,
      uploaded: uploadedIndices(p).length,
      total: 12,
    );
  }
}
