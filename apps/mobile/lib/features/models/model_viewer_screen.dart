import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/services/local_model_library.dart';
import 'package:kwork_mobile/services/export_prefs_service.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

/// Список моделей + 3D viewer + оценка + публикация WB/Ozon (§3.9 / §7 / §19).
class ModelsScreen extends StatefulWidget {
  const ModelsScreen({
    super.key,
    required this.api,
    this.companyId,
    this.onNotifications,
    this.unread = 0,
  });

  final ApiClient api;
  final int? companyId;
  final VoidCallback? onNotifications;
  final int unread;

  @override
  State<ModelsScreen> createState() => _ModelsScreenState();
}

class _ModelsScreenState extends State<ModelsScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;
  String _statusFilter = 'all';
  ProductCategory? _categoryFilter;
  bool _sortNewest = true;
  bool _favoritesOnly = false;
  Set<String> _favorites = {};
  final Map<String, String?> _thumbnails = {};
  final Map<String, File?> _localThumbs = {};
  String? _menuBusyUuid;

  String _modelTitle(Map<String, dynamic> m) {
    final name = m['display_name']?.toString();
    if (name != null && name.isNotEmpty) return name;
    final u = m['uuid']?.toString() ?? '—';
    return u.length > 8 ? u.substring(0, 8) : u;
  }

  String _formatDate(String? iso) {
    final d = DateTime.tryParse(iso ?? '');
    if (d == null) return '—';
    return '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}.${d.year}';
  }

  IconData _publishIcon(String? status) {
    final s = status?.toLowerCase() ?? '';
    if (s.contains('verified') || s.contains('published')) {
      return Icons.check_circle;
    }
    return Icons.radio_button_unchecked;
  }

  Color _publishColor(String? status) {
    final s = status?.toLowerCase() ?? '';
    if (s.contains('verified') || s.contains('published')) {
      return AppColors.success;
    }
    return AppColors.textSecondary;
  }

  Future<void> _loadThumb(String uuid) async {
    final local = await ShootStorage.instance.photoFile(uuid, 0);
    if (await local.exists()) {
      if (mounted) {
        setState(() {
          _localThumbs[uuid] = local;
        });
      }
      return;
    }
    try {
      final url = await widget.api.modelThumbnailUrl(uuid);
      if (url != null && mounted) {
        setState(() => _thumbnails[uuid] = url);
      }
    } catch (_) {}
  }

  Future<void> _renameModel(Map<String, dynamic> m) async {
    final uuid = m['uuid']?.toString();
    if (uuid == null) return;
    final ctrl = TextEditingController(text: m['display_name']?.toString() ?? '');
    final ok = await showFDialog<bool>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: const Text('Переименовать модель'),
        body: FTextField(
          control: FTextFieldControl.managed(controller: ctrl),
          label: const Text('Название'),
        ),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
          FButton(onPress: () => Navigator.pop(ctx, true), child: const Text('Сохранить')),
        ],
      ),
    );
    if (ok != true || ctrl.text.trim().isEmpty) {
      ctrl.dispose();
      return;
    }
    try {
      await widget.api.renameModel(modelUuid: uuid, displayName: ctrl.text.trim());
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
    ctrl.dispose();
  }

  Future<void> _onMenu(String action, Map<String, dynamic> m) async {
    final uuid = m['uuid']?.toString();
    if (uuid == null) return;
    setState(() => _menuBusyUuid = uuid);
    try {
      switch (action) {
        case 'glb_ozon':
          final r = await widget.api.downloadModel(modelUuid: uuid, format: 'glb', marketplace: 'ozon');
          final url = r['download_url']?.toString();
          if (url != null) await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
        case 'usdz_wb':
          final r = await widget.api.downloadModel(modelUuid: uuid, format: 'usdz', marketplace: 'wb');
          final url = r['download_url']?.toString();
          if (url != null) await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
        case 'share':
          final r = await widget.api.createShareLink(modelUuid: uuid);
          final link = r['public_url']?.toString() ?? r['url']?.toString();
          if (link != null && mounted) {
            await Clipboard.setData(ClipboardData(text: link));
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Ссылка скопирована')),
            );
          }
        case 'rate':
          if (mounted) context.push('/home/models/$uuid', extra: m);
        case 'pub_link':
          if (mounted) context.push('/home/models/$uuid', extra: m);
        case 'regen':
          if (mounted) context.push('/home/models/$uuid', extra: m);
        case 'rename':
          await _renameModel(m);
        case 'trash':
          await widget.api.trashModel(modelUuid: uuid);
          await _load();
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Модель перемещена в корзину')),
            );
          }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _menuBusyUuid = null);
    }
  }

  List<Map<String, dynamic>> get _filtered {
    var list = [..._items];
    if (_favoritesOnly) {
      list = list.where((m) => _favorites.contains(m['uuid']?.toString())).toList();
    }
    if (_statusFilter == 'published') {
      list = list.where((m) {
        final s = m['publish_status']?.toString() ?? '';
        return s.contains('published') || s.contains('verified');
      }).toList();
    } else if (_statusFilter == 'draft') {
      list = list.where((m) {
        final s = m['publish_status']?.toString() ?? '';
        return s.isEmpty || s == 'none' || s == 'not_published';
      }).toList();
    }
    if (_categoryFilter != null) {
      final api = _categoryFilter!.api;
      list = list.where((m) => m['category']?.toString() == api).toList();
    }
    list.sort((a, b) {
      final da = a['created_at']?.toString() ?? '';
      final db = b['created_at']?.toString() ?? '';
      return _sortNewest ? db.compareTo(da) : da.compareTo(db);
    });
    return list;
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      _items = await widget.api.listModels(companyId: widget.companyId);
      _favorites = await LocalModelLibrary.instance.favorites();
      // §3.5.3 — фоновая синхронизация GLB для completed заказов
      // ignore: unawaited_futures
      LocalModelLibrary.instance.syncPendingDownloads(
        widget.api,
        companyId: widget.companyId,
      );
      for (final m in _items) {
        final uuid = m['uuid']?.toString();
        if (uuid != null) _loadThumb(uuid);
      }
    } catch (e) {
      _error = formatApiError(e);
    }
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!, style: const TextStyle(color: AppColors.error)),
            FButton(onPress: _load, child: const Text('Повторить')),
          ],
        ),
      );
    }
    if (_items.isEmpty) {
      return const Center(child: Text('Пока нет моделей'));
    }
    final visible = _filtered;
    return RefreshIndicator(
      onRefresh: _load,
      child: CustomScrollView(
        slivers: [
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 48, 16, 8),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      'Модели',
                      style: context.theme.typography.xl.copyWith(fontWeight: FontWeight.bold),
                    ),
                  ),
                  if (widget.onNotifications != null)
                    IconButton(
                      onPressed: widget.onNotifications,
                      icon: Badge(
                        isLabelVisible: widget.unread > 0,
                        label: Text('${widget.unread}'),
                        child: const Icon(FIcons.bell),
                      ),
                    ),
                  FButton(
                    variant: .outline,
                    onPress: () => context.push('/home/models/trash'),
                    child: const Text('Корзина'),
                  ),
                ],
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  FilterChip(
                    label: const Text('Все'),
                    selected: _statusFilter == 'all',
                    onSelected: (_) => setState(() => _statusFilter = 'all'),
                  ),
                  FilterChip(
                    label: const Text('Опубликовано'),
                    selected: _statusFilter == 'published',
                    onSelected: (_) => setState(() => _statusFilter = 'published'),
                  ),
                  FilterChip(
                    label: const Text('Не опубликовано'),
                    selected: _statusFilter == 'draft',
                    onSelected: (_) => setState(() => _statusFilter = 'draft'),
                  ),
                  FilterChip(
                    label: const Text('Избранное'),
                    selected: _favoritesOnly,
                    onSelected: (_) => setState(() => _favoritesOnly = !_favoritesOnly),
                  ),
                  FilterChip(
                    label: Text(_sortNewest ? 'Сначала новые' : 'Сначала старые'),
                    selected: true,
                    onSelected: (_) => setState(() => _sortNewest = !_sortNewest),
                  ),
                  ...ProductCategory.values.map(
                    (c) => FilterChip(
                      label: Text(c.label),
                      selected: _categoryFilter == c,
                      onSelected: (v) => setState(() => _categoryFilter = v ? c : null),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (visible.isEmpty)
            const SliverFillRemaining(
              child: Center(child: Text('Нет моделей по фильтру')),
            )
          else
            SliverList.separated(
              itemCount: visible.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (context, i) {
                final m = visible[i];
                final uuid = m['uuid']?.toString() ?? '';
                final busy = _menuBusyUuid == uuid;
                final localThumb = _localThumbs[uuid];
                final netThumb = _thumbnails[uuid];
                return Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Material(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(12),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(12),
                      onTap: () => context.push('/home/models/$uuid', extra: m),
                      child: Padding(
                        padding: const EdgeInsets.all(12),
                        child: Row(
                          children: [
                            ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: SizedBox(
                                width: 64,
                                height: 64,
                                child: localThumb != null
                                    ? Image.file(localThumb, fit: BoxFit.cover)
                                    : netThumb != null
                                        ? Image.network(
                                            netThumb,
                                            fit: BoxFit.cover,
                                            errorBuilder: (_, __, ___) => _thumbPlaceholder(m),
                                          )
                                        : _thumbPlaceholder(m),
                              ),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _modelTitle(m),
                                    style: const TextStyle(fontWeight: FontWeight.w600),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    _formatDate(m['created_at']?.toString()),
                                    style: const TextStyle(
                                      fontSize: 12,
                                      color: AppColors.textSecondary,
                                    ),
                                  ),
                                  Row(
                                    children: [
                                      Icon(
                                        _publishIcon(m['publish_status']?.toString()),
                                        size: 14,
                                        color: _publishColor(m['publish_status']?.toString()),
                                      ),
                                      const SizedBox(width: 4),
                                      Expanded(
                                        child: Text(
                                          m['publish_status']?.toString() ?? '—',
                                          style: TextStyle(
                                            fontSize: 11,
                                            color: _publishColor(m['publish_status']?.toString()),
                                          ),
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            PopupMenuButton<String>(
                              enabled: !busy,
                              onSelected: (v) => _onMenu(v, m),
                              itemBuilder: (_) => const [
                                PopupMenuItem(
                                  value: 'glb_ozon',
                                  child: Text(
                                    'Скачать .glb (Ozon)',
                                    style: TextStyle(color: AppColors.ozonPrimary),
                                  ),
                                ),
                                PopupMenuItem(
                                  value: 'usdz_wb',
                                  child: Text(
                                    'Скачать .usdz (Wildberries)',
                                    style: TextStyle(color: AppColors.accentPurple),
                                  ),
                                ),
                                PopupMenuItem(value: 'share', child: Text('Поделиться')),
                                PopupMenuItem(value: 'rate', child: Text('Оценить модель')),
                                PopupMenuItem(
                                  value: 'pub_link',
                                  child: Text('Ссылка для верификации'),
                                ),
                                PopupMenuItem(value: 'regen', child: Text('Редактировать')),
                                PopupMenuItem(value: 'rename', child: Text('Переименовать')),
                                PopupMenuItem(value: 'trash', child: Text('Удалить')),
                              ],
                              icon: busy
                                  ? const SizedBox(
                                      width: 24,
                                      height: 24,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : const Icon(Icons.more_vert),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }

  Widget _thumbPlaceholder(Map<String, dynamic> m) {
    return Container(
      color: AppColors.surface,
      child: Icon(Icons.view_in_ar, color: AppColors.accent.withValues(alpha: 0.6)),
    );
  }
}

class ModelViewerScreen extends StatefulWidget {
  const ModelViewerScreen({
    super.key,
    required this.api,
    required this.modelUuid,
    this.model,
  });

  final ApiClient api;
  final String modelUuid;
  final Map<String, dynamic>? model;

  @override
  State<ModelViewerScreen> createState() => _ModelViewerScreenState();
}

class _ModelViewerScreenState extends State<ModelViewerScreen> {
  String? _glbUrl;
  String? _publishStatus;
  Map<String, dynamic>? _storage;
  Map<String, dynamic>? _modelMeta;
  bool _rated = false;
  bool _busy = false;
  bool _favorite = false;
  bool _hasLocalGlb = false;

  static const _reasons = [
    'размытые текстуры',
    'дыры или артефакты',
    'неправильный масштаб',
    'не тот цвет / освещение',
    'другое',
  ];

  @override
  void initState() {
    super.initState();
    _glbUrl = widget.model?['glb_url']?.toString();
    _publishStatus = widget.model?['publish_status']?.toString();
    _modelMeta = widget.model == null ? null : Map<String, dynamic>.from(widget.model!);
    final storage = widget.model?['storage'];
    if (storage is Map) {
      _storage = Map<String, dynamic>.from(storage);
    }
    _boot();
  }

  Future<void> _boot() async {
    final prefs = await SharedPreferences.getInstance();
    _rated = prefs.getBool('rated_${widget.modelUuid}') ?? false;
    _favorite = await LocalModelLibrary.instance.isFavorite(widget.modelUuid);
    _hasLocalGlb = await LocalModelLibrary.instance.hasLocalGlb(widget.modelUuid);
    await LocalModelLibrary.instance.touchAccess(widget.modelUuid);
    try {
      final detail = await widget.api.getModel(widget.modelUuid);
      _publishStatus = detail['publish_status']?.toString() ?? _publishStatus;
      final storage = detail['storage'];
      if (storage is Map) {
        _storage = Map<String, dynamic>.from(storage);
      }
    } catch (_) {}
    try {
      final preview = await widget.api.previewUrl(widget.modelUuid);
      if (preview != null && preview.isNotEmpty) {
        _glbUrl = preview;
      }
    } catch (_) {}
    if (_glbUrl == null || _glbUrl!.startsWith('s3://')) {
      final items = await widget.api.listModels();
      final match = items.where((e) => e['uuid'] == widget.modelUuid);
      if (match.isNotEmpty) {
        _modelMeta = Map<String, dynamic>.from(match.first);
        _publishStatus = match.first['publish_status']?.toString();
        try {
          final dl = await widget.api.downloadModel(modelUuid: widget.modelUuid);
          _glbUrl = dl['download_url']?.toString() ?? _glbUrl;
        } catch (_) {
          _glbUrl = match.first['glb_url']?.toString();
        }
      }
    }
    if (_hasLocalGlb) {
      final local = await LocalModelLibrary.instance.glbFile(widget.modelUuid);
      _glbUrl = local.uri.toString();
    }
    if (mounted) setState(() {});
    if (!_rated && mounted) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _askRating());
    }
  }

  Future<void> _download(String marketplace) async {
    setState(() => _busy = true);
    try {
      final fmt = ExportPrefsService.instance.apiFormat;
      final res = await widget.api.downloadModel(
        modelUuid: widget.modelUuid,
        format: fmt,
        marketplace: marketplace,
      );
      final url = res['download_url']?.toString();
      if (url != null) {
        await Clipboard.setData(ClipboardData(text: url));
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Ссылка ${marketplace.toUpperCase()} скопирована')),
          );
        }
        final uri = Uri.tryParse(url);
        if (uri != null) {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _downloadLocalGlb() async {
    setState(() => _busy = true);
    try {
      final file = await LocalModelLibrary.instance.downloadGlb(
        api: widget.api,
        modelUuid: widget.modelUuid,
      );
      if (file != null && mounted) {
        setState(() {
          _hasLocalGlb = true;
          _glbUrl = file.uri.toString();
        });
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('GLB сохранён: ${file.path}')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _sharePublic() async {
    setState(() => _busy = true);
    try {
      final res = await widget.api.createShareLink(modelUuid: widget.modelUuid);
      final url = res['url']?.toString();
      if (url == null || !mounted) return;
      await Clipboard.setData(ClipboardData(text: url));
      await showDialog<void>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Публичная ссылка §3.12'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              QrImageView(data: url, size: 200),
              const SizedBox(height: 8),
              SelectableText(url, style: const TextStyle(fontSize: 12)),
              if (res['expires_at'] != null)
                Text('До: ${res['expires_at']}', style: const TextStyle(fontSize: 11)),
            ],
          ),
          actions: [
            FButton(onPress: () => Navigator.pop(ctx), child: const Text('Закрыть')),
          ],
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _toggleFavorite() async {
    final next = !_favorite;
    await LocalModelLibrary.instance.setFavorite(widget.modelUuid, next);
    setState(() => _favorite = next);
  }

  Future<void> _regenerate() async {
    final count = await ShootStorage.instance.capturedCount(widget.modelUuid);
    if (count < 12) {
      if (!mounted) return;
      final restore = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Нет локальных фото'),
          content: const Text(
            'Для перегенерации нужны 12 исходников на устройстве. '
            'Восстановить из облака или снять заново?',
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Восстановить')),
          ],
        ),
      );
      if (restore == true) {
        await _restoreSources();
      }
      return;
    }
    final meta = _modelMeta ?? widget.model;
    final categoryApi = meta?['category']?.toString();
    final tierApi = meta?['tier']?.toString();
    if (categoryApi == null || tierApi == null) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Не удалось определить категорию/тариф')),
        );
      }
      return;
    }
    final category = ProductCategory.values.firstWhere(
      (e) => e.api == categoryApi,
      orElse: () => ProductCategory.other,
    );
    final tier = Tier.values.firstWhere(
      (e) => e.api == tierApi,
      orElse: () => Tier.small,
    );
    setState(() => _busy = true);
    try {
      final newUuid = await ShootStorage.instance.cloneForRegeneration(
        sourceModelUuid: widget.modelUuid,
        category: category,
        tier: tier,
      );
      if (!mounted) return;
      context.push('/home/shoot/upload', extra: newUuid);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _extendStorage() async {
    setState(() => _busy = true);
    try {
      final res = await widget.api.extendStorage(modelUuid: widget.modelUuid);
      final storage = res['storage'];
      if (storage is Map) {
        _storage = Map<String, dynamic>.from(storage);
      } else {
        _storage = Map<String, dynamic>.from(res);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(res['message']?.toString() ?? 'Хранение продлено')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _moveToTrash() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Удалить модель?'),
        content: const Text(
          'Исходные фото и модель будут перемещены в корзину на 30 дней. Продолжить?',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: AppColors.error),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Да'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final res = await widget.api.trashModel(modelUuid: widget.modelUuid);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(res['message']?.toString() ?? 'В корзине')),
        );
        context.go('/home/models/trash');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _restoreSources() async {
    setState(() => _busy = true);
    try {
      final res = await widget.api.restoreSources(modelUuid: widget.modelUuid);
      final url = res['download_url']?.toString();
      if (url != null) {
        await Clipboard.setData(ClipboardData(text: url));
        final uri = Uri.tryParse(url);
        if (uri != null) {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
        }
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(res['message']?.toString() ?? 'Исходники восстановлены')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _markPublished(String marketplace) async {
    setState(() => _busy = true);
    try {
      final res = await widget.api.markPublished(
        modelUuid: widget.modelUuid,
        marketplace: marketplace,
      );
      setState(() => _publishStatus = res['publish_status']?.toString());
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addLink() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Ссылка на карточку'),
        content: FTextField(
          control: FTextFieldControl.managed(controller: ctrl),
          hint: 'https://www.wildberries.ru/... или ozon.ru/...',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Добавить')),
        ],
      ),
    );
    if (ok != true || ctrl.text.trim().length < 12) {
      ctrl.dispose();
      return;
    }
    setState(() => _busy = true);
    try {
      final res = await widget.api.addPublicationLink(
        modelUuid: widget.modelUuid,
        url: ctrl.text.trim(),
      );
      setState(() {
        _publishStatus = res['status']?.toString() ?? _publishStatus;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ссылка: ${res['status'] ?? 'ok'}')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: AppColors.error),
        );
      }
    } finally {
      ctrl.dispose();
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _askRating() async {
    int rating = 5;
    final selected = <String>{};
    final other = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setLocal) => Padding(
          padding: EdgeInsets.only(
            left: 20,
            right: 20,
            top: 20,
            bottom: MediaQuery.viewInsetsOf(ctx).bottom + 20,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('Оцените качество модели от 1 до 5', style: Theme.of(ctx).textTheme.titleMedium),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: List.generate(5, (i) {
                  final v = i + 1;
                  return IconButton(
                    onPressed: () => setLocal(() => rating = v),
                    icon: Icon(
                      v <= rating ? Icons.star : Icons.star_border,
                      color: AppColors.warning,
                      size: 32,
                    ),
                  );
                }),
              ),
              TextButton(
                onPressed: () => setLocal(() {}),
                child: const Text('Что не так?'),
              ),
              ..._reasons.map(
                (r) => CheckboxListTile(
                  value: selected.contains(r),
                  title: Text(r),
                  onChanged: (v) => setLocal(() {
                    if (v == true) {
                      selected.add(r);
                    } else {
                      selected.remove(r);
                    }
                  }),
                ),
              ),
              if (selected.contains('другое'))
                FTextField(
                  control: FTextFieldControl.managed(controller: other),
                  label: const Text('Комментарий'),
                ),
              const SizedBox(height: 8),
              FButton(
                onPress: () => Navigator.pop(ctx, true),
                child: const Text('Отправить'),
              ),
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Позже'),
              ),
            ],
          ),
        ),
      ),
    );
    if (ok == true) {
      final reasons = [
        ...selected.where((e) => e != 'другое'),
        if (selected.contains('другое') && other.text.trim().isNotEmpty) other.text.trim(),
      ];
      await widget.api.rateModel(
        modelUuid: widget.modelUuid,
        rating: rating,
        reasons: reasons,
      );
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool('rated_${widget.modelUuid}', true);
      setState(() => _rated = true);
    }
    other.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final canPreview = _glbUrl != null &&
        _glbUrl!.isNotEmpty &&
        !_glbUrl!.startsWith('s3://');

    return FScaffold(
      header: FHeader.nested(
        title: const Text('3D-модель'),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
        suffixes: [
          FHeaderAction(
            icon: Icon(_favorite ? Icons.star : Icons.star_border),
            onPress: _busy ? null : _toggleFavorite,
          ),
          if (_rated)
            FHeaderAction(
              icon: const Icon(Icons.star_outline),
              onPress: _askRating,
            ),
        ],
      ),
      child: Column(
        children: [
          Expanded(
            child: !canPreview
                ? const Center(child: Text('GLB ещё не готов'))
                : ModelViewer(
                    src: _glbUrl!,
                    alt: '3D model',
                    ar: true,
                    autoRotate: true,
                    cameraControls: true,
                    backgroundColor: AppColors.surface,
                  ),
          ),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            color: AppColors.surface,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Статус: ${_publishStatus ?? '—'}',
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
                if (_storage != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      'Облако: ${_storage!['days_left'] ?? '—'} дн. · продлений '
                      '${_storage!['extends_remaining'] ?? '—'}/${_storage!['max_extends'] ?? 3}',
                      style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                    ),
                  ),
                if (_hasLocalGlb)
                  const Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Text(
                      'Локальный GLB сохранён',
                      style: TextStyle(fontSize: 11, color: AppColors.success),
                    ),
                  ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : _regenerate,
                      child: const Text('Перегенерировать'),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : _sharePublic,
                      child: const Text('Share'),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : _downloadLocalGlb,
                      child: Text(_hasLocalGlb ? 'Обновить GLB' : 'GLB локально'),
                    ),
                    FButton(
                      onPress: _busy ? null : () => _download('wb'),
                      child: const Text('Скачать WB'),
                    ),
                    FButton(
                      onPress: _busy ? null : () => _download('ozon'),
                      child: const Text('Скачать Ozon'),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : _restoreSources,
                      child: const Text('Исходники'),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ||
                              ((_storage?['extends_remaining'] as num?)?.toInt() ?? 0) <= 0
                          ? null
                          : _extendStorage,
                      child: const Text('+30 дн.'),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : _moveToTrash,
                      child: const Text('В корзину'),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : _addLink,
                      child: const Text('Ссылка'),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : () => _markPublished('wildberries'),
                      child: const Text('Я на WB'),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : () => _markPublished('ozon'),
                      child: const Text('Я на Ozon'),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy
                          ? null
                          : () async {
                              final ctrl = TextEditingController();
                              final mp = await showDialog<String>(
                                context: context,
                                builder: (ctx) => AlertDialog(
                                  title: const Text('API upload'),
                                  content: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      FTextField(
                                        control: FTextFieldControl.managed(controller: ctrl),
                                        label: const Text('SKU'),
                                      ),
                                    ],
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () => Navigator.pop(ctx, 'wb'),
                                      child: const Text('WB'),
                                    ),
                                    TextButton(
                                      onPressed: () => Navigator.pop(ctx, 'ozon'),
                                      child: const Text('Ozon'),
                                    ),
                                  ],
                                ),
                              );
                              final sku = ctrl.text.trim();
                              ctrl.dispose();
                              if (mp == null || sku.isEmpty) return;
                              setState(() => _busy = true);
                              try {
                                final res = await widget.api.marketplaceUpload(
                                  modelUuid: widget.modelUuid,
                                  marketplace: mp,
                                  sku: sku,
                                );
                                if (mounted) {
                                  setState(() {
                                    _publishStatus = res['publish_status']?.toString();
                                    _busy = false;
                                  });
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(content: Text('API: ${res['publish_status'] ?? 'ok'}')),
                                  );
                                }
                              } catch (e) {
                                if (mounted) {
                                  setState(() => _busy = false);
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    SnackBar(
                                      content: Text('$e'),
                                      backgroundColor: AppColors.error,
                                    ),
                                  );
                                }
                              }
                            },
                      child: const Text('API upload'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
