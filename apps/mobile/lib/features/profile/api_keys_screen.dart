import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

class ApiKeysScreen extends StatefulWidget {
  const ApiKeysScreen({super.key, required this.api});

  final ApiClient api;

  @override
  State<ApiKeysScreen> createState() => _ApiKeysScreenState();
}

class _ApiKeysScreenState extends State<ApiKeysScreen> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;
  String? _error;
  int? _busyId;

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
      final data = await widget.api.listApiKeys();
      _items = (data['items'] as List?)
              ?.map((e) => Map<String, dynamic>.from(e as Map))
              .toList() ??
          [];
    } catch (e) {
      _error = formatApiError(e);
    }
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _create() async {
    final l10n = AppLocalizations.of(context)!;
    final nameCtrl = TextEditingController();
    final ok = await showFDialog<bool>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: Text(l10n.apiKeysCreate),
        body: FTextField(
          control: FTextFieldControl.managed(controller: nameCtrl),
          label: Text(l10n.apiKeysName),
        ),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
          FButton(onPress: () => Navigator.pop(ctx, true), child: Text(l10n.save)),
        ],
      ),
    );
    if (ok != true || nameCtrl.text.trim().length < 2) {
      nameCtrl.dispose();
      return;
    }
    try {
      final res = await widget.api.createApiKey(name: nameCtrl.text.trim());
      nameCtrl.dispose();
      if (!mounted) return;
      final plain = res['key']?.toString() ?? '';
      await showFDialog<void>(
        context: context,
        builder: (ctx, style, animation) => FDialog(
          title: Text(l10n.apiKeysCreated),
          body: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(l10n.apiKeysCopyOnce),
              const SizedBox(height: 8),
              SelectableText(plain, style: const TextStyle(fontSize: 12)),
            ],
          ),
          actions: [
            FButton(
              onPress: () async {
                await Clipboard.setData(ClipboardData(text: plain));
                if (ctx.mounted) Navigator.pop(ctx);
              },
              child: Text(l10n.copyPayload),
            ),
          ],
        ),
      );
      await _load();
    } catch (e) {
      nameCtrl.dispose();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e)), backgroundColor: AppColors.error),
        );
      }
    }
  }

  Future<void> _revoke(int id) async {
    setState(() => _busyId = id);
    try {
      await widget.api.revokeApiKey(id);
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return FScaffold(
      header: FHeader.nested(
        title: Text(l10n.apiKeysTitle),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
        suffixes: [
          FHeaderAction(icon: const Icon(FIcons.plus), onPress: _create),
        ],
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
                  ? Center(child: Text(l10n.apiKeysEmpty))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.all(16),
                        itemCount: _items.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (context, i) {
                          final k = _items[i];
                          final id = k['id'] as int? ?? 0;
                          final busy = _busyId == id;
                          final scopes = (k['scopes'] as List?)?.join(', ') ?? '';
                          return FCard.raw(
                            child: FTile(
                              title: Text(k['name']?.toString() ?? '—'),
                              subtitle: Text('${k['key_prefix'] ?? ''} · $scopes'),
                              details: busy
                                  ? const SizedBox(
                                      width: 24,
                                      height: 24,
                                      child: CircularProgressIndicator(strokeWidth: 2),
                                    )
                                  : FButton(
                                      variant: .destructive,
                                      onPress: () => _revoke(id),
                                      child: Text(l10n.apiKeysRevoke),
                                    ),
                            ),
                          );
                        },
                      ),
                    ),
    );
  }
}
