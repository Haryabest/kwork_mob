import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';

class TeamScreen extends StatefulWidget {
  const TeamScreen({super.key, required this.api, required this.session});

  final ApiClient api;
  final AppSession session;

  @override
  State<TeamScreen> createState() => _TeamScreenState();
}

class _TeamScreenState extends State<TeamScreen> with SingleTickerProviderStateMixin {
  late final FTabController _tabs;
  List<Map<String, dynamic>> _members = [];
  List<Map<String, dynamic>> _audit = [];
  int? _companyId;
  bool _loading = true;
  bool _busy = false;

  final _inviteEmail = TextEditingController();
  String _inviteRole = 'photographer';
  int _inviteLimit = 3;

  @override
  void initState() {
    super.initState();
    _tabs = FTabController(length: 3, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    _inviteEmail.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final data = await widget.api.listCompanyMembers();
      _members = (data['items'] as List?)
              ?.map((e) => Map<String, dynamic>.from(e as Map))
              .toList() ??
          [];
      _companyId = data['company_id'] as int?;
      _audit = await widget.api.listAuditLog();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _invite() async {
    final email = _inviteEmail.text.trim();
    if (email.length < 5) return;
    setState(() => _busy = true);
    try {
      final res = await widget.api.inviteMember(
        email: email,
        role: _inviteRole,
        companyId: _companyId,
        maxConcurrentOrders: _inviteLimit,
      );
      _inviteEmail.clear();
      if (mounted) {
        final url = res['url']?.toString();
        if (url != null) await Clipboard.setData(ClipboardData(text: url));
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Приглашение отправлено${url != null ? ' · ссылка скопирована' : ''}')),
        );
      }
      await _load();
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

  Future<void> _editMember(Map<String, dynamic> m) async {
    var role = m['role']?.toString() ?? 'photographer';
    var limit = (m['max_concurrent_orders'] as num?)?.toInt() ?? 3;
    final limitCtrl = TextEditingController(text: '$limit');
    final ok = await showFDialog<bool>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: Text(m['email']?.toString() ?? 'Сотрудник'),
        body: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            FSelect<String>(
              label: const Text('Роль'),
              control: FSelectControl.managed(
                initial: role,
                onChange: (v) {
                  if (v != null) role = v;
                },
              ),
              items: const {
                'Manager': 'manager',
                'Photographer': 'photographer',
                'Viewer': 'viewer',
              },
            ),
            const SizedBox(height: 8),
            FTextField(
              control: FTextFieldControl.managed(controller: limitCtrl),
              label: const Text('Лимит активных заказов'),
              keyboardType: TextInputType.number,
            ),
          ],
        ),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
          FButton(onPress: () => Navigator.pop(ctx, true), child: const Text('Сохранить')),
        ],
      ),
    );
    if (ok != true) {
      limitCtrl.dispose();
      return;
    }
    final userId = m['user_id'] as int?;
    final parsedLimit = int.tryParse(limitCtrl.text.trim());
    limitCtrl.dispose();
    if (userId == null) return;
    setState(() => _busy = true);
    try {
      await widget.api.changeMemberRole(userId: userId, role: role);
      if (parsedLimit != null) {
        await widget.api.changeMemberLimits(userId: userId, maxConcurrentOrders: parsedLimit);
      }
      await _load();
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

  @override
  Widget build(BuildContext context) {
    if (!widget.session.canManageTeam) {
      return const FScaffold(child: Center(child: Text('Нет доступа к команде')));
    }
    return FScaffold(
      header: FHeader(title: const Text('Команда')),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : FTabs(
              expands: true,
              control: FTabControl.managed(controller: _tabs),
              children: [
                FTabEntry(
                  label: const Text('Участники'),
                  child: RefreshIndicator(
                    onRefresh: _load,
                    child: _members.isEmpty
                        ? ListView(children: const [Center(child: Text('Нет сотрудников'))])
                        : ListView(
                            padding: const EdgeInsets.all(16),
                            children: [
                              for (final m in _members)
                                FTile(
                                  title: Text(m['full_name']?.toString() ?? m['email']?.toString() ?? '—'),
                                  subtitle: Text(
                                    '${m['role']} · лимит ${m['max_concurrent_orders'] ?? '—'} заказов',
                                  ),
                                  onPress: _busy ? null : () => _editMember(m),
                                ),
                            ],
                          ),
                  ),
                ),
                FTabEntry(
                  label: const Text('Пригласить'),
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (_companyId != null)
                        Text('Компания #$_companyId', style: context.theme.typography.sm),
                      const SizedBox(height: 12),
                      FTextField(
                        control: FTextFieldControl.managed(controller: _inviteEmail),
                        label: const Text('Email'),
                        keyboardType: TextInputType.emailAddress,
                      ),
                      const SizedBox(height: 12),
                      FSelect<String>(
                        label: const Text('Роль'),
                        enabled: !_busy,
                        control: FSelectControl.managed(
                          initial: _inviteRole,
                          onChange: _busy
                              ? null
                              : (v) {
                                  if (v != null) setState(() => _inviteRole = v);
                                },
                        ),
                        items: const {
                          'Manager': 'manager',
                          'Photographer': 'photographer',
                          'Viewer': 'viewer',
                        },
                      ),
                      const SizedBox(height: 12),
                      FSelect<int>(
                        label: const Text('Лимит активных заказов'),
                        enabled: !_busy,
                        control: FSelectControl.managed(
                          initial: _inviteLimit,
                          onChange: _busy
                              ? null
                              : (v) {
                                  if (v != null) setState(() => _inviteLimit = v);
                                },
                        ),
                        items: const {
                          '1': 1,
                          '2': 2,
                          '3': 3,
                          '5': 5,
                          '10': 10,
                        },
                      ),
                      const SizedBox(height: 16),
                      FButton(
                        onPress: _busy ? null : _invite,
                        child: Text(_busy ? '…' : 'Отправить приглашение'),
                      ),
                    ],
                  ),
                ),
                FTabEntry(
                  label: const Text('Аудит'),
                  child: RefreshIndicator(
                    onRefresh: _load,
                    child: _audit.isEmpty
                        ? ListView(children: const [Center(child: Text('Нет записей аудита'))])
                        : ListView(
                            padding: const EdgeInsets.all(16),
                            children: [
                              for (final a in _audit)
                                FTile(
                                  title: Text(a['action']?.toString() ?? '—'),
                                  subtitle: Text(
                                    '${a['created_at'] ?? ''}\n${a['details'] ?? ''}',
                                    maxLines: 3,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                            ],
                          ),
                  ),
                ),
              ],
            ),
    );
  }
}
