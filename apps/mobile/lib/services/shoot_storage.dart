import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:archive/archive.dart';
import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

/// Локальное хранение исходников §3.3.1.
class ShootDraft {
  ShootDraft({
    required this.modelUuid,
    required this.category,
    required this.createdAt,
    this.companyId,
    this.tier = Tier.small,
    this.forbidden = const [],
    this.scaleCalibration,
    this.reshootCounts = const {},
    this.birthDate,
    this.ghostScale = 1.0,
    this.zipSha256,
    this.photosPrefix,
    this.photosUploaded = false,
    this.displayName,
  });

  final String modelUuid;
  ProductCategory category;
  Tier tier;
  int? companyId;
  List<ForbiddenCategory> forbidden;
  Map<String, dynamic>? scaleCalibration;
  DateTime createdAt;
  Map<int, int> reshootCounts;
  String? birthDate;
  double ghostScale;
  String? zipSha256;
  String? photosPrefix;
  bool photosUploaded;
  String? displayName;

  Map<String, dynamic> toJson() => {
        'model_uuid': modelUuid,
        'category': category.api,
        'tier': tier.api,
        'company_id': companyId,
        'forbidden': forbidden.map((e) => e.api).toList(),
        'scale_calibration': scaleCalibration,
        'created_at': createdAt.toIso8601String(),
        'reshoot_counts': reshootCounts.map((k, v) => MapEntry('$k', v)),
        if (birthDate != null) 'birth_date': birthDate,
        'ghost_scale': ghostScale,
        if (zipSha256 != null) 'zip_sha256': zipSha256,
        if (photosPrefix != null) 'photos_prefix': photosPrefix,
        'photos_uploaded': photosUploaded,
        if (displayName != null && displayName!.isNotEmpty) 'display_name': displayName,
      };

  static ShootDraft fromJson(Map<String, dynamic> j) {
    return ShootDraft(
      modelUuid: j['model_uuid'] as String,
      category: ProductCategory.values.firstWhere(
        (e) => e.api == j['category'],
        orElse: () => ProductCategory.other,
      ),
      tier: Tier.values.firstWhere(
        (e) => e.api == j['tier'],
        orElse: () => Tier.small,
      ),
      companyId: j['company_id'] as int?,
      forbidden: [
        for (final f in (j['forbidden'] as List? ?? []))
          ForbiddenCategory.values.firstWhere(
            (e) => e.api == f,
            orElse: () => ForbiddenCategory.intimate,
          ),
      ],
      scaleCalibration: j['scale_calibration'] as Map<String, dynamic>?,
      createdAt: DateTime.tryParse(j['created_at']?.toString() ?? '') ??
          DateTime.now(),
      reshootCounts: {
        for (final e in ((j['reshoot_counts'] as Map?) ?? {}).entries)
          int.parse(e.key.toString()): e.value as int,
      },
      birthDate: j['birth_date']?.toString(),
      ghostScale: (j['ghost_scale'] as num?)?.toDouble() ?? 1.0,
      zipSha256: j['zip_sha256']?.toString(),
      photosPrefix: j['photos_prefix']?.toString(),
      photosUploaded: j['photos_uploaded'] == true,
      displayName: j['display_name']?.toString(),
    );
  }
}

class ShootStorage {
  ShootStorage._();
  static final instance = ShootStorage._();

  Future<Directory> _root() async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory(p.join(docs.path, 'models'));
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  Future<Directory> sourceDir(String modelUuid) async {
    final dir = Directory(p.join((await _root()).path, modelUuid, 'source_photos'));
    if (!await dir.exists()) await dir.create(recursive: true);
    return dir;
  }

  Future<File> photoFile(String modelUuid, int index) async {
    final angle = kGuidedDomeAngles[index];
    return File(p.join((await sourceDir(modelUuid)).path, angle.filename));
  }

  Future<void> savePhoto(String modelUuid, int index, List<int> jpegBytes) async {
    final f = await photoFile(modelUuid, index);
    await f.writeAsBytes(jpegBytes, flush: true);
  }

  Future<List<File?>> listPhotos(String modelUuid) async {
    return [
      for (var i = 0; i < kGuidedDomeCount; i++)
        await photoFile(modelUuid, i).then((f) async => await f.exists() ? f : null),
    ];
  }

  Future<int> capturedCount(String modelUuid) async {
    var n = 0;
    for (final f in await listPhotos(modelUuid)) {
      if (f != null) n++;
    }
    return n;
  }

