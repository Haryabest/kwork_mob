import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
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
    AnalyticsService.instance.track('screen_view', {'screen': 'storage'});
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
    final l10n = AppLocalizations.of(context)!;
    setState(() => _busy = true);
    try {
      final zip = await _lib.exportAllZip();
      await Clipboard.setData(ClipboardData(text: zip.path));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.storZipCopied(zip.path))),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e')),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _cleanupNow() async {
    final l10n = AppLocalizations.of(context)!;
    setState(() => _busy = true);
    try {
      final n = await _lib.runAutoCleanup();
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.storGlbDeleted('$n'))),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final stats = _stats;
    return FScaffold(
      header: FHeader(title: Text(l10n.localStorage)),
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (stats != null)
            Text(
              l10n.storUsedLine(
                _lib.formatBytes(stats.bytes),
                '${stats.models}',
                '${stats.glbs}',
              ),
              style: context.theme.typography.lg,
            ),
          const SizedBox(height: 16),
          FSwitch(
            label: Text(l10n.storAutoDownload),
            description: Text(l10n.storAutoDownloadDesc),
            value: _autoDownload,
            enabled: !_busy,
            onChange: (v) async {
              await _lib.setAutoDownloadEnabled(v);
              setState(() => _autoDownload = v);
            },
          ),
          const SizedBox(height: 12),
          FSwitch(
            label: Text(l10n.storAutoCleanup),
            description: Text(l10n.storAutoCleanupDesc('$_cleanupDays')),
            value: _autoCleanup,
            enabled: !_busy,
            onChange: (v) async {
              await _lib.setAutoCleanupEnabled(v);
              setState(() => _autoCleanup = v);
            },
          ),
          const SizedBox(height: 12),
          FSelect<int>(
            label: Text(l10n.storCleanupDays),
            enabled: !_busy,
            control: FSelectControl.managed(
              initial: _cleanupDays,
              onChange: (v) async {
                if (v == null) return;
                await _lib.setAutoCleanupDays(v);
                setState(() => _cleanupDays = v);
              },
            ),
            items: {
              l10n.storDays7: 7,
              l10n.storDays14: 14,
              l10n.storDays30: 30,
              l10n.storDays60: 60,
              l10n.storDays90: 90,
            },
          ),
          const SizedBox(height: 16),
          FButton(
            onPress: _busy ? null : _cleanupNow,
            variant: .outline,
            child: Text(l10n.storCleanupNow),
          ),
          const SizedBox(height: 8),
          FButton(
            onPress: _busy ? null : _exportZip,
            child: Text(l10n.storExportZip),
          ),
        ],
      ),
    );
  }
}
