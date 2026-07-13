import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:model_viewer_plus/model_viewer_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Список моделей + 3D viewer + оценка 1–5 (§3.9.3).
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
  bool _rated = false;

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
    _boot();
  }

  Future<void> _boot() async {
    final prefs = await SharedPreferences.getInstance();
    _rated = prefs.getBool('rated_${widget.modelUuid}') ?? false;
    if (_glbUrl == null) {
      final items = await widget.api.listModels();
      final match = items.where((e) => e['uuid'] == widget.modelUuid);
      if (match.isNotEmpty) {
        _glbUrl = match.first['glb_url']?.toString();
      }
    }
    if (mounted) setState(() {});
    if (!_rated && mounted) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _askRating());
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
      child: _glbUrl == null || _glbUrl!.isEmpty
          ? const Center(child: Text('GLB ещё не готов'))
          : ModelViewer(
              src: _glbUrl!,
              alt: '3D model',
              ar: true,
              autoRotate: true,
              cameraControls: true,
              backgroundColor: AppColors.surface,
            ),
    );
  }
}
