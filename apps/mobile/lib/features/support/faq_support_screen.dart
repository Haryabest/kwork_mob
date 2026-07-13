import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';

/// FAQ + форма вопроса + история обращений (§3.13 / §19.13).
class FaqSupportScreen extends StatefulWidget {
  const FaqSupportScreen({super.key, required this.api});

  final ApiClient api;

  @override
  State<FaqSupportScreen> createState() => _FaqSupportScreenState();
}

class _FaqSupportScreenState extends State<FaqSupportScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;
  List<Map<String, dynamic>> _faq = [];
  List<Map<String, dynamic>> _tickets = [];
  bool _loading = true;
  final _subject = TextEditingController();
  final _message = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 2, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    _subject.dispose();
    _message.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final faq = await widget.api.getFaq();
      final tickets = await widget.api.listSupportQuestions();
      if (!mounted) return;
      setState(() {
        _faq = faq;
        _tickets = tickets;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка загрузки: $e')),
      );
    }
  }

  Future<void> _ask() async {
    if (_message.text.trim().length < 10) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Вопрос: минимум 10 символов')),
      );
      return;
    }
    setState(() => _sending = true);
    try {
      await widget.api.askSupport(
        subject: _subject.text.trim().isEmpty ? 'Вопрос из приложения' : _subject.text.trim(),
        message: _message.text.trim(),
      );
      _subject.clear();
      _message.clear();
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Вопрос отправлен')),
      );
      _tabs.animateTo(1);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('$e')),
      );
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return FScaffold(
      header: FHeader(
        title: const Text('FAQ / Поддержка'),
        suffixes: [
          FHeaderAction(
            icon: const Icon(FIcons.refreshCw),
            onPress: _load,
          ),
        ],
      ),
      child: Column(
        children: [
          TabBar(
            controller: _tabs,
            labelColor: context.theme.colors.primary,
            tabs: const [
              Tab(text: 'FAQ'),
              Tab(text: 'Мои обращения'),
            ],
          ),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : TabBarView(
                    controller: _tabs,
                    children: [
                      _FaqTab(
                        items: _faq,
                        subject: _subject,
                        message: _message,
                        sending: _sending,
                        onAsk: _ask,
                      ),
                      _TicketsTab(items: _tickets, api: widget.api),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}

class _FaqTab extends StatelessWidget {
  const _FaqTab({
    required this.items,
    required this.subject,
    required this.message,
    required this.sending,
    required this.onAsk,
  });

  final List<Map<String, dynamic>> items;
  final TextEditingController subject;
  final TextEditingController message;
  final bool sending;
  final VoidCallback onAsk;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (items.isEmpty)
          const Text('Пока нет вопросов в FAQ')
        else
          ...items.map(
            (f) => ExpansionTile(
              title: Text(f['question']?.toString() ?? ''),
              subtitle: Text(f['category']?.toString() ?? ''),
              children: [
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(f['answer']?.toString() ?? ''),
                ),
              ],
            ),
          ),
        const SizedBox(height: 24),
        Text(
          'Не нашли ответ? Задайте вопрос',
          style: context.theme.typography.sm.copyWith(
            color: context.theme.colors.mutedForeground,
          ),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: subject,
          decoration: const InputDecoration(labelText: 'Тема (опционально)'),
        ),
        const SizedBox(height: 8),
        TextField(
          controller: message,
          maxLines: 4,
          decoration: const InputDecoration(labelText: 'Ваш вопрос'),
        ),
        const SizedBox(height: 12),
        FButton(
          onPress: sending ? null : onAsk,
          child: Text(sending ? 'Отправка…' : 'Отправить'),
        ),
      ],
    );
  }
}

class _TicketsTab extends StatelessWidget {
  const _TicketsTab({required this.items, required this.api});

  final List<Map<String, dynamic>> items;
  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const Center(child: Text('Нет обращений'));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: items.length,
      separatorBuilder: (_, __) => const Divider(),
      itemBuilder: (ctx, i) {
        final t = items[i];
        return ListTile(
          title: Text(t['subject']?.toString() ?? 'Обращение #${t['id']}'),
          subtitle: Text('${t['status']} · ${t['created_at'] ?? ''}'),
          onTap: () async {
            try {
              final detail = await api.getSupportQuestion(t['id'] as int);
              if (!ctx.mounted) return;
              await showModalBottomSheet<void>(
                context: ctx,
                isScrollControlled: true,
                builder: (c) => DraggableScrollableSheet(
                  expand: false,
                  initialChildSize: 0.6,
                  builder: (_, scroll) {
                    final msgs = (detail['messages'] as List?) ?? [];
                    return ListView(
                      controller: scroll,
                      padding: const EdgeInsets.all(16),
                      children: [
                        Text('Статус: ${detail['status']}'),
                        const SizedBox(height: 12),
                        ...msgs.map(
                          (m) => Padding(
                            padding: const EdgeInsets.only(bottom: 8),
                            child: Text(
                              '${m['is_staff'] == true ? 'Поддержка' : 'Вы'}: ${m['body']}',
                            ),
                          ),
                        ),
                      ],
                    );
                  },
                ),
              );
            } catch (e) {
              if (ctx.mounted) {
                ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text('$e')));
              }
            }
          },
        );
      },
    );
  }
}
