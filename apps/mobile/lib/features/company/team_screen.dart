import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
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
  int _membersTotal = 0;
  bool _loadingMoreMembers = false;
  static const _memberPageSize = 20;
  bool _loading = true;
  bool _busy = false;

  final _memberSearchCtrl = TextEditingController();
  String _memberSearch = '';
  String? _memberRoleFilter;

  final _inviteEmail = TextEditingController();
  String _inviteRole = 'photographer';
  int _inviteLimit = 3;

  @override
  void initState() {
    super.initState();
    AnalyticsService.instance.track('screen_view', {'screen': 'team'});
    _tabs = FTabController(length: 3, vsync: this);
    _memberSearchCtrl.addListener(_onMemberSearchChanged);
    _load();
  }

  void _onMemberSearchChanged() {
    final next = _memberSearchCtrl.text.trim();
    if (next == _memberSearch) return;
    Future<void>.delayed(const Duration(milliseconds: 400), () {
      if (!mounted || _memberSearchCtrl.text.trim() != next) return;
      setState(() => _memberSearch = next);
      _loadMembers();
    });
  }

  @override
  void dispose() {
    _tabs.dispose();
    _inviteEmail.dispose();
    _memberSearchCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadMembers({bool append = false}) async {
    if (append) {
      if (_loadingMoreMembers || _members.length >= _membersTotal) return;
      setState(() => _loadingMoreMembers = true);
    }
    try {
      final data = await widget.api.listCompanyMembers(
        search: _memberSearch.isEmpty ? null : _memberSearch,
        role: _memberRoleFilter,
        limit: _memberPageSize,
        offset: append ? _members.length : 0,
      );
      final items = (data['items'] as List?)
              ?.map((e) => Map<String, dynamic>.from(e as Map))
              .toList() ??
          [];
      _companyId = data['company_id'] as int?;
      _membersTotal = (data['total'] as num?)?.toInt() ?? items.length;
      if (append) {
        _members = [..._members, ...items];
      } else {
        _members = items;
      }
    } catch (_) {}
    if (mounted) {
      setState(() => _loadingMoreMembers = false);
    }
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      await _loadMembers();
      _audit = await widget.api.listAuditLog();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _massExtendStorage() async {
    final l10n = AppLocalizations.of(context)!;
    final ok = await showFDialog<bool>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: Text(l10n.teamExtendAllTitle),
        body: Text(l10n.teamExtendAllBody),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
          FButton(onPress: () => Navigator.pop(ctx, true), child: Text(l10n.teamExtend)),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      final res = await widget.api.massExtendCompanyStorage();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(res['message']?.toString() ?? l10n.done)),
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

  Future<void> _invite() async {
    final l10n = AppLocalizations.of(context)!;
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
          SnackBar(content: Text(url != null ? l10n.teamInviteSentWithLink : l10n.teamInviteSent)),
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
    final l10n = AppLocalizations.of(context)!;
    var role = m['role']?.toString() ?? 'photographer';
    var limit = (m['max_concurrent_orders'] as num?)?.toInt() ?? 3;
    final limitCtrl = TextEditingController(text: '$limit');
    final ok = await showFDialog<bool>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: Text(m['email']?.toString() ?? l10n.teamMemberFallback),
        body: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            FSelect<String>(
              label: Text(l10n.teamRole),
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
              label: Text(l10n.teamActiveOrdersLimit),
              keyboardType: TextInputType.number,
            ),
          ],
        ),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
          FButton(onPress: () => Navigator.pop(ctx, true), child: Text(l10n.save)),
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
    final l10n = AppLocalizations.of(context)!;
    if (!widget.session.canManageTeam) {
      return FScaffold(child: Center(child: Text(l10n.teamNoAccess)));
    }
    return FScaffold(
      header: FHeader(title: Text(l10n.teamTitle)),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : FTabs(
              expands: true,
              control: FTabControl.managed(controller: _tabs),
              children: [
                FTabEntry(
                  label: Text(l10n.teamMembers),
                  child: RefreshIndicator(
                    onRefresh: _load,
                    child: _members.isEmpty
                        ? ListView(children: [Center(child: Text(l10n.teamNoMembers))])
                        : ListView(
                            padding: const EdgeInsets.all(16),
                            children: [
                              if (widget.session.isOwner) ...[
                                FButton(
                                  variant: .outline,
                                  onPress: _busy ? null : _massExtendStorage,
                                  prefix: const Icon(FIcons.clock),
                                  child: Text(l10n.teamExtendAllBtn),
                                ),
                                const SizedBox(height: 16),
                              ],
                              FTextField(
                                control: FTextFieldControl.managed(controller: _memberSearchCtrl),
                                label: Text(l10n.teamSearchHint),
                              ),
                              const SizedBox(height: 8),
                              FSelect<String?>(
                                label: Text(l10n.teamRole),
                                control: FSelectControl.managed(
                                  initial: _memberRoleFilter,
                                  onChange: (v) {
                                    setState(() => _memberRoleFilter = v);
                                    _loadMembers().then((_) {
                                      if (mounted) setState(() {});
                                    });
                                  },
                                ),
                                items: {
                                  l10n.teamRoleAll: null,
                                  'Manager': 'manager',
                                  'Photographer': 'photographer',
                                  'Viewer': 'viewer',
                                  'Owner': 'owner',
                                },
                              ),
                              if (_membersTotal > _members.length)
                                Padding(
                                  padding: const EdgeInsets.only(top: 12),
                                  child: FButton(
                                    variant: .outline,
                                    onPress: _loadingMoreMembers ? null : () => _loadMembers(append: true),
                                    child: Text(
                                      _loadingMoreMembers ? '…' : l10n.teamLoadMore,
                                    ),
                                  ),
                                ),
                              const SizedBox(height: 12),
                              for (final m in _members)
                                FTile(
                                  title: Text(m['full_name']?.toString() ?? m['email']?.toString() ?? '—'),
                                  subtitle: Text(
                                    l10n.teamMemberSubtitle(
                                      '${m['role']}',
                                      '${m['max_concurrent_orders'] ?? '—'}',
                                    ),
                                  ),
                                  onPress: _busy ? null : () => _editMember(m),
                                ),
                            ],
                          ),
                  ),
                ),
                FTabEntry(
                  label: Text(l10n.teamInvite),
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (_companyId != null)
                        Text(l10n.teamCompany('$_companyId'), style: context.theme.typography.sm),
                      const SizedBox(height: 12),
                      FTextField(
                        control: FTextFieldControl.managed(controller: _inviteEmail),
                        label: const Text('Email'),
                        keyboardType: TextInputType.emailAddress,
                      ),
                      const SizedBox(height: 12),
                      FSelect<String>(
                        label: Text(l10n.teamRole),
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
                        label: Text(l10n.teamActiveOrdersLimit),
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
                        child: Text(_busy ? '…' : l10n.teamSendInvite),
                      ),
                    ],
                  ),
                ),
                FTabEntry(
                  label: Text(l10n.teamAudit),
                  child: RefreshIndicator(
                    onRefresh: _load,
                    child: _audit.isEmpty
                        ? ListView(children: [Center(child: Text(l10n.teamNoAudit))])
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
