import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/services/local_model_library.dart';

class StorageSettingsScreen extends StatefulWidget {
  const StorageSettingsScreen({super.key, required this.api});

  final ApiClient api;

  @override
  State<StorageSettingsScreen> createState() => _StorageSettingsScreenState();
}

class _StorageSettingsScreenState extends State<StorageSettingsScreen> {
  final _lib = LocalModelLibrary.instance;
  ({int bytes, int models, int glbs})? _stats;
  bool _autoCleanup = false;
  bool _autoDownload = true;
  int _cleanupDays = 30;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    _stats = await _lib.storageStats();
    _autoCleanup = await _lib.autoCleanupEnabled();
    _autoDownload = await _lib.loadAutoDownloadEnabled();
    _cleanupDays = await _lib.autoCleanupDays();
    if (mounted) setState(() {});
  }

  Future<void> _exportZip() async {
    setState(() => _busy = true);
    try {
      final zip = await _lib.exportAllZip();
      await Clipboard.setData(ClipboardData(text: zip.path));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('ZIP: ${zip.path} (путь скопирован)')),
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

  Future<void> _cleanupNow() async {
    setState(() => _busy = true);
    try {
      final n = await _lib.runAutoCleanup();
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Удалено локальных GLB: $n')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final stats = _stats;
    return FScaffold(
      header: const FHeader(title: Text('Локальное хранилище')),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (stats != null)
            Text(
              'Занято: ${_lib.formatBytes(stats.bytes)} · '
              'папок: ${stats.models} · GLB: ${stats.glbs}',
              style: context.theme.typography.lg,
            ),
          const SizedBox(height: 16),
          FSwitch(
            label: const Text('Автозагрузка GLB при завершении'),
            description: const Text('§3.3.2 — сохранять модель на устройство'),
            value: _autoDownload,
            enabled: !_busy,
            onChange: (v) async {
              await _lib.setAutoDownloadEnabled(v);
              setState(() => _autoDownload = v);
            },
          ),
          const SizedBox(height: 12),
          FSwitch(
            label: const Text('Автоочистка GLB'),
            description: Text('Удалять не избранные старше $_cleanupDays дн.'),
            value: _autoCleanup,
            enabled: !_busy,
            onChange: (v) async {
              await _lib.setAutoCleanupEnabled(v);
              setState(() => _autoCleanup = v);
            },
          ),
          const SizedBox(height: 12),
          FSelect<int>(
            label: const Text('Срок автоочистки (дней)'),
            enabled: !_busy,
            control: FSelectControl.managed(
              initial: _cleanupDays,
              onChange: (v) async {
                if (v == null) return;
                await _lib.setAutoCleanupDays(v);
                setState(() => _cleanupDays = v);
              },
            ),
            items: const {
              '7 дней': 7,
              '14 дней': 14,
              '30 дней': 30,
              '60 дней': 60,
              '90 дней': 90,
            },
          ),
          const SizedBox(height: 16),
          FButton(
            onPress: _busy ? null : _cleanupNow,
            variant: .outline,
            child: const Text('Очистить сейчас'),
          ),
          const SizedBox(height: 8),
          FButton(
            onPress: _busy ? null : _exportZip,
            child: const Text('Экспорт всех GLB в ZIP'),
          ),
        ],
      ),
    );
  }
}
