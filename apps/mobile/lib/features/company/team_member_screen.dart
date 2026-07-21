import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

/// Детальная карточка сотрудника §3.16.1 (parity web `/team/[userId]`).
class TeamMemberScreen extends StatefulWidget {
  const TeamMemberScreen({
    super.key,
    required this.api,
    required this.session,
    required this.userId,
  });

  final ApiClient api;
  final AppSession session;
  final int userId;

  @override
  State<TeamMemberScreen> createState() => _TeamMemberScreenState();
}

class _TeamMemberScreenState extends State<TeamMemberScreen> {
  Map<String, dynamic>? _member;
  List<Map<String, dynamic>> _tasks = [];
  List<Map<String, dynamic>> _sessions = [];
  bool _loading = true;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final results = await Future.wait([
        widget.api.getCompanyMember(widget.userId),
        widget.api.listMemberTasks(widget.userId),
        widget.api.listMemberSessions(widget.userId),
      ]);
      _member = results[0];
      _tasks = results[1];
      _sessions = results[2];
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _saveRole(String role) async {
    setState(() => _busy = true);
    try {
      await widget.api.changeMemberRole(userId: widget.userId, role: role);
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _saveLimits(int limit) async {
    setState(() => _busy = true);
    try {
      await widget.api.changeMemberLimits(
        userId: widget.userId,
        maxConcurrentOrders: limit,
      );
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _revokeSessions() async {
    setState(() => _busy = true);
    try {
      await widget.api.revokeMemberSessions(widget.userId);
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _removeMember() async {
    final l10n = AppLocalizations.of(context)!;
    final ok = await showFDialog<bool>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: const Text('Удалить сотрудника'),
        body: const Text(
          'Черновики и незавершённые заказы останутся в компании. Продолжить?',
        ),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
          FButton(
            variant: .destructive,
            onPress: () => Navigator.pop(ctx, true),
            child: Text(l10n.yes),
          ),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      await widget.api.removeCompanyMember(widget.userId);
      if (mounted) context.pop();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  int get _activeTasks => _tasks.where((t) {
        final s = t['status']?.toString() ?? '';
        return {'pending', 'awaiting_payment', 'paid', 'queued', 'processing', 'generating'}.contains(s);
      }).length;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final m = _member;
    return FScaffold(
      header: FHeader.nested(
        title: Text(m?['full_name']?.toString() ?? m?['email']?.toString() ?? l10n.teamMemberFallback),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
      ),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : m == null
              ? Center(child: Text(l10n.teamNoMembers))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      Text(m['email']?.toString() ?? '—', style: const TextStyle(color: AppColors.textSecondary)),
                      const SizedBox(height: 8),
                      Text(
                        l10n.teamMemberSubtitle('${m['role']}', '${m['max_concurrent_orders'] ?? '—'}'),
                      ),
                      if (m['active_orders_count'] != null || _activeTasks > 0) ...[
                        const SizedBox(height: 8),
                        Text(
                          'Активных заказов: ${m['active_orders_count'] ?? _activeTasks}',
                          style: const TextStyle(fontSize: 13),
                        ),
                      ],
                      if (m['last_activity_at'] != null) ...[
                        const SizedBox(height: 4),
                        Text(
                          'Последняя активность: ${m['last_activity_at']}',
                          style: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
                        ),
                      ],
                      const SizedBox(height: 16),
                      FButton(
                        variant: .outline,
                        onPress: _busy
                            ? null
                            : () => context.go('/home?tab=orders&author=${widget.userId}'),
                        child: const Text('Заказы сотрудника'),
                      ),
                      const SizedBox(height: 16),
                      FSelect<String>(
                        label: Text(l10n.teamRole),
                        enabled: !_busy && widget.session.isOwner,
                        control: FSelectControl.managed(
                          initial: m['role']?.toString() ?? 'photographer',
                          onChange: _busy ? null : (v) { if (v != null) _saveRole(v); },
                        ),
                        items: const {
                          'Manager': 'manager',
                          'Photographer': 'photographer',
                          'Viewer': 'viewer',
                        },
                      ),
                      const SizedBox(height: 12),
                      FSelect<int>(
                        label: Text(l10n.teamActiveOrdersLimit),
                        enabled: !_busy && widget.session.isOwner,
                        control: FSelectControl.managed(
                          initial: (m['max_concurrent_orders'] as num?)?.toInt() ?? 3,
                          onChange: _busy
                              ? null
                              : (v) {
                                  if (v != null) _saveLimits(v);
                                },
                        ),
                        items: const {'1': 1, '2': 2, '3': 3, '5': 5, '10': 10},
                      ),
                      const SizedBox(height: 24),
                      Text('Заказы', style: context.theme.typography.sm),
                      const SizedBox(height: 8),
                      if (_tasks.isEmpty)
                        const Text('Нет заказов', style: TextStyle(color: AppColors.textSecondary))
                      else
                        for (final t in _tasks.take(20))
                          FTile(
                            title: Text('#${t['id']} · ${t['status'] ?? '—'}'),
                            subtitle: Text('${t['category'] ?? '—'} · ${t['tier'] ?? '—'}'),
                          ),
                      const SizedBox(height: 24),
                      Text('Сессии', style: context.theme.typography.sm),
                      const SizedBox(height: 8),
                      if (_sessions.isEmpty)
                        Text('—', style: const TextStyle(color: AppColors.textSecondary))
                      else ...[
                        for (final s in _sessions.take(10))
                          FTile(
                            title: Text(s['created_at']?.toString() ?? '—'),
                            subtitle: Text(s['expires_at']?.toString() ?? ''),
                          ),
                        FButton(
                          variant: .outline,
                          onPress: _busy || !widget.session.isOwner ? null : _revokeSessions,
                          child: const Text('Завершить все сессии'),
                        ),
                      ],
                      if (widget.session.isOwner) ...[
                        const SizedBox(height: 24),
                        FButton(
                          variant: .destructive,
                          onPress: _busy ? null : _removeMember,
                          child: const Text('Удалить сотрудника'),
                        ),
                      ],
                    ],
                  ),
                ),
    );
  }
}
