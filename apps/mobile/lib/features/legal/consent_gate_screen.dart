import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/services/push_deep_link.dart';

/// Блокировка приложения до принятия новых версий документов (§2.8.2).
class LegalConsentGateScreen extends StatefulWidget {
  const LegalConsentGateScreen({super.key, required this.api});

  final ApiClient api;

  @override
  State<LegalConsentGateScreen> createState() => _LegalConsentGateScreenState();
}

class _LegalConsentGateScreenState extends State<LegalConsentGateScreen> {
  List<Map<String, dynamic>> _pending = [];
  final _accepted = <String>{};
  final _bodies = <String, String>{};
  bool _loading = true;
  bool _submitting = false;
  String? _error;
  String? _expanded;

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
      final pending = await widget.api.legalPending();
      for (final p in pending) {
        final slug = p['slug']?.toString();
        if (slug == null) continue;
        try {
          final doc = await widget.api.legalDocument(slug);
          _bodies[slug] = doc['body']?.toString() ?? '';
        } catch (_) {
          _bodies[slug] = '';
        }
      }
      if (!mounted) return;
      setState(() {
        _pending = pending;
        _loading = false;
      });
      if (pending.isEmpty) {
        await _goHomeAfterConsent();
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _loading = false;
          _error = formatApiError(e);
        });
      }
    }
  }

  Future<void> _goHomeAfterConsent() async {
    if (!mounted) return;
    final pending = await PushDeepLink.take();
    if (pending != null) {
      context.go(pending);
      return;
    }
    context.go('/home');
  }

  Future<void> _submit() async {
    final slugs = _pending.map((e) => e['slug']?.toString()).whereType<String>().toList();
    if (!_accepted.containsAll(slugs)) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Примите все обновлённые документы')),
      );
      return;
    }
    setState(() => _submitting = true);
    try {
      await widget.api.legalAccept(slugs);
      if (mounted) await _goHomeAfterConsent();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FScaffold(
      header: const FHeader(title: Text('Обновлены условия')),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(_error!, style: const TextStyle(color: AppColors.error)),
                      FButton(onPress: _load, child: const Text('Повторить')),
                    ],
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    const Text(
                      'Для продолжения работы примите новые версии документов (§2.8).',
                      style: TextStyle(color: AppColors.textSecondary),
                    ),
                    const SizedBox(height: 16),
                    ..._pending.map((p) {
                      final slug = p['slug']?.toString() ?? '';
                      final title = p['title']?.toString() ?? slug;
                      final version = p['version'];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Text('$title · v$version', style: const TextStyle(fontWeight: FontWeight.w600)),
                              TextButton(
                                onPressed: () => setState(() {
                                  _expanded = _expanded == slug ? null : slug;
                                }),
                                child: Text(_expanded == slug ? 'Скрыть текст' : 'Читать'),
                              ),
                              if (_expanded == slug)
                                Container(
                                  constraints: const BoxConstraints(maxHeight: 220),
                                  padding: const EdgeInsets.all(8),
                                  color: AppColors.surface,
                                  child: SingleChildScrollView(
                                    child: Text(_bodies[slug] ?? '', style: const TextStyle(fontSize: 13)),
                                  ),
                                ),
                              CheckboxListTile(
                                value: _accepted.contains(slug),
                                onChanged: (v) => setState(() {
                                  if (v == true) {
                                    _accepted.add(slug);
                                  } else {
                                    _accepted.remove(slug);
                                  }
                                }),
                                title: const Text('Принимаю'),
                                controlAffinity: ListTileControlAffinity.leading,
                                contentPadding: EdgeInsets.zero,
                              ),
                            ],
                          ),
                        ),
                      );
                    }),
                    const SizedBox(height: 12),
                    FButton(
                      onPress: _submitting ? null : _submit,
                      child: Text(_submitting ? 'Сохранение…' : 'Продолжить'),
                    ),
                  ],
                ),
    );
  }
}
