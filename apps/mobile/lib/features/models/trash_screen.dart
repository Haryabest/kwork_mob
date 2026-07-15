import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

/// Корзина моделей 30 дней §3.3.1
class ModelsTrashScreen extends StatefulWidget {
  const ModelsTrashScreen({super.key, required this.api});

  final ApiClient api;

  @override
  State<ModelsTrashScreen> createState() => _ModelsTrashScreenState();
}

class _ModelsTrashScreenState extends State<ModelsTrashScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;
  String? _busyUuid;

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
      _items = await widget.api.listTrashModels();
    } catch (e) {
      _error = formatApiError(e);
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _restore(String uuid) async {
    final l10n = AppLocalizations.of(context)!;
    setState(() => _busyUuid = uuid);
    try {
      final res = await widget.api.restoreFromTrash(modelUuid: uuid);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(res['message']?.toString() ?? l10n.trashRestored)),
      );
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busyUuid = null);
    }
  }

  String _fmt(String? iso) {
    if (iso == null || iso.length < 10) return '—';
    return iso.substring(0, 10);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return FScaffold(
      header: FHeader.nested(
        title: Text(l10n.trashTitle),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
      ),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(_error!, style: const TextStyle(color: AppColors.error)),
                      FButton(onPress: _load, child: Text(l10n.mvRetry)),
                    ],
                  ),
                )
              : _items.isEmpty
                  ? Center(
                      child: Text(
                        l10n.trashEmpty,
                        textAlign: TextAlign.center,
                      ),
                    )
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: _items.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (context, i) {
                          final m = _items[i];
                          final uuid = m['uuid']?.toString() ?? '';
                          final busy = _busyUuid == uuid;
                          final orderId = m['order_id']?.toString() ?? '—';
                          return FCard.raw(
                            child: FTile(
                              title: Text(uuid.length > 8 ? '${uuid.substring(0, 8)}…' : uuid),
                              subtitle: Text(
                                '${l10n.trashOrderLine(orderId, _fmt(m['trashed_at']?.toString()))}\n'
                                '${l10n.trashPurgeLine(_fmt(m['purge_at']?.toString()))}',
                              ),
                              details: busy
                                  ? const SizedBox(
                                      width: 24,
                                      height: 24,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : FButton(
                                      onPress: () => _restore(uuid),
                                      child: Text(l10n.trashRestore),
                                    ),
                              onPress: () => context.push('/home/models/$uuid', extra: m),
                            ),
                          );
                        },
                      ),
                    ),
    );
  }
}
