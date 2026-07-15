import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
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
        _error = formatApiError(e);
        _loading = false;
      });
    }
  }

  Future<ShootDraft?> _draftFromMeta() async {
    final meta = _meta;
    if (meta == null) return null;
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
    return draft;
  }

  Future<void> _startAr() async {
    final draft = await _draftFromMeta();
    if (draft == null || !mounted) return;
    context.push('/shoot/${widget.token}/dome', extra: draft.modelUuid);
  }

  Future<void> _pickGallery() async {
    final draft = await _draftFromMeta();
    if (draft == null || !mounted) return;
    final picker = ImagePicker();
    final images = await picker.pickMultiImage(limit: kGuidedDomeCount);
    if (images.length != kGuidedDomeCount) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            AppLocalizations.of(context)!.guestPhotosRequired(
              '$kGuidedDomeCount',
              '${images.length}',
            ),
          ),
        ),
      );
      return;
    }
    for (var i = 0; i < kGuidedDomeCount; i++) {
      final bytes = await images[i].readAsBytes();
      await ShootStorage.instance.savePhoto(draft.modelUuid, i, bytes);
    }
    if (!mounted) return;
    context.push('/shoot/${widget.token}/upload', extra: draft.modelUuid);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return FScaffold(
      header: FHeader.nested(
        title: Text(l10n.guestShootTitle),
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
                        l10n.guestTask(_meta?['task_uuid']?.toString().substring(0, 8) ?? ''),
                        style: context.theme.typography.lg,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        l10n.guestMeta(
                          _meta?['category']?.toString() ?? '—',
                          _meta?['tier']?.toString() ?? '—',
                        ),
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        l10n.guestHint,
                        style: const TextStyle(color: AppColors.textSecondary),
                      ),
                      const Spacer(),
                      FButton(
                        onPress: _startAr,
                        child: Text(l10n.guestStartAr),
                      ),
                      const SizedBox(height: 12),
                      FButton(
                        variant: .outline,
                        onPress: _pickGallery,
                        child: Text(l10n.guestGallery12),
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
  String _statusKey = 'ready';
  int _uploadIndex = 0;
  String? _error;
  bool _running = false;
  bool _done = false;

  Future<void> _run() async {
    if (_running) return;
    setState(() {
      _running = true;
      _error = null;
      _progress = 0;
      _statusKey = 'getting';
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
          _statusKey = 'uploading';
          _uploadIndex = i + 1;
          _progress = (i / 12);
        });
        await widget.api.uploadPhotoPresigned(
          uploadUrl: uploads[i]['upload_url'] as String,
          file: file,
          contentType: uploads[i]['content_type'] as String? ?? 'image/jpeg',
        );
      }
      setState(() {
        _statusKey = 'confirming';
        _progress = 0.95;
      });
      await widget.api.completeShootByToken(widget.token);
      await ShootStorage.instance.clearActiveDraft();
      if (!mounted) return;
      setState(() {
        _done = true;
        _running = false;
        _progress = 1;
        _statusKey = 'sent';
      });
    } catch (e) {
      setState(() {
        _error = formatApiError(e);
        _running = false;
      });
    }
  }

  String _guestStatus(AppLocalizations l10n, int uploadingIndex) {
    return switch (_statusKey) {
      'ready' => l10n.guestReadyToSend,
      'getting' => l10n.guestGettingUrls,
      'uploading' => l10n.guestUploading('$uploadingIndex'),
      'confirming' => l10n.guestConfirming,
      'sent' => l10n.guestSentToOwner,
      _ => l10n.guestReadyToSend,
    };
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final uploadIdx = _uploadIndex > 0 ? _uploadIndex : 1;
    return FScaffold(
      header: FHeader.nested(
        title: Text(l10n.guestUploadTitle),
        prefixes: [
          FHeaderAction.back(onPress: _running ? null : () => context.pop()),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(_guestStatus(l10n, uploadIdx)),
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
            if (_done) ...[
              const SizedBox(height: 16),
              Text(l10n.guestLinkUsed),
            ],
            const Spacer(),
            if (!_done)
              FButton(
                onPress: _running ? null : _run,
                child: Text(l10n.guestSend12Photos),
              ),
          ],
        ),
      ),
    );
  }
}
