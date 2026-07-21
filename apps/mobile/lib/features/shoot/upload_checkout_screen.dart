import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
import 'package:kwork_mobile/services/photo_encryption.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/cloud_draft_backup_service.dart';
import 'package:kwork_mobile/services/upload_progress_service.dart';

/// Загрузка 12 JPEG + ZIP SHA-256 → checkout §3.6.3 / resumable §3.4.1.
class UploadCheckoutScreen extends StatefulWidget {
  const UploadCheckoutScreen({
    super.key,
    required this.api,
    required this.session,
    required this.modelUuid,
  });

  final ApiClient api;
  final AppSession session;
  final String modelUuid;

  @override
  State<UploadCheckoutScreen> createState() => _UploadCheckoutScreenState();
}

class _UploadCheckoutScreenState extends State<UploadCheckoutScreen> {
  final _progressSvc = UploadProgressService.instance;
  double _progress = 0;
  String _statusKey = 'preparing';
  String _statusExtra = '';
  String? _error;
  bool _running = false;
  bool _hasResume = false;

  @override
  void initState() {
    super.initState();
    AnalyticsService.instance.track('screen_view', {'screen': 'shoot_upload'});
    _checkResume();
  }

  String _statusText(AppLocalizations l10n) {
    return switch (_statusKey) {
      'preparing' => l10n.uploadPreparing,
      'resume' => l10n.uploadResumeFound(_statusExtra),
      'building' => l10n.uploadBuildingZip,
      'sha256' => l10n.uploadSha256(_statusExtra),
      'presigned' => l10n.uploadPresigned,
      'encrypting' => l10n.uploadEncrypting,
      'progress' => l10n.uploadProgress(_statusExtra.split('/').first, _statusExtra.split('/').last),
      'uploaded' => l10n.uploadUploaded(_statusExtra),
      'interrupted' => l10n.uploadInterrupted,
      'retry' => l10n.uploadProgress(_statusExtra.split('/').first, _statusExtra.split('/').last),
      _ => _statusExtra.isNotEmpty ? _statusExtra : l10n.uploadPreparing,
    };
  }

  Future<void> _checkResume() async {
    final saved = await _progressSvc.load(widget.modelUuid);
    if (saved != null && saved['completed'] != true) {
      if (mounted) {
        setState(() {
          _hasResume = true;
          _statusKey = 'resume';
          _statusExtra = '${_progressSvc.uploadedIndices(saved).length}';
        });
      }
    }
  }

