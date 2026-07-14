import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';

/// Гостевой вход по shoot-link (§3.15) — deep link `/shoot/{token}`.
class GuestShootGateScreen extends StatefulWidget {
  const GuestShootGateScreen({
    super.key,
    required this.api,
    required this.token,
  });

  final ApiClient api;
  final String token;

  @override
  State<GuestShootGateScreen> createState() => _GuestShootGateScreenState();
}

class _GuestShootGateScreenState extends State<GuestShootGateScreen> {
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _meta;

  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    try {
      final meta = await widget.api.getShootByToken(widget.token);
      if (!mounted) return;
      setState(() {
        _meta = meta;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _startAr() async {
    final meta = _meta;
    if (meta == null) return;
    final taskUuid = meta['task_uuid'] as String;
    final category = ProductCategory.values.firstWhere(
      (e) => e.api == meta['category'],
      orElse: () => ProductCategory.other,
    );
    final tier = Tier.values.firstWhere(
      (e) => e.api == meta['tier'],
      orElse: () => Tier.small,
    );
    final draft = ShootDraft(
      modelUuid: taskUuid,
      category: category,
      tier: tier,
      createdAt: DateTime.now(),
    );
    await ShootStorage.instance.writeMetadata(draft);
    if (!mounted) return;
    context.push('/shoot/${widget.token}/dome', extra: taskUuid);
  }

  @override
  Widget build(BuildContext context) {
    return FScaffold(
      header: FHeader.nested(
        title: const Text('Съёмка по ссылке'),
        prefixes: [
          FHeaderAction.back(
            onPress: () {
              if (context.canPop()) {
                context.pop();
              } else {
                context.go('/splash');
              }
            },
          ),
        ],
      ),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Padding(
                  padding: const EdgeInsets.all(20),
                  child: Text(_error!, style: const TextStyle(color: AppColors.error)),
                )
              : Padding(
                  padding: const EdgeInsets.all(20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'Задача ${_meta?['task_uuid']?.toString().substring(0, 8) ?? ''}…',
                        style: context.theme.typography.lg,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Категория: ${_meta?['category'] ?? '—'} · тариф: ${_meta?['tier'] ?? '—'}',
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Гостевой режим: только съёмка 12 ракурсов, без доступа к кабинету (§3.15).',
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                      const Spacer(),
                      FButton(
                        onPress: _startAr,
                        child: const Text('Начать AR-съёмку'),
                      ),
                    ],
                  ),
                ),
    );
  }
}

/// Загрузка 12 фото по shoot-link + complete (§3.15).
class GuestShootUploadScreen extends StatefulWidget {
  const GuestShootUploadScreen({
    super.key,
    required this.api,
    required this.token,
    required this.modelUuid,
  });

  final ApiClient api;
  final String token;
  final String modelUuid;

  @override
  State<GuestShootUploadScreen> createState() => _GuestShootUploadScreenState();
}

class _GuestShootUploadScreenState extends State<GuestShootUploadScreen> {
  double _progress = 0;
  String _status = 'Готово к отправке';
  String? _error;
  bool _running = false;
  bool _done = false;

  Future<void> _run() async {
    if (_running) return;
    setState(() {
      _running = true;
      _error = null;
      _progress = 0;
      _status = 'Получение upload URL…';
    });
    try {
      final meta = await widget.api.getShootByToken(widget.token);
      final uploads = (meta['uploads'] as List)
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList();
      final photos = await ShootStorage.instance.listPhotos(widget.modelUuid);
      for (var i = 0; i < uploads.length; i++) {
        final file = photos[i];
        if (file == null) throw StateError('Нет файла ракурса $i');
        setState(() {
          _status = 'Загрузка ${i + 1}/12…';
          _progress = (i / 12);
        });
        await widget.api.uploadPhotoPresigned(
          uploadUrl: uploads[i]['upload_url'] as String,
          file: file,
          contentType: uploads[i]['content_type'] as String? ?? 'image/jpeg',
        );
      }
      setState(() {
        _status = 'Подтверждение…';
        _progress = 0.95;
      });
      await widget.api.completeShootByToken(widget.token);
      await ShootStorage.instance.clearActiveDraft();
      if (!mounted) return;
      setState(() {
        _done = true;
        _running = false;
        _progress = 1;
        _status = 'Фото отправлены владельцу';
      });
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
    return FScaffold(
      header: FHeader.nested(
        title: const Text('Отправка по ссылке'),
        prefixes: [
          FHeaderAction.back(onPress: _running ? null : () => context.pop()),
        ],
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
              color: AppColors.wbPrimary,
              backgroundColor: AppColors.surface,
            ),
            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(_error!, style: const TextStyle(color: AppColors.error)),
            ],
            if (_done) ...[
              const SizedBox(height: 16),
              const Text(
                'Ссылка использована. Владелец компании получит уведомление.',
              ),
            ],
            const Spacer(),
            if (!_done)
              FButton(
                onPress: _running ? null : _run,
                child: const Text('Отправить 12 фото'),
              ),
          ],
        ),
      ),
    );
  }
}
