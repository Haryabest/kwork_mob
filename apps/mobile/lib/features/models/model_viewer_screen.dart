import 'dart:io';
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/l10n/catalog_l10n.dart';
import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/services/local_model_library.dart';
import 'package:kwork_mobile/services/export_prefs_service.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
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
    required this.session,
    this.companyId,
    this.onNotifications,
    this.unread = 0,
  });

  final ApiClient api;
  final AppSession session;
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
  final _search = TextEditingController();
  final _dateFrom = TextEditingController();
  final _dateTo = TextEditingController();
  String? _tierFilter;
  int _authorFilter = -1;
  List<Map<String, dynamic>> _members = [];
  int _total = 0;
  int _pageSize = 20;
  bool _loadingMore = false;
  Timer? _searchDebounce;
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
    if (s == 'import_validating') return Icons.hourglass_top;
    if (s == 'imported') return Icons.file_download_done;
    if (s == 'import_failed') return Icons.error_outline;
    if (s.contains('verified') || s.contains('published')) {
      return Icons.check_circle;
    }
    return Icons.radio_button_unchecked;
  }

  Color _publishColor(String? status) {
    final s = status?.toLowerCase() ?? '';
    if (s == 'import_validating') return AppColors.accentBright;
    if (s == 'imported') return AppColors.success;
    if (s == 'import_failed') return AppColors.error;
    if (s.contains('verified') || s.contains('published')) {
      return AppColors.success;
    }
    return AppColors.textSecondary;
  }

  String _publishLabel(String? status) {
    final l = AppLocalizations.of(context)!;
    final s = status?.toLowerCase() ?? '';
    switch (s) {
      case 'import_validating':
        return l.mvPublishValidating;
      case 'imported':
        return l.mvPublishImported;
      case 'import_failed':
        return l.mvPublishImportFailed;
      case 'not_published':
        return l.mvPublishNotPublished;
      default:
        if (s.contains('verified')) return l.mvPublishVerified;
        if (s.contains('published')) return l.mvPublishPublished;
        return status ?? '—';
    }
  }

  bool _isImportBadge(String? status) {
    final s = status?.toLowerCase() ?? '';
    return s == 'import_validating' || s == 'imported' || s == 'import_failed';
  }

  bool _isNsfwBlocked(Map<String, dynamic> m) =>
      m['order_status']?.toString() == 'blocked_nsfw';

  String _listStatusLabel(Map<String, dynamic> m) {
    if (_isNsfwBlocked(m)) return AppLocalizations.of(context)!.orderStatusBlockedNsfw;
    return _publishLabel(m['publish_status']?.toString());
  }

  IconData _listStatusIcon(Map<String, dynamic> m) {
    if (_isNsfwBlocked(m)) return Icons.block;
    return _publishIcon(m['publish_status']?.toString());
  }

  Color _listStatusColor(Map<String, dynamic> m) {
    if (_isNsfwBlocked(m)) return AppColors.error;
    return _publishColor(m['publish_status']?.toString());
  }

  bool _showListBadge(Map<String, dynamic> m) =>
      _isImportBadge(m['publish_status']?.toString()) || _isNsfwBlocked(m);

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
    final l = AppLocalizations.of(context)!;
    final ctrl = TextEditingController(text: m['display_name']?.toString() ?? '');
    final ok = await showFDialog<bool>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: Text(l.mvRenameTitle),
        body: FTextField(
          control: FTextFieldControl.managed(controller: ctrl),
          label: Text(l.mvNameLabel),
        ),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(l.cancel)),
          FButton(onPress: () => Navigator.pop(ctx, true), child: Text(l.save)),
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
              SnackBar(content: Text(AppLocalizations.of(context)!.mvLinkCopied)),
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
              SnackBar(content: Text(AppLocalizations.of(context)!.mvMovedToTrash)),
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
    return list;
  }

  String? get _publishFilterParam {
    if (_statusFilter == 'published' || _statusFilter == 'draft') return _statusFilter;
    return null;
  }

  Future<void> _resetAndLoad() => _load();

  Future<void> _load({bool append = false}) async {
    if (!append) {
      setState(() {
        _loading = true;
        _error = null;
      });
    } else {
      setState(() => _loadingMore = true);
    }
    try {
      final page = await widget.api.listModelsPage(
        companyId: widget.companyId,
        search: _search.text.trim().isEmpty ? null : _search.text.trim(),
        dateFrom: _dateFrom.text.trim().isEmpty ? null : _dateFrom.text.trim(),
        dateTo: _dateTo.text.trim().isEmpty ? null : _dateTo.text.trim(),
        tier: _tierFilter,
        authorId: _authorFilter >= 0 ? _authorFilter : null,
        category: _categoryFilter?.api,
        publishFilter: _publishFilterParam,
        sort: _sortNewest ? 'newest' : 'oldest',
        limit: _pageSize,
        offset: append ? _items.length : 0,
      );
      final items = (page['items'] as List).cast<Map<String, dynamic>>();
      _total = (page['total'] as num?)?.toInt() ?? items.length;
      if (!append) {
        _favorites = await LocalModelLibrary.instance.favorites();
        if (widget.companyId != null && widget.session.canFilterCompanyOrders) {
          try {
            final m = await widget.api.listCompanyMembers();
            final raw = m['items'] as List? ?? [];
            _members = raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
          } catch (_) {}
        }
        // ignore: unawaited_futures
        LocalModelLibrary.instance.syncPendingDownloads(
          widget.api,
          companyId: widget.companyId,
        );
      }
      if (append) {
        _items = [..._items, ...items];
      } else {
        _items = items;
      }
      for (final m in items) {
        final uuid = m['uuid']?.toString();
        if (uuid != null) _loadThumb(uuid);
      }
    } catch (e) {
      if (!append) _error = formatApiError(e);
    }
    if (mounted) {
      setState(() {
        _loading = false;
        _loadingMore = false;
      });
    }
  }

  @override
  void dispose() {
    _searchDebounce?.cancel();
    _search.dispose();
    _dateFrom.dispose();
    _dateTo.dispose();
    super.dispose();
  }

  Future<void> _pickDate(TextEditingController ctrl) async {
    final now = DateTime.now();
    final initial = DateTime.tryParse(ctrl.text.trim()) ?? now;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial.isAfter(now) ? now : initial,
      firstDate: DateTime(2020),
      lastDate: now,
    );
    if (picked == null) return;
    ctrl.text =
        '${picked.year.toString().padLeft(4, '0')}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}';
    _resetAndLoad();
  }

  String _memberLabel(int? userId) {
    if (userId == null) return '';
    for (final m in _members) {
      if (m['user_id'] == userId) {
        return m['full_name']?.toString() ?? m['email']?.toString() ?? '#$userId';
      }
    }
    return '#$userId';
  }

  @override
  void initState() {
    super.initState();
    _search.addListener(() {
      _searchDebounce?.cancel();
      _searchDebounce = Timer(const Duration(milliseconds: 400), _resetAndLoad);
    });
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context)!;
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(_error!, style: const TextStyle(color: AppColors.error)),
            FButton(onPress: _load, child: Text(l.mvRetry)),
          ],
        ),
      );
    }
    if (_items.isEmpty && _total == 0) {
      return RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(l.mvTitle, style: context.theme.typography.xl.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            Center(child: Text(l.mvNoModels)),
          ],
        ),
      );
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
                      l.mvTitle,
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
                    child: Text(l.mvTrash),
                  ),
                ],
              ),
            ),
          ),
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: Column(
                children: [
                  FTextField(
                    control: FTextFieldControl.managed(controller: _search),
                    label: Text(l.mvSearchHint),
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: GestureDetector(
                          onTap: () => _pickDate(_dateFrom),
                          child: AbsorbPointer(
                            child: FTextField(
                              control: FTextFieldControl.managed(controller: _dateFrom),
                              label: Text(l.dateFrom),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: GestureDetector(
                          onTap: () => _pickDate(_dateTo),
                          child: AbsorbPointer(
                            child: FTextField(
                              control: FTextFieldControl.managed(controller: _dateTo),
                              label: Text(l.dateTo),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  if (_dateFrom.text.isNotEmpty || _dateTo.text.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton(
                        onPressed: () {
                          _dateFrom.clear();
                          _dateTo.clear();
                          _resetAndLoad();
                        },
                        child: Text(l.mvClearDates),
                      ),
                    ),
                  ],
                  const SizedBox(height: 8),
                  FSelect<String>(
                    label: Text(l.mvFilterTierAll),
                    control: FSelectControl.managed(
                      initial: _tierFilter ?? 'all',
                      onChange: (v) {
                        setState(() => _tierFilter = v == null || v == 'all' ? null : v);
                        _resetAndLoad();
                      },
                    ),
                    items: {
                      l.mvFilterTierAll: 'all',
                      Tier.small.localized(l): Tier.small.api,
                      Tier.large.localized(l): Tier.large.api,
                    },
                  ),
                  if (widget.companyId != null &&
                      widget.session.canFilterCompanyOrders &&
                      _members.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    FSelect<int>(
                      label: Text(l.mvFilterAuthor),
                      control: FSelectControl.managed(
                        initial: _authorFilter,
                        onChange: (v) {
                          setState(() => _authorFilter = v ?? -1);
                          _resetAndLoad();
                        },
                      ),
                      items: {
                        l.mvFilterAuthorAll: -1,
                        for (final m in _members)
                          _memberLabel(m['user_id'] as int?): m['user_id'] as int,
                      },
                    ),
                  ],
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
                    label: Text(l.mvFilterAll),
                    selected: _statusFilter == 'all',
                    onSelected: (_) {
                      setState(() => _statusFilter = 'all');
                      _resetAndLoad();
                    },
                  ),
                  FilterChip(
                    label: Text(l.mvPublishPublished),
                    selected: _statusFilter == 'published',
                    onSelected: (_) {
                      setState(() => _statusFilter = 'published');
                      _resetAndLoad();
                    },
                  ),
                  FilterChip(
                    label: Text(l.mvPublishNotPublished),
                    selected: _statusFilter == 'draft',
                    onSelected: (_) {
                      setState(() => _statusFilter = 'draft');
                      _resetAndLoad();
                    },
                  ),
                  FilterChip(
                    label: Text(l.mvFilterFavorites),
                    selected: _favoritesOnly,
                    onSelected: (_) => setState(() => _favoritesOnly = !_favoritesOnly),
                  ),
                  FilterChip(
                    label: Text(_sortNewest ? l.mvSortNewest : l.mvSortOldest),
                    selected: true,
                    onSelected: (_) {
                      setState(() => _sortNewest = !_sortNewest);
                      _resetAndLoad();
                    },
                  ),
                  ...ProductCategory.values.map(
                    (c) => FilterChip(
                      label: Text(c.label),
                      selected: _categoryFilter == c,
                      onSelected: (v) {
                        setState(() => _categoryFilter = v ? c : null);
                        _resetAndLoad();
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (visible.isEmpty)
            SliverFillRemaining(
              child: Center(child: Text(l.mvNoModelsFilter)),
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
                                        _listStatusIcon(m),
                                        size: 14,
                                        color: _listStatusColor(m),
                                      ),
                                      const SizedBox(width: 4),
                                      if (_showListBadge(m))
                                        FBadge(
                                          child: Text(
                                            _listStatusLabel(m),
                                            style: const TextStyle(fontSize: 10),
                                          ),
                                        )
                                      else
                                        Expanded(
                                          child: Text(
                                            _listStatusLabel(m),
                                            style: TextStyle(
                                              fontSize: 11,
                                              color: _listStatusColor(m),
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
                              itemBuilder: (_) => [
                                PopupMenuItem(
                                  value: 'glb_ozon',
                                  child: Text(
                                    l.mvDownloadGlbOzon,
                                    style: const TextStyle(color: AppColors.ozonPrimary),
                                  ),
                                ),
                                PopupMenuItem(
                                  value: 'usdz_wb',
                                  child: Text(
                                    l.mvDownloadUsdzWb,
                                    style: const TextStyle(color: AppColors.accentPurple),
                                  ),
                                ),
                                PopupMenuItem(value: 'share', child: Text(l.mvShare)),
                                PopupMenuItem(value: 'rate', child: Text(l.mvRate)),
                                PopupMenuItem(
                                  value: 'pub_link',
                                  child: Text(l.mvVerifyLink),
                                ),
                                PopupMenuItem(value: 'regen', child: Text(l.mvEdit)),
                                PopupMenuItem(value: 'rename', child: Text(l.mvRename)),
                                PopupMenuItem(value: 'trash', child: Text(l.mvDelete)),
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
          if (_items.length < _total)
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                child: FButton(
                  onPress: _loadingMore ? null : () => _load(append: true),
                  child: Text(_loadingMore ? '…' : l.mvLoadMore),
                ),
              ),
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

  static const _reasons = ['blurry', 'holes', 'scale', 'color', 'other'];

  String _reasonLabel(String code) {
    final l = AppLocalizations.of(context)!;
    switch (code) {
      case 'blurry':
        return l.mvReasonBlurry;
      case 'holes':
        return l.mvReasonHoles;
      case 'scale':
        return l.mvReasonScale;
      case 'color':
        return l.mvReasonColor;
      default:
        return l.mvReasonOther;
    }
  }

  @override
  void initState() {
    super.initState();
    AnalyticsService.instance.track('screen_view', {'screen': 'model_viewer'});
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
            SnackBar(content: Text(AppLocalizations.of(context)!.mvLinkCopiedMarketplace(marketplace.toUpperCase()))),
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
          SnackBar(content: Text(AppLocalizations.of(context)!.mvGlbSaved(file.path))),
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
          title: Text(AppLocalizations.of(ctx)!.mvPublicLinkTitle),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              QrImageView(data: url, size: 200),
              const SizedBox(height: 8),
              SelectableText(url, style: const TextStyle(fontSize: 12)),
              if (res['expires_at'] != null)
                Text(AppLocalizations.of(ctx)!.mvUntil('${res['expires_at']}'), style: const TextStyle(fontSize: 11)),
            ],
          ),
          actions: [
            FButton(onPress: () => Navigator.pop(ctx), child: Text(AppLocalizations.of(ctx)!.faqClose)),
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
          title: Text(AppLocalizations.of(ctx)!.mvNoLocalPhotosTitle),
          content: Text(AppLocalizations.of(ctx)!.mvNoLocalPhotosBody),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(AppLocalizations.of(ctx)!.cancel)),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: Text(AppLocalizations.of(ctx)!.mvRestore)),
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
          SnackBar(content: Text(AppLocalizations.of(context)!.mvCantDetectCategory)),
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
          SnackBar(content: Text(res['message']?.toString() ?? AppLocalizations.of(context)!.mvStorageExtended)),
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
        title: Text(AppLocalizations.of(ctx)!.mvDeleteTitle),
        content: Text(AppLocalizations.of(ctx)!.mvDeleteBody),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(AppLocalizations.of(ctx)!.cancel)),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: AppColors.error),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(AppLocalizations.of(ctx)!.yes),
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
          SnackBar(content: Text(res['message']?.toString() ?? AppLocalizations.of(context)!.mvInTrash)),
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
          SnackBar(content: Text(res['message']?.toString() ?? AppLocalizations.of(context)!.mvSourcesRestored)),
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
        title: Text(AppLocalizations.of(ctx)!.mvCardLinkTitle),
        content: FTextField(
          control: FTextFieldControl.managed(controller: ctrl),
          hint: AppLocalizations.of(ctx)!.mvCardLinkHint,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(AppLocalizations.of(ctx)!.cancel)),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(AppLocalizations.of(ctx)!.mvAdd)),
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
          SnackBar(content: Text(AppLocalizations.of(context)!.mvLinkStatus('${res['status'] ?? 'ok'}'))),
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
              Text(AppLocalizations.of(ctx)!.mvRateTitle, style: Theme.of(ctx).textTheme.titleMedium),
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
                child: Text(AppLocalizations.of(ctx)!.mvWhatsWrong),
              ),
              ..._reasons.map(
                (r) => CheckboxListTile(
                  value: selected.contains(r),
                  title: Text(_reasonLabel(r)),
                  onChanged: (v) => setLocal(() {
                    if (v == true) {
                      selected.add(r);
                    } else {
                      selected.remove(r);
                    }
                  }),
                ),
              ),
              if (selected.contains('other'))
                FTextField(
                  control: FTextFieldControl.managed(controller: other),
                  label: Text(AppLocalizations.of(ctx)!.mvComment),
                ),
              const SizedBox(height: 8),
              FButton(
                onPress: () => Navigator.pop(ctx, true),
                child: Text(AppLocalizations.of(ctx)!.faqSend),
              ),
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: Text(AppLocalizations.of(ctx)!.mvLater),
              ),
            ],
          ),
        ),
      ),
    );
    if (ok == true) {
      final reasons = [
        ...selected.where((e) => e != 'other'),
        if (selected.contains('other') && other.text.trim().isNotEmpty) other.text.trim(),
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

    final l = AppLocalizations.of(context)!;
    return FScaffold(
      header: FHeader.nested(
        title: Text(l.mvModelTitle),
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
                ? Center(child: Text(l.mvGlbNotReady))
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
                  l.queueStatus(_publishStatus ?? '—'),
                  style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                ),
                if (_storage != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      l.mvCloud(
                        '${_storage!['days_left'] ?? '—'}',
                        '${_storage!['extends_remaining'] ?? '—'}',
                        '${_storage!['max_extends'] ?? 3}',
                      ),
                      style: const TextStyle(fontSize: 11, color: AppColors.textSecondary),
                    ),
                  ),
                if (_hasLocalGlb)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      l.mvLocalGlbSaved,
                      style: const TextStyle(fontSize: 11, color: AppColors.success),
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
                      child: Text(l.mvRegenerate),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : _sharePublic,
                      child: Text(l.mvShare),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : _downloadLocalGlb,
                      child: Text(_hasLocalGlb ? l.mvUpdateGlb : l.mvGlbLocal),
                    ),
                    FButton(
                      onPress: _busy ? null : () => _download('wb'),
                      child: Text(l.mvDownloadWb),
                    ),
                    FButton(
                      onPress: _busy ? null : () => _download('ozon'),
                      child: Text(l.mvDownloadOzon),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : _restoreSources,
                      child: Text(l.mvSources),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ||
                              ((_storage?['extends_remaining'] as num?)?.toInt() ?? 0) <= 0
                          ? null
                          : _extendStorage,
                      child: Text(l.mvExtend30),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : _moveToTrash,
                      child: Text(l.mvToTrash),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : _addLink,
                      child: Text(l.mvLink),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : () => _markPublished('wildberries'),
                      child: Text(l.mvImOnWb),
                    ),
                    FButton(
                      variant: .outline,
                      onPress: _busy ? null : () => _markPublished('ozon'),
                      child: Text(l.mvImOnOzon),
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
                                  title: Text(l.mvApiUploadTitle),
                                  content: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      FTextField(
                                        control: FTextFieldControl.managed(controller: ctrl),
                                        label: Text(l.mvApiSkuLabel),
                                      ),
                                    ],
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () => Navigator.pop(ctx, 'wb'),
                                      child: Text(l.mvImOnWb),
                                    ),
                                    TextButton(
                                      onPressed: () => Navigator.pop(ctx, 'ozon'),
                                      child: Text(l.mvImOnOzon),
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
                                    SnackBar(content: Text(AppLocalizations.of(context)!.mvApiResult('${res['publish_status'] ?? 'ok'}'))),
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
                      child: Text(l.mvApiUploadBtn),
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
