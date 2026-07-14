import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

/// Список моделей + 3D viewer + оценка + публикация WB/Ozon (§3.9 / §7 / §19).
class ModelsScreen extends StatefulWidget {
  const ModelsScreen({super.key, required this.api});

  final ApiClient api;

  @override
  State<ModelsScreen> createState() => _ModelsScreenState();
}

class _ModelsScreenState extends State<ModelsScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;

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
      _items = await widget.api.listModels();
    } catch (e) {
      _error = e.toString();
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
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView.separated(
        padding: const EdgeInsets.all(16),
        itemCount: _items.length,
        separatorBuilder: (_, __) => const SizedBox(height: 8),
        itemBuilder: (context, i) {
          final m = _items[i];
          return ListTile(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            tileColor: AppColors.surface,
            title: Text(m['uuid']?.toString().substring(0, 8) ?? '—'),
            subtitle: Text(m['publish_status']?.toString() ?? ''),
            trailing: const Icon(Icons.view_in_ar),
            onTap: () => context.push('/home/models/${m['uuid']}', extra: m),
          );
        },
      ),
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
  bool _rated = false;
  bool _busy = false;

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
    final storage = widget.model?['storage'];
    if (storage is Map) {
      _storage = Map<String, dynamic>.from(storage);
    }
    _boot();
  }

  Future<void> _boot() async {
    final prefs = await SharedPreferences.getInstance();
    _rated = prefs.getBool('rated_${widget.modelUuid}') ?? false;
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
        _publishStatus = match.first['publish_status']?.toString();
        try {
          final dl = await widget.api.downloadModel(modelUuid: widget.modelUuid);
          _glbUrl = dl['download_url']?.toString() ?? _glbUrl;
        } catch (_) {
          _glbUrl = match.first['glb_url']?.toString();
        }
      }
    }
    if (mounted) setState(() {});
    if (!_rated && mounted) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _askRating());
    }
  }

  Future<void> _download(String marketplace) async {
    setState(() => _busy = true);
    try {
      final res = await widget.api.downloadModel(
        modelUuid: widget.modelUuid,
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
        context.pop();
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
        content: TextField(
          controller: ctrl,
          decoration: const InputDecoration(
            hintText: 'https://www.wildberries.ru/... или ozon.ru/...',
          ),
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
                TextField(
                  controller: other,
                  decoration: const InputDecoration(labelText: 'Комментарий'),
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
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
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
                                      TextField(
                                        controller: ctrl,
                                        decoration: const InputDecoration(labelText: 'SKU'),
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
