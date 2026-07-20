import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/analytics_service.dart';

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
  bool _loadingMore = false;
  String? _error;
  String? _busyUuid;
  int _total = 0;
  String? _publishFilter;
  final _searchCtrl = TextEditingController();
  static const _pageSize = 20;

  @override
  void initState() {
    super.initState();
    AnalyticsService.instance.track('screen_view', {'screen': 'trash'});
    _load();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

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
      final page = await widget.api.listTrashModelsPage(
        limit: _pageSize,
        offset: append ? _items.length : 0,
        publishFilter: _publishFilter,
        search: _searchCtrl.text.trim().isEmpty ? null : _searchCtrl.text.trim(),
      );
      final items = (page['items'] as List).cast<Map<String, dynamic>>();
      _total = (page['total'] as num?)?.toInt() ?? items.length;
      if (append) {
        _items = [..._items, ...items];
      } else {
        _items = items;
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

  Widget _filterBar(AppLocalizations l10n) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          FTextField(
            control: FTextFieldControl.managed(controller: _searchCtrl),
            label: const Text('Поиск UUID'),
            onSubmit: (_) => _load(),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            children: [
              FButton(
                style: _publishFilter == null ? .primary : .outline,
                onPress: () {
                  setState(() => _publishFilter = null);
                  _load();
                },
                child: const Text('Все'),
              ),
              FButton(
                style: _publishFilter == 'published' ? .primary : .outline,
                onPress: () {
                  setState(() => _publishFilter = 'published');
                  _load();
                },
                child: const Text('Опублик.'),
              ),
              FButton(
                style: _publishFilter == 'draft' ? .primary : .outline,
                onPress: () {
                  setState(() => _publishFilter = 'draft');
                  _load();
                },
                child: const Text('Черновики'),
              ),
            ],
          ),
        ],
      ),
    );
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
          : RefreshIndicator(
              onRefresh: () => _load(),
              child: _error != null
                  ? ListView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      children: [
                        _filterBar(l10n),
                        SizedBox(height: MediaQuery.sizeOf(context).height * 0.2),
                        Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(_error!, style: const TextStyle(color: AppColors.error)),
                              FButton(onPress: _load, child: Text(l10n.mvRetry)),
                            ],
                          ),
                        ),
                      ],
                    )
                  : _items.isEmpty
                      ? ListView(
                          physics: const AlwaysScrollableScrollPhysics(),
                          children: [
                            _filterBar(l10n),
                            SizedBox(height: MediaQuery.sizeOf(context).height * 0.2),
                            Center(
                              child: Text(
                                _publishFilter != null || _searchCtrl.text.trim().isNotEmpty
                                    ? 'Нет моделей по фильтру'
                                    : l10n.trashEmpty,
                                textAlign: TextAlign.center,
                              ),
                            ),
                          ],
                        )
                      : ListView.separated(
                          physics: const AlwaysScrollableScrollPhysics(),
                          padding: const EdgeInsets.only(bottom: 16),
                          itemCount: _items.length + (_items.length < _total ? 1 : 0) + 1,
                          separatorBuilder: (_, i) => i == 0 ? const SizedBox.shrink() : const SizedBox(height: 8),
                          itemBuilder: (context, i) {
                            if (i == 0) return _filterBar(l10n);
                            final idx = i - 1;
                            if (idx >= _items.length) {
                              return FButton(
                                onPress: _loadingMore ? null : () => _load(append: true),
                                child: Text(_loadingMore ? '…' : l10n.mvLoadMore),
                              );
                            }
                            final m = _items[idx];
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
