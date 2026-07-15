import 'dart:convert';

import 'package:archive/archive.dart';
import 'package:http/http.dart' as http;
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Облачный бэкап черновиков TTL 7 дней §3.3.2.
class CloudDraftBackupService {
  CloudDraftBackupService._();
  static final instance = CloudDraftBackupService._();

  static const _promptKey = 'cloud_restore_prompt_done';

  Future<void> syncDraft(ApiClient api, ShootDraft draft) async {
    final count = await ShootStorage.instance.capturedCount(draft.modelUuid);
    if (count == 0) return;

    final zipBytes = await ShootStorage.instance.buildPartialZipBytes(draft);
    final prepared = await api.prepareDraftBackup(
      modelUuid: draft.modelUuid,
      category: draft.category.api,
      capturedCount: count,
      tier: draft.tier.api,
    );
    final uploadUrl = prepared['upload_url'] as String;
    await http.put(
      Uri.parse(uploadUrl),
      headers: {'Content-Type': 'application/zip'},
      body: zipBytes,
    );
  }

  Future<List<Map<String, dynamic>>> listRemote(ApiClient api) async {
    return await api.listDraftBackups();
  }

  Future<bool> shouldOfferRestore(ApiClient api) async {
    final prefs = await SharedPreferences.getInstance();
    if (prefs.getBool(_promptKey) == true) return false;
    if (await ShootStorage.instance.hasResumableDraft()) return false;

    final remote = await listRemote(api);
    if (remote.isEmpty) return false;

    for (final item in remote) {
      final uuid = item['model_uuid']?.toString();
      if (uuid == null) continue;
      final local = await ShootStorage.instance.loadDraft(uuid);
      if (local == null) return true;
      final localCount = await ShootStorage.instance.capturedCount(uuid);
      final remoteCount = (item['captured_count'] as num?)?.toInt() ?? 0;
      if (remoteCount > localCount) return true;
    }
    return false;
  }

  Future<void> markPromptDone() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_promptKey, true);
  }

  Future<ShootDraft?> restore(ApiClient api, String modelUuid) async {
    final res = await api.restoreDraftBackup(modelUuid);
    final url = res['download_url']?.toString();
    if (url == null) throw StateError('Нет URL бэкапа');

    final resp = await http.get(Uri.parse(url));
    if (resp.statusCode != 200) {
      throw StateError('Не удалось скачать бэкап (${resp.statusCode})');
    }

    final archive = ZipDecoder().decodeBytes(resp.bodyBytes);
    ArchiveFile? metaFile;
    for (final f in archive.files) {
      if (f.name == 'metadata.json') metaFile = f;
    }
    if (metaFile == null) throw StateError('metadata.json отсутствует в бэкапе');

    final meta = jsonDecode(utf8.decode(metaFile.content as List<int>)) as Map<String, dynamic>;
    final draft = ShootDraft.fromJson(meta);

    for (final f in archive.files) {
      if (!f.isFile || f.name == 'metadata.json') continue;
      final idx = kGuidedDomeAngles.indexWhere((a) => a.filename == f.name);
      if (idx >= 0) {
        await ShootStorage.instance.savePhoto(
          draft.modelUuid,
          idx,
          f.content as List<int>,
        );
      }
    }
    await ShootStorage.instance.writeMetadata(draft);
    return draft;
  }
}
