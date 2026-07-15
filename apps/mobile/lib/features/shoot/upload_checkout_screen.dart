import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/services/photo_encryption.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';

/// Загрузка 12 JPEG + ZIP SHA-256 → checkout §3.6.3.
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
  double _progress = 0;
  String _status = 'Подготовка…';
  String? _error;
  bool _running = false;

  Future<void> _run() async {
    if (_running) return;
    setState(() {
      _running = true;
      _error = null;
      _progress = 0;
    });

    try {
      final draft = await ShootStorage.instance.loadActiveDraft();
      if (draft == null || draft.modelUuid != widget.modelUuid) {
        throw StateError('Черновик съёмки не найден');
      }
      if (draft.forbidden.isNotEmpty) {
        throw StateError(
          'Вы выбрали запрещённую категорию. Заказ будет отклонён без возврата средств.',
        );
      }

      setState(() => _status = 'Сборка ZIP + SHA-256…');
      final zip = await ShootStorage.instance.buildZip(draft);
      draft.zipSha256 = zip.sha256;
      await ShootStorage.instance.writeMetadata(draft);
      setState(() {
        _status = 'SHA-256: ${zip.sha256.substring(0, 12)}…';
        _progress = 0.1;
      });

      setState(() => _status = 'Получение presigned URL…');
      final prepared = await widget.api.preparePhotos(
        taskUuid: draft.modelUuid,
        companyId: widget.session.companyId,
      );
      final taskUuid = prepared['task_uuid'] as String;
      final encryptionRequired = prepared['encryption_required'] == true ||
          widget.session.e2ePhotoEncryption;
      final uploads = (prepared['uploads'] as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      final photos = await ShootStorage.instance.listPhotos(draft.modelUuid);

      String? encKeyB64;
      if (encryptionRequired) {
        encKeyB64 = PhotoEncryptionService.instance.generateKeyB64();
        await widget.api.registerPhotoEncryptionKey(
          taskUuid: taskUuid,
          keyB64: encKeyB64,
        );
        setState(() => _status = 'E2E шифрование фото…');
      }

      for (var i = 0; i < uploads.length; i++) {
        final file = photos[i];
        if (file == null) throw StateError('Нет файла ракурса $i');
        setState(() {
          _status = encryptionRequired
              ? 'Шифрование и загрузка ${i + 1}/12…'
              : 'Загрузка ${i + 1}/12…';
          _progress = 0.1 + (i / 12) * 0.85;
        });
        Uint8List? payload;
        var contentType = uploads[i]['content_type'] as String? ?? 'image/jpeg';
        if (encryptionRequired && encKeyB64 != null) {
          final raw = await file.readAsBytes();
          payload = PhotoEncryptionService.instance.encryptJpeg(raw, encKeyB64);
          contentType = 'application/octet-stream';
        }
        await widget.api.uploadPhotoPresigned(
          uploadUrl: uploads[i]['upload_url'] as String,
          file: file,
          contentType: contentType,
          bytesOverride: payload,
        );
      }

      draft.photosPrefix = prepared['photos_prefix'] as String?;
      draft.photosUploaded = true;
      await ShootStorage.instance.writeMetadata(draft);

      if (!mounted) return;
      context.pushReplacement('/home/shoot/checkout', extra: widget.modelUuid);
    } catch (e) {
      setState(() {
        _error = formatApiError(e);
        _running = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return FScaffold(
      header: FHeader.nested(
        title: const Text('Загрузка фото'),
        prefixes: [FHeaderAction.back(onPress: _running ? null : () => context.pop())],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(_status),
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: _progress,
              color: AppColors.accent,
              backgroundColor: AppColors.surface,
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: const TextStyle(color: AppColors.error)),
            ],
            const Spacer(),
            FButton(
              onPress: _running ? null : _run,
              child: Text(_running ? 'Загрузка…' : 'Загрузить 12 фото'),
            ),
          ],
        ),
      ),
    );
  }
}