  Future<File> writeMetadata(ShootDraft draft, {String? zipSha256}) async {
    final dir = Directory(p.join((await _root()).path, draft.modelUuid));
    if (!await dir.exists()) await dir.create(recursive: true);
    final meta = {
      ...draft.toJson(),
      if (zipSha256 != null) 'zip_sha256': zipSha256,
    };
    final f = File(p.join(dir.path, 'metadata.json'));
    await f.writeAsString(const JsonEncoder.withIndent('  ').convert(meta));
    final index = File(p.join((await _root()).path, 'draft_index.json'));
    await index.writeAsString(jsonEncode({'active': draft.modelUuid, ...meta}));
    return f;
  }

  Future<ShootDraft?> loadActiveDraft() async {
    final index = File(p.join((await _root()).path, 'draft_index.json'));
    if (!await index.exists()) return null;
    final j = jsonDecode(await index.readAsString()) as Map<String, dynamic>;
    final created = DateTime.tryParse(j['created_at']?.toString() ?? '');
    if (created != null && DateTime.now().difference(created).inDays > 7) {
      return null;
    }
    return ShootDraft.fromJson(j);
  }

  Future<void> clearActiveDraft() async {
    final index = File(p.join((await _root()).path, 'draft_index.json'));
    if (await index.exists()) await index.delete();
  }

  Future<void> discardDraft(String modelUuid) async {
    await clearActiveDraft();
    final dir = Directory(p.join((await _root()).path, modelUuid));
    if (await dir.exists()) await dir.delete(recursive: true);
  }

  Future<bool> hasResumableDraft() async {
    final draft = await loadActiveDraft();
    if (draft == null) return false;
    final n = await capturedCount(draft.modelUuid);
    return n > 0 && n < kGuidedDomeCount;
  }

  Future<int> resumeIndex(String modelUuid) async {
    final photos = await listPhotos(modelUuid);
    for (var i = 0; i < kGuidedDomeCount; i++) {
      if (photos[i] == null) return i;
    }
    return kGuidedDomeCount - 1;
  }

  Future<ShootDraft?> loadDraft(String modelUuid) async {
    final f = File(p.join((await _root()).path, modelUuid, 'metadata.json'));
    if (!await f.exists()) return loadActiveDraft();
    final j = jsonDecode(await f.readAsString()) as Map<String, dynamic>;
    return ShootDraft.fromJson(j);
  }

  /// ZIP 12 JPEG + metadata.json, SHA-256 (§3.6.3).
  Future<({File zip, String sha256})> buildZip(ShootDraft draft) async {
    final archive = Archive();
    final photos = await listPhotos(draft.modelUuid);
    for (var i = 0; i < kGuidedDomeCount; i++) {
      final f = photos[i];
      if (f == null) throw StateError('Нет фото ракурса ${i + 1}');
      final bytes = await f.readAsBytes();
      archive.addFile(ArchiveFile(kGuidedDomeAngles[i].filename, bytes.length, bytes));
    }
    final metaBytes = utf8.encode(jsonEncode(draft.toJson()));
    archive.addFile(ArchiveFile('metadata.json', metaBytes.length, metaBytes));

    final encoded = ZipEncoder().encode(archive);
    final digest = sha256.convert(encoded).toString();

    final zipPath = p.join((await _root()).path, draft.modelUuid, 'source.zip');
    final zipFile = File(zipPath);
    await zipFile.writeAsBytes(encoded, flush: true);
    await writeMetadata(draft, zipSha256: digest);
    return (zip: zipFile, sha256: digest);
  }

  String newUuid() => const Uuid().v4();

  /// Копия 12 фото для перегенерации (новый task_uuid).
  Future<String> cloneForRegeneration({
    required String sourceModelUuid,
    required ProductCategory category,
    required Tier tier,
    int? companyId,
    Map<String, dynamic>? scaleCalibration,
    String? birthDate,
  }) async {
    final newUuid = this.newUuid();
    for (var i = 0; i < kGuidedDomeCount; i++) {
      final src = await photoFile(sourceModelUuid, i);
      if (!await src.exists()) {
        throw StateError('Нет локального фото ракурса ${i + 1}');
      }
      final dst = await photoFile(newUuid, i);
      await dst.writeAsBytes(await src.readAsBytes(), flush: true);
    }
    final draft = ShootDraft(
      modelUuid: newUuid,
      category: category,
      tier: tier,
      companyId: companyId,
      scaleCalibration: scaleCalibration,
      birthDate: birthDate,
      createdAt: DateTime.now(),
    );
    await writeMetadata(draft);
    return newUuid;
  }
}