  Future<void> _run({bool resume = false}) async {
    if (_running) return;
    setState(() {
      _running = true;
      _error = null;
      if (!resume) _progress = 0;
    });

    try {
      final l10n = AppLocalizations.of(context)!;
      final draft = await ShootStorage.instance.loadActiveDraft();
      if (draft == null || draft.modelUuid != widget.modelUuid) {
        throw StateError(l10n.ucDraftNotFound);
      }
      if (draft.forbidden.isNotEmpty) {
        throw StateError(l10n.ucForbiddenCategory);
      }

      try {
        await CloudDraftBackupService.instance.syncDraft(widget.api, draft);
      } catch (_) {}

      var progress = resume ? await _progressSvc.load(widget.modelUuid) : null;

      if (!resume || progress == null) {
        setState(() {
          _statusKey = 'building';
          _statusExtra = '';
        });
        final zip = await ShootStorage.instance.buildZip(draft);
        draft.zipSha256 = zip.sha256;
        await ShootStorage.instance.writeMetadata(draft);
        progress = {
          'model_uuid': draft.modelUuid,
          'zip_sha256': zip.sha256,
          'upload_mode': 'zip',
          'uploaded_parts': <int>[],
          'completed': false,
        };
        await _progressSvc.save(draft.modelUuid, progress);
        setState(() {
          _statusKey = 'sha256';
          _statusExtra = zip.sha256.substring(0, 12);
          _progress = 0.05;
        });
      } else {
        draft.zipSha256 = progress['zip_sha256']?.toString() ?? draft.zipSha256;
      }

      final prepared = await widget.api.preparePhotos(
        taskUuid: progress['task_uuid']?.toString() ?? draft.modelUuid,
        companyId: widget.session.companyId,
      );
      final taskUuid = prepared['task_uuid'] as String;
      final encryptionRequired = prepared['encryption_required'] == true ||
          widget.session.e2ePhotoEncryption;
      progress!['task_uuid'] = taskUuid;
      progress['photos_prefix'] = prepared['photos_prefix'];
      progress['encryption_required'] = encryptionRequired;
      await _progressSvc.save(draft.modelUuid, progress);

      if (encryptionRequired) {
        await _runPresignedUpload(
          draft: draft,
          progress: progress,
          prepared: prepared,
          taskUuid: taskUuid,
          encryptionRequired: encryptionRequired,
        );
      } else {
        await _runZipUpload(draft: draft, progress: progress, taskUuid: taskUuid);
      }

      draft.photosPrefix = progress['photos_prefix']?.toString();
      draft.photosUploaded = true;
      await ShootStorage.instance.writeMetadata(draft);

      progress['completed'] = true;
      await _progressSvc.save(draft.modelUuid, progress);
      await _progressSvc.clear(draft.modelUuid);

      if (!mounted) return;
      context.pushReplacement('/home/shoot/checkout', extra: widget.modelUuid);
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = formatApiError(e);
          _running = false;
          _hasResume = true;
          _statusKey = 'interrupted';
          _statusExtra = '';
        });
      }
    }
  }

  Future<void> _runZipUpload({
    required ShootDraft draft,
    required Map<String, dynamic> progress,
    required String taskUuid,
  }) async {
    final zip = await ShootStorage.instance.buildZip(draft);
    final zipBytes = await zip.zip.readAsBytes();
    final sha256 = zip.sha256;
    progress['zip_sha256'] = sha256;

    var uploadId = progress['upload_id']?.toString();
    var chunkSize = (progress['chunk_size'] as num?)?.toInt() ?? 524288;
    var totalChunks = (progress['total_chunks'] as num?)?.toInt();

    if (uploadId == null || uploadId.isEmpty) {
      setState(() {
        _statusKey = 'presigned';
        _statusExtra = '';
      });
      final init = await widget.api.initZipUpload(
        taskUuid: taskUuid,
        totalSize: zipBytes.length,
        sha256: sha256,
        chunkSize: chunkSize,
      );
      uploadId = init['upload_id'] as String;
      chunkSize = (init['chunk_size'] as num).toInt();
      totalChunks = (init['total_chunks'] as num).toInt();
      progress['upload_id'] = uploadId;
      progress['chunk_size'] = chunkSize;
      progress['total_chunks'] = totalChunks;
      progress['upload_mode'] = 'zip';
      await _progressSvc.save(draft.modelUuid, progress);
    }
    totalChunks ??= (zipBytes.length + chunkSize - 1) ~/ chunkSize;

    final uploaded = _progressSvc.uploadedZipParts(progress).toSet();
    for (var part = 0; part < totalChunks; part++) {
      if (uploaded.contains(part)) continue;
      final start = part * chunkSize;
      final end = start + chunkSize > zipBytes.length ? zipBytes.length : start + chunkSize;
      final chunk = Uint8List.sublistView(zipBytes, start, end);
      await _uploadZipChunkWithRetry(
        uploadId: uploadId!,
        partIndex: part,
        bytes: chunk,
        total: totalChunks,
      );
      uploaded.add(part);
      progress['uploaded_parts'] = uploaded.toList()..sort();
      await _progressSvc.save(draft.modelUuid, progress);
      if (mounted) {
        setState(() {
          _statusKey = 'progress';
          _statusExtra = '${uploaded.length}/$totalChunks';
          _progress = 0.1 + (uploaded.length / totalChunks) * 0.85;
        });
      }
    }

    await widget.api.completeZipUpload(uploadId!);
  }

  Future<void> _runPresignedUpload({
    required ShootDraft draft,
    required Map<String, dynamic> progress,
    required Map<String, dynamic> prepared,
    required String taskUuid,
    required bool encryptionRequired,
  }) async {
    final l10n = AppLocalizations.of(context)!;
    final uploads = (prepared['uploads'] as List)
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    var uploaded = _progressSvc.uploadedIndices(progress).toSet();

    String? encKeyB64;
    if (encryptionRequired) {
      encKeyB64 = await _progressSvc.loadEncKey(draft.modelUuid);
      if (encKeyB64 == null && progress['enc_registered'] != true) {
        encKeyB64 = PhotoEncryptionService.instance.generateKeyB64();
        await widget.api.registerPhotoEncryptionKey(
          taskUuid: taskUuid,
          keyB64: encKeyB64,
        );
        await _progressSvc.saveEncKey(draft.modelUuid, encKeyB64);
        progress['enc_registered'] = true;
        await _progressSvc.save(draft.modelUuid, progress);
      }
      setState(() {
        _statusKey = 'encrypting';
        _statusExtra = '';
      });
    }

    setState(() {
      _statusKey = 'presigned';
      _statusExtra = '';
    });

    final photos = await ShootStorage.instance.listPhotos(draft.modelUuid);
    for (var i = 0; i < uploads.length; i++) {
      if (uploaded.contains(i)) continue;
      final file = photos[i];
      if (file == null) throw StateError(l10n.ucNoViewFile('$i'));
      await _uploadWithRetry(
        index: i,
        total: uploads.length,
        upload: uploads[i],
        file: file,
        encryptionRequired: encryptionRequired,
        encKeyB64: encKeyB64,
      );
      uploaded.add(i);
      progress['uploaded_indices'] = uploaded.toList()..sort();
      await _progressSvc.save(draft.modelUuid, progress);
      if (mounted) {
        setState(() {
          _statusKey = 'uploaded';
          _statusExtra = '${uploaded.length}';
          _progress = 0.1 + (uploaded.length / 12) * 0.85;
        });
      }
    }
  }

  Future<void> _uploadZipChunkWithRetry({
    required String uploadId,
    required int partIndex,
    required Uint8List bytes,
    required int total,
  }) async {
    Object? lastError;
    for (var attempt = 0; attempt < 4; attempt++) {
      if (attempt > 0) {
        await Future<void>.delayed(Duration(seconds: attempt * 2));
        if (mounted) {
          setState(() {
            _statusKey = 'retry';
            _statusExtra = '${partIndex + 1}/$total';
          });
        }
      }
      try {
        await widget.api.uploadZipChunk(
          uploadId: uploadId,
          partIndex: partIndex,
          bytes: bytes,
        );
        return;
      } catch (e) {
        lastError = e;
      }
    }
    throw lastError ?? StateError('zip chunk upload failed');
  }

  Future<void> _uploadWithRetry({
    required int index,
    required int total,
    required Map<String, dynamic> upload,
    required File file,
    required bool encryptionRequired,
    String? encKeyB64,
  }) async {
    Object? lastError;
    for (var attempt = 0; attempt < 4; attempt++) {
      if (attempt > 0) {
        await Future<void>.delayed(Duration(seconds: attempt * 2));
        if (mounted) {
          setState(() {
            _statusKey = 'retry';
            _statusExtra = '${index + 1}/$total';
          });
        }
      }
      try {
        Uint8List? payload;
        var contentType = upload['content_type'] as String? ?? 'image/jpeg';
        if (encryptionRequired && encKeyB64 != null) {
          final raw = await file.readAsBytes();
          payload = PhotoEncryptionService.instance.encryptJpeg(raw, encKeyB64);
          contentType = 'application/octet-stream';
        }
        await widget.api.uploadPhotoPresigned(
          uploadUrl: upload['upload_url'] as String,
          file: file,
          contentType: contentType,
          bytesOverride: payload,
        );
        return;
      } catch (e) {
        lastError = e;
      }
    }
    throw lastError ?? StateError('upload failed');
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return FScaffold(
      header: FHeader.nested(
        title: Text(l10n.uploadPhotoTitle),
        prefixes: [FHeaderAction.back(onPress: _running ? null : () => context.pop())],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (_hasResume && !_running)
              Text(
                l10n.uploadResumeHint,
                style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
            const SizedBox(height: 8),
            Text(_statusText(l10n)),
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: _progress > 0 ? _progress : null,
              color: AppColors.accent,
              backgroundColor: AppColors.surface,
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: const TextStyle(color: AppColors.error)),
            ],
            const Spacer(),
            FButton(
              onPress: _running
                  ? null
                  : () => _run(resume: _hasResume),
              child: Text(
                _running
                    ? l10n.uploadUploading
                    : (_hasResume ? l10n.uploadContinue : l10n.upload12Photos),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
