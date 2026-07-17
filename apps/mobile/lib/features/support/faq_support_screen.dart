import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
import 'package:kwork_mobile/core/theme.dart';

/// FAQ + форма вопроса + история обращений (§3.13 / §19.13).
class FaqSupportScreen extends StatefulWidget {
  const FaqSupportScreen({super.key, required this.api, this.initialTicketId});

  final ApiClient api;
  final int? initialTicketId;

  @override
  State<FaqSupportScreen> createState() => _FaqSupportScreenState();
}

class _FaqSupportScreenState extends State<FaqSupportScreen>
    with SingleTickerProviderStateMixin {
  late final FTabController _tabs;
  List<Map<String, dynamic>> _faq = [];
  List<Map<String, dynamic>> _tickets = [];
  bool _loading = true;
  final _subject = TextEditingController();
  final _message = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    AnalyticsService.instance.track('screen_view', {'screen': 'faq_support'});
    _tabs = FTabController(length: 2, vsync: this);
    _load().then((_) => _openInitialTicket());
  }

  Future<void> _openInitialTicket() async {
    final id = widget.initialTicketId;
    if (id == null || !mounted) return;
    _tabs.index = 1;
    await Future<void>.delayed(Duration.zero);
    if (!mounted) return;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (c) => _TicketThreadSheet(api: widget.api, ticketId: id),
    );
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
      final l10n = AppLocalizations.of(context)!;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.faqLoadError('$e'))),
      );
    }
  }

  Future<void> _ask() async {
    final l10n = AppLocalizations.of(context)!;
    if (_message.text.trim().length < 10) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.faqQuestionMin)),
      );
      return;
    }
    setState(() => _sending = true);
    try {
      await widget.api.askSupport(
        subject: _subject.text.trim().isEmpty ? l10n.faqDefaultSubject : _subject.text.trim(),
        message: _message.text.trim(),
      );
      _subject.clear();
      _message.clear();
      await _load();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.faqQuestionSent)),
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
    final l10n = AppLocalizations.of(context)!;
    return FScaffold(
      header: FHeader(
        title: Text(l10n.faqSupportTitle),
        suffixes: [
          FHeaderAction(
            icon: const Icon(FIcons.refreshCw),
            onPress: _load,
          ),
        ],
      ),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : FTabs(
              expands: true,
              control: FTabControl.managed(controller: _tabs),
              children: [
                FTabEntry(
                  label: Text(l10n.faqTab),
                  child: _FaqTab(
                    items: _faq,
                    subject: _subject,
                    message: _message,
                    sending: _sending,
                    onAsk: _ask,
                  ),
                ),
                FTabEntry(
                  label: Text(l10n.faqMyTickets),
                  child: _TicketsTab(items: _tickets, api: widget.api),
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
    final l10n = AppLocalizations.of(context)!;
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (items.isEmpty)
          Text(l10n.faqEmpty)
        else
          FAccordion(
            children: [
              for (final f in items)
                FAccordionItem(
                  title: Text(f['question']?.toString() ?? ''),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Text(f['answer']?.toString() ?? ''),
                  ),
                ),
            ],
          ),
        const SizedBox(height: 24),
        Text(
          l10n.faqAskPrompt,
          style: context.theme.typography.sm.copyWith(
            color: context.theme.colors.mutedForeground,
          ),
        ),
        const SizedBox(height: 8),
        FTextField(
          control: FTextFieldControl.managed(controller: subject),
          label: Text(l10n.faqSubjectOptional),
        ),
        const SizedBox(height: 8),
        FTextField(
          control: FTextFieldControl.managed(controller: message),
          label: Text(l10n.faqYourQuestion),
          maxLines: 4,
        ),
        const SizedBox(height: 12),
        FButton(
          onPress: sending ? null : onAsk,
          child: Text(sending ? l10n.faqSending : l10n.faqSend),
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
    final l10n = AppLocalizations.of(context)!;
    if (items.isEmpty) {
      return Center(child: Text(l10n.faqNoTickets));
    }
    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: items.length,
      separatorBuilder: (_, __) => const Divider(),
      itemBuilder: (ctx, i) {
        final t = items[i];
        return FTile(
          title: Text(t['subject']?.toString() ?? l10n.faqTicketDefault('${t['id']}')),
          subtitle: Text('${t['status']} · ${t['created_at'] ?? ''}'),
          onPress: () async {
            await showModalBottomSheet<void>(
              context: ctx,
              isScrollControlled: true,
              builder: (c) => _TicketThreadSheet(
                api: api,
                ticketId: t['id'] as int,
              ),
            );
          },
        );
      },
    );
  }
}

class _TicketThreadSheet extends StatefulWidget {
  const _TicketThreadSheet({required this.api, required this.ticketId});

  final ApiClient api;
  final int ticketId;

  @override
  State<_TicketThreadSheet> createState() => _TicketThreadSheetState();
}

class _TicketThreadSheetState extends State<_TicketThreadSheet> {
  Map<String, dynamic>? _detail;
  final _reply = TextEditingController();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _reply.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final detail = await widget.api.getSupportQuestion(widget.ticketId);
    if (mounted) setState(() => _detail = detail);
  }

  bool get _closed {
    final s = _detail?['status']?.toString();
    return s == 'closed' || s == 'resolved';
  }

  Future<void> _send() async {
    if (_reply.text.trim().isEmpty || _closed) return;
    setState(() => _busy = true);
    try {
      await widget.api.replySupport(widget.ticketId, _reply.text.trim());
      _reply.clear();
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final msgs = (_detail?['messages'] as List?) ?? [];
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        top: 16,
        bottom: MediaQuery.viewInsetsOf(context).bottom + 16,
      ),
      child: SizedBox(
        height: MediaQuery.sizeOf(context).height * 0.65,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              l10n.queueStatus('${_detail?['status'] ?? '…'}'),
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            Expanded(
              child: _detail == null
                  ? const Center(child: CircularProgressIndicator())
                  : ListView(
                      children: [
                        ...msgs.map(
                          (m) => Container(
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: m['is_staff'] == true
                                  ? AppColors.surface
                                  : AppColors.accent.withValues(alpha: 0.08),
                              borderRadius: BorderRadius.circular(10),
                            ),
                            child: Text(
                              '${m['is_staff'] == true ? l10n.faqSupportRole : l10n.faqYouRole}: ${m['body']}',
                            ),
                          ),
                        ),
                      ],
                    ),
            ),
            if (!_closed) ...[
              FTextField(
                control: FTextFieldControl.managed(controller: _reply),
                hint: l10n.faqClarifyHint,
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: FButton(
                      onPress: _busy ? null : _send,
                      child: Text(l10n.faqReply),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FButton(
                    variant: .outline,
                    onPress: _busy
                        ? null
                        : () async {
                            await widget.api.closeSupport(widget.ticketId);
                            await _load();
                          },
                    child: Text(l10n.faqClose),
                  ),
                ],
              ),
            ] else
              Text(l10n.faqTicketClosed),
          ],
        ),
      ),
    );
  }
}
