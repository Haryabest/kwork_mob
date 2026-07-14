import 'dart:io' show Platform;
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/services/photo_encryption.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';

/// ZIP/SHA-256 + prepare + presigned upload + create order (§3.4 / §3.6.3).
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
  final _promo = TextEditingController();

  @override
  void dispose() {
    _promo.dispose();
    super.dispose();
  }

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
        encKeyB64 = await PhotoEncryptionService.instance.generateKeyB64();
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
          _progress = 0.1 + (i / 12) * 0.7;
        });
        Uint8List? payload;
        var contentType = uploads[i]['content_type'] as String? ?? 'image/jpeg';
        if (encryptionRequired && encKeyB64 != null) {
          final raw = await file.readAsBytes();
          payload = await PhotoEncryptionService.instance.encryptJpeg(
            raw,
            encKeyB64,
          );
          contentType = 'application/octet-stream';
        }
        await widget.api.uploadPhotoPresigned(
          uploadUrl: uploads[i]['upload_url'] as String,
          file: file,
          contentType: contentType,
          bytesOverride: payload,
        );
      }

      setState(() {
        _status = widget.session.hidePrices
            ? 'Отправка на генерацию…'
            : 'Создание заказа…';
        _progress = 0.9;
      });

      final order = await widget.api.createOrder(
        taskUuid: taskUuid,
        category: draft.category,
        tier: draft.tier,
        companyId: widget.session.companyId,
        promocode: _promo.text.trim().isEmpty ? null : _promo.text.trim(),
        forbidden: draft.forbidden,
        birthDate: draft.birthDate,
        scaleCalibration: draft.scaleCalibration,
        photosPrefix: prepared['photos_prefix'] as String?,
        deviceModel: Platform.isIOS
            ? 'iOS'
            : (Platform.isAndroid ? 'Android' : Platform.operatingSystem),
        osVersion: Platform.operatingSystemVersion,
      );

      await ShootStorage.instance.clearActiveDraft();
      if (!mounted) return;
      final orderId = order['id'] as int;
      context.go('/home/queue/$orderId');
    } on DioException catch (e) {
      setState(() {
        _error = e.response?.data?.toString() ?? e.message ?? 'Ошибка сети';
        _running = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _running = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final hidePrices = widget.session.hidePrices;
    return FScaffold(
      header: FHeader.nested(
        title: const Text('Загрузка и заказ'),
        prefixes: [FHeaderAction.back(onPress: _running ? null : () => context.pop())],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (!hidePrices) ...[
              TextField(
                controller: _promo,
                enabled: !_running,
                decoration: const InputDecoration(
                  labelText: 'Промокод',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
            ],
            Text(_status),
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: _progress,
              color: AppColors.wbPrimary,
              backgroundColor: AppColors.surface,
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: const TextStyle(color: AppColors.error)),
            ],
            const Spacer(),
            FButton(
              onPress: _running ? null : _run,
              child: Text(
                hidePrices ? 'Отправить на генерацию' : 'Оплатить и загрузить',
              ),
            ),
          ],
        ),
      ),
    );
  }
}
