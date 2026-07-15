import 'dart:convert';
import 'dart:io';

import 'package:archive/archive.dart';
import 'package:http/http.dart' as http;
import 'package:kwork_mobile/core/api.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Локальные GLB, избранное, автоочистка, экспорт ZIP (§3.3.2).
class LocalModelLibrary {
  LocalModelLibrary._();
  static final instance = LocalModelLibrary._();

  static const _favoritesKey = 'favorite_models';
  static const _autoCleanupKey = 'auto_cleanup_enabled';
  static const _autoCleanupDaysKey = 'auto_cleanup_days';
  static const _autoDownloadKey = 'auto_download_glb';

  Future<Directory> _modelsRoot() async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory(p.join(docs.path, 'models'));
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  Future<File> glbFile(String modelUuid) async {
    return File(p.join((await _modelsRoot()).path, modelUuid, 'model.glb'));
  }

  Future<bool> hasLocalGlb(String modelUuid) async {
    return (await glbFile(modelUuid)).exists();
  }

  Future<Set<String>> favorites() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getStringList(_favoritesKey) ?? [];
    return raw.toSet();
  }

  Future<bool> isFavorite(String modelUuid) async {
    return (await favorites()).contains(modelUuid);
  }

  Future<void> setFavorite(String modelUuid, bool value) async {
    final prefs = await SharedPreferences.getInstance();
    final set = await favorites();
    if (value) {
      set.add(modelUuid);
    } else {
      set.remove(modelUuid);
    }
    await prefs.setStringList(_favoritesKey, set.toList());
  }

  bool get autoDownloadEnabled =>
      _cachedAutoDownload ?? true;

  bool? _cachedAutoDownload;

  Future<bool> loadAutoDownloadEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    _cachedAutoDownload = prefs.getBool(_autoDownloadKey) ?? true;
    return _cachedAutoDownload!;
  }

  Future<void> setAutoDownloadEnabled(bool value) async {
    _cachedAutoDownload = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_autoDownloadKey, value);
  }

  Future<bool> autoCleanupEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_autoCleanupKey) ?? false;
  }

  Future<void> setAutoCleanupEnabled(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_autoCleanupKey, value);
  }

  Future<int> autoCleanupDays() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getInt(_autoCleanupDaysKey) ?? 30;
  }

  Future<void> setAutoCleanupDays(int days) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setInt(_autoCleanupDaysKey, days);
  }

  Future<void> touchAccess(String modelUuid) async {
    final prefs = await SharedPreferences.getInstance();
    final map = _decodeAccessMap(prefs.getString('model_access_at'));
    map[modelUuid] = DateTime.now().toIso8601String();
    await prefs.setString('model_access_at', jsonEncode(map));
  }

  Map<String, String> _decodeAccessMap(String? raw) {
    if (raw == null || raw.isEmpty) return {};
    try {
      final j = jsonDecode(raw) as Map;
      return j.map((k, v) => MapEntry(k.toString(), v.toString()));
    } catch (_) {
      return {};
    }
  }

  Future<({int bytes, int models, int glbs})> storageStats() async {
    final root = await _modelsRoot();
    var bytes = 0;
    var models = 0;
    var glbs = 0;
    await for (final entity in root.list(recursive: true, followLinks: false)) {
      if (entity is File) {
        bytes += await entity.length();
        if (entity.path.endsWith('model.glb')) glbs++;
      }
    }
    await for (final entity in root.list(followLinks: false)) {
      if (entity is Directory) models++;
    }
    return (bytes: bytes, models: models, glbs: glbs);
  }

  String formatBytes(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(2)} GB';
  }

  Future<File?> downloadGlb({
    required ApiClient api,
    required String modelUuid,
  }) async {
    final dl = await api.downloadModel(modelUuid: modelUuid, format: 'glb');
    final url = dl['download_url']?.toString();
    if (url == null || url.isEmpty) return null;
    final res = await http.get(Uri.parse(url));
    if (res.statusCode < 200 || res.statusCode >= 300) {
      throw HttpException('GLB download failed: ${res.statusCode}');
    }
    final file = await glbFile(modelUuid);
    await file.parent.create(recursive: true);
    await file.writeAsBytes(res.bodyBytes, flush: true);
    await touchAccess(modelUuid);
    return file;
  }

  Future<void> downloadIfNeeded({
    required ApiClient api,
    required String modelUuid,
  }) async {
    if (!await loadAutoDownloadEnabled()) return;
    if (await hasLocalGlb(modelUuid)) return;
    try {
      await downloadGlb(api: api, modelUuid: modelUuid);
    } catch (_) {}
  }

  /// §3.5.3 — при запуске / «Мои модели»: скачать GLB для completed без локальной копии.
  /// [companyId] — корпоративный режим: заказы и модели компании (§3.5.3).
  Future<int> syncPendingDownloads(ApiClient api, {int? companyId}) async {
    if (!await loadAutoDownloadEnabled()) return 0;
    var count = 0;
    final seen = <String>{};

    try {
      final orders = await api.listOrders(companyId: companyId);
      for (final o in orders) {
        final status = o['status']?.toString().toLowerCase() ?? '';
        if (status != 'completed') continue;
        final uuid = o['task_uuid']?.toString();
        if (uuid == null || uuid.isEmpty || seen.contains(uuid)) continue;
        seen.add(uuid);
        if (await hasLocalGlb(uuid)) continue;
        try {
          await downloadGlb(api: api, modelUuid: uuid);
          count++;
        } catch (_) {}
      }
    } catch (_) {}

    try {
      final models = await api.listModels(companyId: companyId);
      for (final m in models) {
        final uuid = m['uuid']?.toString();
        if (uuid == null || seen.contains(uuid)) continue;
        final pub = m['publish_status']?.toString() ?? '';
        if (pub == 'import_validating' || pub == 'import_failed') continue;
        final glbUrl = m['glb_url']?.toString();
        if (glbUrl == null || glbUrl.isEmpty) continue;
        seen.add(uuid);
        if (await hasLocalGlb(uuid)) continue;
        try {
          await downloadGlb(api: api, modelUuid: uuid);
          count++;
        } catch (_) {}
      }
    } catch (_) {}

    return count;
  }

  Future<File> exportAllZip() async {
    final root = await _modelsRoot();
    final archive = Archive();
    await for (final entity in root.list(followLinks: false)) {
      if (entity is! Directory) continue;
      final uuid = p.basename(entity.path);
      final glb = File(p.join(entity.path, 'model.glb'));
      if (await glb.exists()) {
        final bytes = await glb.readAsBytes();
        archive.addFile(ArchiveFile('$uuid/model.glb', bytes.length, bytes));
      }
    }
    final encoded = ZipEncoder().encode(archive);
    final out = File(p.join(root.path, 'all_models_export.zip'));
    await out.writeAsBytes(encoded, flush: true);
    return out;
  }

  Future<int> runAutoCleanup() async {
    if (!await autoCleanupEnabled()) return 0;
    final days = await autoCleanupDays();
    final cutoff = DateTime.now().subtract(Duration(days: days));
    final fav = await favorites();
    final prefs = await SharedPreferences.getInstance();
    final access = _decodeAccessMap(prefs.getString('model_access_at'));
    final root = await _modelsRoot();
    var removed = 0;
    await for (final entity in root.list(followLinks: false)) {
      if (entity is! Directory) continue;
      final uuid = p.basename(entity.path);
      if (fav.contains(uuid)) continue;
      final glb = File(p.join(entity.path, 'model.glb'));
      if (!await glb.exists()) continue;
      final at = DateTime.tryParse(access[uuid] ?? '') ?? await glb.lastModified();
      if (at.isAfter(cutoff)) continue;
      await glb.delete();
      removed++;
    }
    return removed;
  }
}
