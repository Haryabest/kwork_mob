import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/locale_controller.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/core/theme_controller.dart';
import 'package:kwork_mobile/features/models/model_viewer_screen.dart';
import 'package:kwork_mobile/features/support/faq_support_screen.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:kwork_mobile/services/push_service.dart';
import 'package:kwork_mobile/services/export_prefs_service.dart';
import 'package:kwork_mobile/services/local_model_library.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
import 'package:kwork_mobile/services/oauth_audit_hints.dart';
import 'package:kwork_mobile/services/oauth_pending.dart';
import 'package:kwork_mobile/services/notification_inbox.dart';
import 'package:kwork_mobile/services/upload_progress_service.dart';
import 'package:kwork_mobile/widgets/campaign_banner.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({
    super.key,
    required this.api,
    required this.session,
    required this.push,
    this.initialTab,
    this.initialSupportTicketId,
  });

  final ApiClient api;
  final AppSession session;
  final PushService push;
  final int? initialTab;
  final int? initialSupportTicketId;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  late int _index;
  int _unread = 0;
  int? _supportTicketId;
  List<Map<String, dynamic>> _campaignBanners = [];
  final _dismissedBannerIds = <int>{};
  final _homeTabKey = GlobalKey<_HomeTabState>();

  static const _tabScreens = ['home', 'models', 'orders', 'support', 'profile'];

  String _screenName(int i) => _tabScreens[i.clamp(0, _tabScreens.length - 1)];

  @override
  void initState() {
    super.initState();
    _index = widget.initialTab ?? 0;
    _supportTicketId = widget.initialSupportTicketId;
    widget.session.addListener(_onSession);
    _refresh();
    _loadUnread();
    _loadCampaignBanners();
    AnalyticsService.instance.flush(widget.api);
    AnalyticsService.instance.track('screen_view', {'screen': _screenName(_index)});
    LocalModelLibrary.instance.runAutoCleanup();
    LocalModelLibrary.instance.syncPendingDownloads(
      widget.api,
      companyId: widget.session.corporate ? widget.session.companyId : null,
    );
    widget.push.bindForegroundNavigate(_handleForegroundNavigate);
  }

  @override
  void dispose() {
    widget.push.bindForegroundNavigate(null);
    widget.session.removeListener(_onSession);
    super.dispose();
  }

  void _handleForegroundNavigate(String route, {String? title}) {
    final uri = Uri.tryParse(route);
    if (uri == null) return;
    if (uri.path == '/home' && uri.queryParameters['tab'] == 'support') {
      final ticketId = int.tryParse(uri.queryParameters['supportTicket'] ?? '');
      setState(() {
        _index = 3;
        if (ticketId != null) _supportTicketId = ticketId;
      });
      if (title != null && title.isNotEmpty && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(title), duration: const Duration(seconds: 3)),
        );
      }
      return;
    }
    if (uri.path == '/home' && uri.queryParameters['tab'] == 'profile') {
      setState(() => _index = 4);
      return;
    }
    if (mounted) context.go(route);
  }

  Future<void> _loadCampaignBanners() async {
    try {
      final items = await widget.api.listCampaignBanners();
      if (!mounted) return;
      setState(() => _campaignBanners = items);
      for (final b in items) {
        final id = b['id'];
        AnalyticsService.instance.track('screen_view', {
          'screen': 'campaign_banner',
          if (id is int) 'banner_id': id,
        });
      }
    } catch (_) {}
  }

  Future<void> _loadUnread() async {
    var n = 0;
    try {
      final data = await widget.api.listNotifications(limit: 1);
      n = (data['unread'] as num?)?.toInt() ?? 0;
    } catch (_) {
      n = await NotificationInbox.instance.unreadCount();
    }
    if (mounted) setState(() => _unread = n);
  }

  @override
  void didUpdateWidget(HomeShell oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.initialTab != null && widget.initialTab != oldWidget.initialTab) {
      setState(() => _index = widget.initialTab!);
    }
    if (widget.initialSupportTicketId != null &&
        widget.initialSupportTicketId != oldWidget.initialSupportTicketId) {
      setState(() {
        _index = widget.initialTab ?? 3;
        _supportTicketId = widget.initialSupportTicketId;
      });
    }
  }

  void _onSession() {
    if (mounted) setState(() {});
  }

  Future<void> _refresh() async {
    try {
      final me = await widget.api.me();
      widget.session.applyMe(me);
      final companies = await widget.api.myCompanies();
      await widget.session.setCompanies(companies);
    } catch (_) {}
  }

  Future<void> _switchMode() async {
    final l10n = AppLocalizations.of(context)!;
    final session = widget.session;
    if (session.companies.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.homeNoCompanies)),
      );
      return;
    }
    final choice = await showFSheet<Object>(
      context: context,
      side: .btt,
      builder: (ctx) => SafeArea(
        child: FTileGroup(
          children: [
            FTile(
              title: Text(l10n.personalMode),
              selected: !session.corporate,
              onPress: () => Navigator.pop(ctx, 'personal'),
            ),
            ...session.companies.map(
              (c) => FTile(
                title: Text(c['name']?.toString() ?? l10n.corporateMode),
                subtitle: Text(c['role']?.toString() ?? ''),
                selected: session.corporate && session.companyId == c['id'],
                onPress: () => Navigator.pop(ctx, c),
              ),
            ),
          ],
        ),
      ),
    );
    if (choice == null || !mounted) return;
    final confirmed = await showFDialog<bool>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: Text(l10n.homeSwitchModeTitle),
        body: Text(l10n.homeSwitchModeBody),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
          FButton(onPress: () => Navigator.pop(ctx, true), child: Text(l10n.confirm)),
        ],
      ),
    );
    if (confirmed != true) return;
    if (choice == 'personal') {
      if (!session.corporate) return;
      await session.setPersonal();
      AnalyticsService.instance.track('screen_view', {'screen': 'mode_personal'});
    } else {
      final c = choice as Map<String, dynamic>;
      final cid = c['id'] as int?;
      if (session.corporate && session.companyId == cid) return;
      await session.setCompany(c);
      AnalyticsService.instance.track('screen_view', {'screen': 'mode_corporate'});
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final session = widget.session;
    final pages = [
      _HomeTab(
        key: _homeTabKey,
        api: widget.api,
        session: session,
        onSwitchMode: _switchMode,
        onQueue: () => context.push('/home/queue'),
        onNotifications: () async {
          await context.push('/home/notifications');
          await _loadUnread();
        },
        unread: _unread,
        onShootLink: session.canManageTeam
            ? () {
                AnalyticsService.instance.track('screen_view', {'screen': 'shoot_link_fab'});
                context.push('/home/shoot-link');
              }
            : null,
      ),
      ModelsScreen(
        api: widget.api,
        session: session,
        companyId: session.corporate ? session.companyId : null,
        onNotifications: () async {
          await context.push('/home/notifications');
          await _loadUnread();
        },
        unread: _unread,
      ),
      _OrdersTab(api: widget.api, session: session),
      FaqSupportScreen(
        key: ValueKey('support-${_supportTicketId ?? 'list'}'),
        api: widget.api,
        initialTicketId: _supportTicketId,
      ),
      _ProfileTab(
        api: widget.api,
        push: widget.push,
        session: session,
        onSwitchMode: _switchMode,
        onLogout: () async {
          await widget.api.clearTokens();
          if (context.mounted) context.go('/auth');
        },
      ),
    ];

    return Material(
      color: Theme.of(context).scaffoldBackgroundColor,
      child: Stack(
        children: [
          FScaffold(
            child: pages[_index],
            footer: FBottomNavigationBar(
            index: _index,
            onChange: (i) {
              setState(() => _index = i);
              AnalyticsService.instance.track('screen_view', {'screen': _screenName(i)});
              if (i == 0) _homeTabKey.currentState?.refreshPending();
              if (i == 1) {
                LocalModelLibrary.instance.syncPendingDownloads(
                  widget.api,
                  companyId: widget.session.corporate ? widget.session.companyId : null,
                );
              }
            },
            children: [
              FBottomNavigationBarItem(
                icon: const Icon(FIcons.house),
                label: Text(l10n.home),
              ),
              FBottomNavigationBarItem(
                icon: const Icon(FIcons.box),
                label: Text(l10n.models),
              ),
              FBottomNavigationBarItem(
                icon: const Icon(FIcons.receipt),
                label: Text(l10n.orders),
              ),
              FBottomNavigationBarItem(
                icon: const Icon(FIcons.lifeBuoy),
                label: Text(l10n.support),
              ),
              FBottomNavigationBarItem(
                icon: const Icon(FIcons.user),
                label: Text(l10n.profile),
              ),
            ],
          ),
        ),
        if (_index <= 1)
          Positioned(
            left: 16,
            right: 16,
            bottom: 156,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final b in _campaignBanners)
                  if (!_dismissedBannerIds.contains(b['id']))
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: CampaignBanner(
                        title: b['title']?.toString() ?? '',
                        body: b['body']?.toString() ?? '',
                        clickUrl: b['click_url']?.toString(),
                        onCta: () async {
                          final id = b['id'];
                          AnalyticsService.instance.track('screen_view', {
                            'screen': 'campaign_banner_click',
                            if (id is int) 'banner_id': id,
                          });
                          final url = b['click_url']?.toString();
                          final uri = url == null ? null : Uri.tryParse(url);
                          if (uri != null) {
                            await launchUrl(uri, mode: LaunchMode.externalApplication);
                          }
                        },
                        onDismiss: () {
                          final id = b['id'];
                          AnalyticsService.instance.track('screen_view', {
                            'screen': 'campaign_banner_dismiss',
                            if (id is int) 'banner_id': id,
                          });
                          setState(() {
                            if (id is int) _dismissedBannerIds.add(id);
                          });
                        },
                      ),
                    ),
              ],
            ),
          ),
        if (_index <= 1)
          Positioned(
            right: 20,
            bottom: 88,
            child: FloatingActionButton(
              backgroundColor: AppColors.accent,
              foregroundColor: Colors.white,
              onPressed: () => context.push('/home/shoot'),
              tooltip: l10n.shoot,
              child: const Icon(FIcons.camera),
            ),
          ),
        ],
      ),
    );
  }
}

class _HomeTab extends StatefulWidget {
  const _HomeTab({
    super.key,
    required this.api,
    required this.session,
    required this.onSwitchMode,
    required this.onQueue,
    required this.onNotifications,
    required this.unread,
    this.onShootLink,
  });

  final ApiClient api;
  final AppSession session;
  final VoidCallback onSwitchMode;
  final VoidCallback onQueue;
  final VoidCallback onNotifications;
  final int unread;
  final VoidCallback? onShootLink;

  @override
  State<_HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<_HomeTab> {
  ({String modelUuid, int uploaded, int total})? _pendingUpload;

  @override
  void initState() {
    super.initState();
    refreshPending();
  }

  Future<void> refreshPending() async {
    final summary = await UploadProgressService.instance.pendingSummary();
    if (!mounted) return;
    final hadPending = _pendingUpload != null;
    setState(() => _pendingUpload = summary);
    if (summary != null && !hadPending) {
      AnalyticsService.instance.track('screen_view', {'screen': 'pending_upload_banner'});
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final session = widget.session;
    final modeLabel = session.corporate
        ? (session.companyName ?? l10n.corporateMode)
        : l10n.personalMode;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 48, 20, 100),
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                l10n.appName,
                style: context.theme.typography.xl.copyWith(fontWeight: FontWeight.bold),
              ),
            ),
            IconButton(
              onPressed: widget.onNotifications,
              icon: Stack(
                clipBehavior: Clip.none,
                children: [
                  const Icon(FIcons.bell),
                  if (widget.unread > 0)
                    Positioned(
                      right: -6,
                      top: -4,
                      child: FBadge(child: Text('${widget.unread}')),
                    ),
                ],
              ),
            ),
          ],
        ),
        if (_pendingUpload != null) ...[
          const SizedBox(height: 12),
          Material(
            color: AppColors.ozonPrimary.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      const Icon(FIcons.upload, color: AppColors.ozonPrimary, size: 20),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          l10n.homePendingUploadTitle(
                            '${_pendingUpload!.uploaded}',
                            '${_pendingUpload!.total}',
                          ),
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            color: AppColors.ozonPrimary,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    l10n.homePendingUploadHint,
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                  ),
                  const SizedBox(height: 10),
                  FButton(
                    onPress: () async {
                      AnalyticsService.instance.track('screen_view', {'screen': 'pending_upload_continue'});
                      await context.push(
                        '/home/shoot/upload',
                        extra: _pendingUpload!.modelUuid,
                      );
                      await refreshPending();
                    },
                    child: Text(l10n.uploadContinue),
                  ),
                ],
              ),
            ),
          ),
        ],
        const SizedBox(height: 4),
        Text(session.email ?? '…', style: TextStyle(color: AppColors.textSecondary)),
        if (!session.hidePrices && session.balance != null) ...[
          const SizedBox(height: 4),
          Text(
            l10n.balanceLabel(session.balance!.toStringAsFixed(0)),
            style: const TextStyle(color: AppColors.ozonPrimary, fontWeight: FontWeight.w600),
          ),
        ],
        const SizedBox(height: 16),
        FButton(
          variant: .outline,
          onPress: widget.onSwitchMode,
          child: Text(l10n.homeModePrefix(modeLabel)),
        ),
        const SizedBox(height: 24),
        FButton(
          variant: .secondary,
          onPress: widget.onQueue,
          prefix: const Icon(FIcons.hourglass),
          child: Text(l10n.queue),
        ),
        if (widget.onShootLink != null) ...[
          const SizedBox(height: 12),
          FButton(
            variant: .outline,
            onPress: widget.onShootLink,
            prefix: const Icon(FIcons.qrCode),
            child: Text(l10n.homeShootLinkQr),
          ),
        ],
      ],
    );
  }
}

class _OrdersTab extends StatefulWidget {
  const _OrdersTab({required this.api, required this.session});
  final ApiClient api;
  final AppSession session;

  @override
  State<_OrdersTab> createState() => _OrdersTabState();
}

class _OrdersTabState extends State<_OrdersTab> {
  List<Map<String, dynamic>> _items = [];
  List<Map<String, dynamic>> _members = [];
  int _authorFilter = -1;
  bool _loading = true;

  static Map<String, String> _statusLabels(AppLocalizations l10n) => {
    'pending': l10n.orderStatusPending,
    'awaiting_payment': l10n.orderStatusAwaitingPayment,
    'queued': l10n.orderStatusQueued,
    'processing': l10n.orderStatusProcessing,
    'completed': l10n.orderStatusCompleted,
    'failed': l10n.orderStatusFailed,
    'cancelled': l10n.orderStatusCancelled,
    'paid': l10n.orderStatusPaid,
    'blocked_nsfw': l10n.orderStatusBlockedNsfw,
  };

  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    if (widget.session.canFilterCompanyOrders) {
      try {
        final m = await widget.api.listCompanyMembers();
        final raw = m['items'] as List? ?? [];
        _members = raw.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      } catch (_) {}
    }
    await _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _items = await widget.api.listOrders(
        companyId: widget.session.corporate ? widget.session.companyId : null,
        userId: _authorFilter >= 0 ? _authorFilter : null,
      );
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  String _statusText(String? status, AppLocalizations l10n) =>
      _statusLabels(l10n)[status ?? ''] ?? status ?? '—';

  Color _statusColor(String? status) {
    switch (status) {
      case 'completed':
        return AppColors.success;
      case 'processing':
      case 'queued':
        return AppColors.accentBright;
      case 'failed':
      case 'blocked_nsfw':
        return AppColors.error;
      case 'cancelled':
        return AppColors.textSecondary;
      default:
        return AppColors.textSecondary;
    }
  }

  String _authorLabel(int? userId) {
    if (userId == null) return '';
    for (final m in _members) {
      if (m['user_id'] == userId) {
        return m['full_name']?.toString() ?? m['email']?.toString() ?? '#$userId';
      }
    }
    return '#$userId';
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    if (_loading) return const Center(child: CircularProgressIndicator());
    return Column(
      children: [
        if (widget.session.canFilterCompanyOrders && _members.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 48, 16, 0),
            child: FSelect<int>(
              label: Text(l10n.ordersExecutorFilter),
              control: FSelectControl.managed(
                initial: _authorFilter,
                onChange: (v) {
                  setState(() => _authorFilter = v ?? -1);
                  _load();
                },
              ),
              items: {
                l10n.ordersAllMembers: -1,
                for (final m in _members)
                  _authorLabel(m['user_id'] as int?): m['user_id'] as int,
              },
            ),
          ),
        Expanded(
          child: _items.isEmpty
              ? Center(child: Text(l10n.ordersEmpty))
              : ListView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                  itemCount: _items.length,
                  itemBuilder: (context, i) {
                    final o = _items[i];
                    final status = o['status']?.toString();
                    return FTile(
                      title: Text('#${o['id']} · ${_statusText(status, l10n)}'),
                      subtitle: Text(
                        '${o['category']} · ${o['tier']}'
                        '${widget.session.canFilterCompanyOrders && o['user_id'] != null ? ' · ${_authorLabel(o['user_id'] as int?)}' : ''}',
                      ),
                      prefix: Icon(
                        status == 'blocked_nsfw' ? Icons.block : Icons.shopping_bag_outlined,
                        color: _statusColor(status),
                      ),
                      onPress: () => context.push('/home/queue/${o['id']}'),
                    );
                  },
                ),
        ),
      ],
    );
  }
}

class _ProfileTab extends StatefulWidget {
  const _ProfileTab({
    required this.api,
    required this.push,
    required this.session,
    required this.onSwitchMode,
    required this.onLogout,
  });

  final ApiClient api;
  final PushService push;
  final AppSession session;
  final VoidCallback onSwitchMode;
  final VoidCallback onLogout;

  @override
  State<_ProfileTab> createState() => _ProfileTabState();
}

class _ProfileTabState extends State<_ProfileTab> with WidgetsBindingObserver {
  Map<String, bool> _prefs = {};
  bool _totpEnabled = false;
  bool _ownerRequired = false;
  bool _loading2fa = false;
  List<Map<String, dynamic>> _sessions = [];
  bool _loadingSessions = false;
  String? _setupSecret;
  String? _setupChallenge;
  String? _setupUri;
  final _code = TextEditingController();
  final _oldPass = TextEditingController();
  final _newPass = TextEditingController();
  final _newPass2 = TextEditingController();
  final _fullName = TextEditingController();
  final _inn = TextEditingController();
  final _phone = TextEditingController();
  bool _changingPass = false;
  bool _deleting = false;
  List<Map<String, String>> _oauthProviders = [];
  bool _oauthLinking = false;
  List<Map<String, dynamic>> _accessLog = [];
  List<Map<String, dynamic>> _pushDevices = [];
  int? _revokingDeviceId;

  static String _prefLabel(AppLocalizations l, String key) {
    switch (key) {
      case 'push_enabled':
        return l.prefPushEnabled;
      case 'email_enabled':
        return l.prefEmailEnabled;
      case 'generation_done':
        return l.prefGenerationDone;
      case 'refund':
        return l.prefRefund;
      case 'nsfw_blocked':
        return l.prefNsfwBlocked;
      case 'source_expire':
        return l.prefSourceExpire;
      case 'cleanup':
        return l.prefCleanup;
      case 'publish_reminder':
        return l.prefPublishReminder;
      case 'topup_failed':
        return l.prefTopupFailed;
      case 'support_reply':
        return l.prefSupportReply;
      default:
        return key;
    }
  }

  static const _masterPrefKeys = ['push_enabled', 'email_enabled'];

  static const _prefKeys = [
    'generation_done',
    'refund',
    'nsfw_blocked',
    'source_expire',
    'cleanup',
    'publish_reminder',
    'topup_failed',
    'support_reply',
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    OAuthPending.instance.bind(_onOAuthPending);
    AnalyticsService.instance.track('screen_view', {'screen': 'settings'});
    _boot();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    OAuthPending.instance.unbind();
    _code.dispose();
    _oldPass.dispose();
    _newPass.dispose();
    _newPass2.dispose();
    _fullName.dispose();
    _inn.dispose();
    _phone.dispose();
    super.dispose();
  }

  Future<void> _boot() async {
    final prefs = await widget.push.loadPrefs();
    _fullName.text = widget.session.fullName ?? '';
    _inn.text = widget.session.inn ?? '';
    _phone.text = widget.session.phone ?? '';
    await ExportPrefsService.instance.load();
    try {
      final st = await widget.api.twoFaStatus();
      _totpEnabled = st['totp_enabled'] == true;
      _ownerRequired = st['owner_2fa_required'] == true;
    } catch (_) {}
    await _loadSessions();
    await _loadOAuth();
    await OAuthAuditHints.refresh(widget.api, widget.session);
    try {
      _accessLog = await widget.api.listUserAccessLog();
    } catch (_) {
      _accessLog = [];
    }
    try {
      _pushDevices = await widget.api.listUserDevices();
    } catch (_) {
      _pushDevices = [];
    }
    if (mounted) setState(() => _prefs = prefs);
  }

  Future<void> _revokePushDevice(int id) async {
    setState(() => _revokingDeviceId = id);
    try {
      await widget.api.deleteUserDevice(id);
      _pushDevices = await widget.api.listUserDevices();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Устройство отвязано')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _revokingDeviceId = null);
    }
  }

  Future<void> _refreshOAuthAuditHints() async {
    await OAuthAuditHints.refresh(widget.api, widget.session);
    if (mounted) setState(() {});
  }

  Future<void> _refreshMeOAuth() async {
    try {
      final me = await widget.api.me();
      widget.session.applyMe(me);
    } catch (_) {}
  }

  Future<void> _loadOAuth() async {
    try {
      _oauthProviders = await widget.api.listOAuthProviders();
    } catch (_) {
      _oauthProviders = [];
    }
  }

  void _onOAuthPending(String provider, String code, String state, OAuthFlow flow) {
    if (flow == OAuthFlow.link) {
      _completeOAuthLink(provider, code, state);
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _resumePendingOAuthLink();
    }
  }

  Future<void> _resumePendingOAuthLink() async {
    final pending = OAuthPending.instance;
    if (pending.pendingFlow != OAuthFlow.link) return;
    final code = pending.pendingCode;
    final st = pending.pendingState;
    final provider = pending.pendingProvider;
    if (code != null && st != null && provider != null) {
      await _completeOAuthLink(provider, code, st);
      return;
    }
    if (_oauthLinking) {
      await _loadOAuth();
      if (mounted) setState(() => _oauthLinking = false);
    }
  }

  Future<void> _completeOAuthLink(String provider, String code, String state) async {
    setState(() => _oauthLinking = true);
    try {
      await widget.api.oauthLinkComplete(provider: provider, code: code, state: state);
      AnalyticsService.instance.track('screen_view', {'screen': 'oauth_link_$provider'});
      await _refreshMeOAuth();
      await _loadOAuth();
      await _refreshOAuthAuditHints();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Соцсеть привязана')),
        );
        setState(() {});
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e))),
        );
      }
    } finally {
      OAuthPending.instance.clear();
      if (mounted) setState(() => _oauthLinking = false);
    }
  }

  Future<void> _unlinkOAuth(String provider) async {
    setState(() => _oauthLinking = true);
    try {
      await widget.api.oauthUnlink(
        provider,
        companyId: widget.session.corporate ? widget.session.companyId : null,
      );
      await _refreshMeOAuth();
      await _refreshOAuthAuditHints();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Соцсеть отвязана')),
        );
        setState(() {});
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e))),
        );
      }
    } finally {
      if (mounted) setState(() => _oauthLinking = false);
    }
  }

  Future<void> _linkOAuth(String provider) async {
    setState(() => _oauthLinking = true);
    try {
      OAuthPending.instance.start(provider, flow: OAuthFlow.link);
      final cid = widget.session.corporate ? widget.session.companyId : null;
      final url = await widget.api.oauthLinkAuthorizeUrl(provider, companyId: cid);
      final uri = Uri.parse(url);
      if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
        throw StateError('Не удалось открыть браузер');
      }
    } catch (e) {
      OAuthPending.instance.clear();
      if (mounted) {
        setState(() => _oauthLinking = false);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e))),
        );
      }
    }
  }

  Future<void> _loadSessions() async {
    setState(() => _loadingSessions = true);
    try {
      _sessions = await widget.api.listAuthSessions();
    } catch (_) {
      _sessions = [];
    } finally {
      if (mounted) setState(() => _loadingSessions = false);
    }
  }

  Future<void> _revokeSession(int sessionId) async {
    final l10n = AppLocalizations.of(context)!;
    try {
      await widget.api.revokeAuthSession(sessionId);
      await _loadSessions();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.profileSessionRevoke)),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e))),
        );
      }
    }
  }

  Future<void> _revokeOtherSessions() async {
    final l10n = AppLocalizations.of(context)!;
    try {
      final n = await widget.api.revokeOtherAuthSessions();
      await _loadSessions();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(n > 0 ? l10n.profileSessionsRevokeOthersDone : l10n.profileSessionsEmpty)),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e))),
        );
      }
    }
  }

  String _sessionWhen(String? iso) {
    final d = DateTime.tryParse(iso ?? '');
    if (d == null) return '—';
    return '${d.day.toString().padLeft(2, '0')}.${d.month.toString().padLeft(2, '0')}.${d.year}';
  }

  Future<void> _togglePref(String key, bool value) async {
    await widget.push.setPref(key, value);
    setState(() => _prefs[key] = value);
  }

  Future<void> _start2fa() async {
    setState(() => _loading2fa = true);
    try {
      final data = await widget.api.twoFaSetup();
      setState(() {
        _setupSecret = data['secret']?.toString();
        _setupChallenge = data['challenge_token']?.toString();
        _setupUri = data['otpauth_uri']?.toString();
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e))),
        );
      }
    } finally {
      if (mounted) setState(() => _loading2fa = false);
    }
  }

  Future<void> _disable2fa() async {
    final l10n = AppLocalizations.of(context)!;
    final disableCode = TextEditingController();
    final ok = await showFDialog<bool>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: Text(l10n.profileDisable2faTitle),
        body: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(l10n.profileDisable2faBody),
            const SizedBox(height: 8),
            FTextField(
              control: FTextFieldControl.managed(controller: disableCode),
              label: Text(l10n.profile2faCodeLabel),
              keyboardType: TextInputType.number,
              maxLength: 6,
            ),
          ],
        ),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
          FButton(onPress: () => Navigator.pop(ctx, true), child: Text(l10n.profileDisable2fa)),
        ],
      ),
    );
    final code = disableCode.text.trim();
    disableCode.dispose();
    if (ok != true || code.isEmpty || !mounted) return;
    setState(() => _loading2fa = true);
    try {
      await widget.api.twoFaDisable(code: code);
      if (!mounted) return;
      setState(() => _totpEnabled = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.profile2faDisabledSnackbar)),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e))),
        );
      }
    } finally {
      if (mounted) setState(() => _loading2fa = false);
    }
  }

  Future<void> _confirm2fa() async {
    setState(() => _loading2fa = true);
    try {
      await widget.api.twoFaConfirm(
        code: _code.text.trim(),
        challengeToken: _setupChallenge,
      );
      _code.clear();
      setState(() {
        _totpEnabled = true;
        _setupSecret = null;
        _setupChallenge = null;
        _setupUri = null;
        _ownerRequired = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context)!.profile2faEnabledSnackbar)),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e))),
        );
      }
    } finally {
      if (mounted) setState(() => _loading2fa = false);
    }
  }

  Future<void> _saveProfile() async {
    try {
      final me = await widget.api.updateProfile({
        'full_name': _fullName.text.trim(),
        'inn': _inn.text.trim(),
        'phone': _phone.text.trim(),
      });
      widget.session.applyMe(me);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context)!.profileSaved)),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e))),
        );
      }
    }
  }

  Future<void> _saveExportFormat(ExportFormat fmt) async {
    await ExportPrefsService.instance.setFormat(fmt);
    AnalyticsService.instance.track('screen_view', {'screen': 'export_prefs_save'});
    try {
      await widget.api.updateProfile({'export_format': fmt == ExportFormat.usdz ? 'usdz' : 'glb'});
    } catch (_) {}
    if (mounted) setState(() {});
  }

  Future<void> _changePassword() async {
    final l10n = AppLocalizations.of(context)!;
    final ok = await showFDialog<bool>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: Text(l10n.profileChangePasswordTitle),
        body: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            FTextField(
              control: FTextFieldControl.managed(controller: _oldPass),
              label: Text(l10n.profileCurrentPassword),
              obscureText: true,
            ),
            const SizedBox(height: 8),
            FTextField(
              control: FTextFieldControl.managed(controller: _newPass),
              label: Text(l10n.profileNewPassword),
              obscureText: true,
            ),
            const SizedBox(height: 8),
            FTextField(
              control: FTextFieldControl.managed(controller: _newPass2),
              label: Text(l10n.profilePasswordConfirm),
              obscureText: true,
            ),
          ],
        ),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
          FButton(onPress: () => Navigator.pop(ctx, true), child: Text(l10n.save)),
        ],
      ),
    );
    if (ok != true) return;
    if (_newPass.text.length < 8) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.profileMinPassword)),
      );
      return;
    }
    if (_newPass.text != _newPass2.text) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.profilePasswordMismatch)),
      );
      return;
    }
    setState(() => _changingPass = true);
    try {
      await widget.api.changePassword(
        oldPassword: _oldPass.text,
        newPassword: _newPass.text,
      );
      _oldPass.clear();
      _newPass.clear();
      _newPass2.clear();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.profilePasswordChanged)),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e))),
        );
      }
    } finally {
      if (mounted) setState(() => _changingPass = false);
    }
  }

  Future<void> _deleteAccount() async {
    final l10n = AppLocalizations.of(context)!;
    final ok = await showFDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx, style, animation) => FDialog(
        title: Text(l10n.profileDeleteAccountTitle),
        body: Text(l10n.profileDeleteAccountBody),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: Text(l10n.cancel)),
          FButton(
            variant: .destructive,
            onPress: () => Navigator.pop(ctx, true),
            child: Text(l10n.profileDeleteAccountBtn),
          ),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _deleting = true);
    try {
      final res = await widget.api.requestAccountDeletion();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(res['message']?.toString() ?? l10n.profileDeleteRequestAccepted)),
        );
        await widget.api.clearTokens();
        if (context.mounted) context.go('/auth');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(formatApiError(e))),
        );
      }
    } finally {
      if (mounted) setState(() => _deleting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 48, 20, 20),
      children: [
        Text(l10n.profile, style: context.theme.typography.xl),
        const SizedBox(height: 12),
        FTileGroup(
          children: [
            FTile(
              title: Text(widget.session.email ?? '—'),
              subtitle: Text(l10n.account),
            ),
            if (widget.session.isOwner && widget.session.corporate)
              FTile(
                title: Text(l10n.companyTopupTitle),
                subtitle: Text(l10n.companyTopupSubtitle),
                prefix: const Icon(FIcons.wallet),
                onPress: () => context.push('/home/company-topup'),
              ),
            if (widget.session.isOwner && widget.session.corporate)
              FTile(
                title: Text(l10n.companyPoliciesTitle),
                subtitle: Text(l10n.companyPoliciesSubtitle),
                prefix: const Icon(FIcons.shield),
                onPress: () => context.push('/home/company-policies'),
              ),
            if (!widget.session.hidePrices)
              FTile(
                title: Text(l10n.balanceLabel(
                  widget.session.balance?.toStringAsFixed(0) ?? '—',
                )),
                prefix: const Icon(FIcons.wallet),
                onPress: () => context.push('/home/balance'),
              ),
            if (widget.session.canManageTeam)
              FTile(
                title: Text(l10n.team),
                prefix: const Icon(FIcons.users),
                onPress: () => context.push('/home/team'),
              ),
            if (widget.session.isOwner)
              FTile(
                title: Text(l10n.importModel),
                subtitle: Text(l10n.importModelSub),
                prefix: const Icon(FIcons.upload),
                onPress: () => context.push('/home/import-model'),
              ),
            if (widget.session.isOwner)
              FTile(
                title: Text(l10n.apiKeysTitle),
                subtitle: Text(l10n.apiKeysSubtitle),
                prefix: const Icon(FIcons.key),
                onPress: () => context.push('/home/api-keys'),
              ),
            if (widget.session.isOwner)
              FTile(
                title: Text(l10n.publishGuideTitle),
                prefix: const Icon(FIcons.bookOpen),
                onPress: () => context.push('/home/publish-guide'),
              ),
            FTile(
              title: Text(l10n.switchMode),
              prefix: const Icon(FIcons.arrowLeftRight),
              onPress: widget.onSwitchMode,
            ),
            FTile(
              title: Text(l10n.localStorage),
              subtitle: Text(l10n.localStorageSub),
              prefix: const Icon(FIcons.hardDrive),
              onPress: () => context.push('/home/storage'),
            ),
            FTile(
              title: Text(l10n.calibration),
              subtitle: Text(l10n.calibrationSub),
              prefix: const Icon(FIcons.ruler),
              onPress: () => context.push('/home/calibration'),
            ),
          ],
        ),
        const SizedBox(height: 12),
        FTextField(
          control: FTextFieldControl.managed(controller: _fullName),
          label: Text(l10n.profileFullNameLabel),
        ),
        const SizedBox(height: 8),
        FTextField(
          control: FTextFieldControl.managed(controller: _inn),
          label: Text(l10n.profileInnLabel),
          keyboardType: TextInputType.number,
        ),
        const SizedBox(height: 8),
        FTextField(
          control: FTextFieldControl.managed(controller: _phone),
          label: Text(l10n.profilePhoneLabel),
          keyboardType: TextInputType.phone,
        ),
        const SizedBox(height: 8),
        FButton(onPress: _saveProfile, child: Text(l10n.saveProfile)),
        const SizedBox(height: 16),
        FSelect<String>(
          label: Text(l10n.profileExportFormat),
          control: FSelectControl.managed(
            initial: ExportPrefsService.instance.format == ExportFormat.usdz ? 'usdz' : 'glb',
            onChange: (v) async {
              if (v == null) return;
              await _saveExportFormat(v == 'usdz' ? ExportFormat.usdz : ExportFormat.glb);
            },
          ),
          items: {
            l10n.profileExportGlb: 'glb',
            l10n.profileExportUsdz: 'usdz',
          },
        ),
        const SizedBox(height: 8),
        FSelect<String>(
          label: Text(l10n.profileTheme),
          control: FSelectControl.managed(
            initial: switch (AppThemeController.instance.preference) {
              AppThemePreference.light => 'light',
              AppThemePreference.dark => 'dark',
              AppThemePreference.system => 'system',
            },
            onChange: (v) async {
              if (v == null) return;
              await AppThemeController.instance.setPreference(
                switch (v) {
                  'light' => AppThemePreference.light,
                  'dark' => AppThemePreference.dark,
                  _ => AppThemePreference.system,
                },
              );
              if (mounted) setState(() {});
            },
          ),
          items: {
            l10n.themeSystem: 'system',
            l10n.themeLight: 'light',
            l10n.themeDark: 'dark',
          },
        ),
        const SizedBox(height: 8),
        FSelect<String>(
          label: Text(l10n.languageInterface),
          control: FSelectControl.managed(
            initial: AppLocaleController.instance.locale.languageCode,
            onChange: (v) async {
              if (v == null) return;
              await AppLocaleController.instance.setLocale(Locale(v));
              if (mounted) setState(() {});
            },
          ),
          items: {
            l10n.langRu: 'ru',
            l10n.langEn: 'en',
            l10n.langKk: 'kk',
            l10n.langZh: 'zh',
          },
        ),
        const SizedBox(height: 16),
        Text(l10n.profileNotificationsSection, style: context.theme.typography.sm),
        const SizedBox(height: 8),
        ..._masterPrefKeys.map(
          (key) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: FSwitch(
              label: Text(_prefLabel(l10n, key)),
              value: _prefs[key] ?? true,
              onChange: (v) => _togglePref(key, v),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(l10n.profileEventsSection, style: context.theme.typography.xs.copyWith(color: AppColors.textSecondary)),
        const SizedBox(height: 8),
        ..._prefKeys.map(
          (key) {
            final channelsOn =
                (_prefs['push_enabled'] ?? true) || (_prefs['email_enabled'] ?? true);
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: FSwitch(
                label: Text(_prefLabel(l10n, key)),
                value: _prefs[key] ?? true,
                onChange: channelsOn ? (v) => _togglePref(key, v) : null,
              ),
            );
          },
        ),
        const SizedBox(height: 16),
        if (_oauthProviders.isNotEmpty) ...[
          Text('Вход через соцсети', style: context.theme.typography.sm),
          const SizedBox(height: 8),
          ..._oauthProviders.map((p) {
            final key = p['provider'] ?? '';
            final linked = widget.session.oauthProviders.contains(key);
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: FTile(
                title: Text(p['label'] ?? key),
                subtitle: linked ? const Text('Привязано', style: TextStyle(color: AppColors.success)) : null,
                suffix: _oauthLinking
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                    : linked
                        ? FButton(
                            variant: .outline,
                            onPress: () => _unlinkOAuth(key),
                            child: const Text('Отвязать'),
                          )
                        : FButton(
                            variant: .outline,
                            onPress: () => _linkOAuth(key),
                            child: const Text('Привязать'),
                          ),
              ),
            );
          }),
          if (widget.session.lastOAuthLoginHint != null) ...[
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                widget.session.lastOAuthLoginHint!,
                style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
            ),
          ],
          if (widget.session.lastOAuthLinkHint != null) ...[
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                widget.session.lastOAuthLinkHint!,
                style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
            ),
          ],
          if (widget.session.lastOAuthUnlinkHint != null) ...[
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Text(
                widget.session.lastOAuthUnlinkHint!,
                style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
              ),
            ),
          ],
          const SizedBox(height: 16),
        ],
        if (_accessLog.isNotEmpty) ...[
          Text('Скачивания моделей', style: context.theme.typography.sm),
          const SizedBox(height: 8),
          ..._accessLog.take(10).map((r) {
            final uuid = r['model_uuid']?.toString() ?? '—';
            final short = uuid.length > 8 ? '${uuid.substring(0, 8)}…' : uuid;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: FTile(
                title: Text(short),
                subtitle: Text(
                  '${r['action'] ?? '—'} · ${r['timestamp'] ?? ''}',
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            );
          }),
          const SizedBox(height: 16),
        ],
        Text(l10n.profileSecuritySection, style: context.theme.typography.sm),
        const SizedBox(height: 8),
        FTile(
          title: Text(l10n.profileChangePassword),
          prefix: const Icon(FIcons.key),
          onPress: _changingPass ? null : _changePassword,
        ),
        const SizedBox(height: 16),
        Text(l10n.profile2faSection, style: context.theme.typography.sm),
        const SizedBox(height: 8),
        Material(
          color: Theme.of(context).colorScheme.surfaceContainerHighest.withValues(alpha: 0.35),
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Icon(
                      _totpEnabled ? FIcons.shieldCheck : FIcons.shield,
                      color: _totpEnabled ? AppColors.success : AppColors.textSecondary,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _totpEnabled ? l10n.profile2faEnabled : l10n.profile2faDisabled,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
                if (_ownerRequired) ...[
                  const SizedBox(height: 8),
                  Text(
                    l10n.profile2faOwnerRequired,
                    style: const TextStyle(color: AppColors.warning, fontSize: 13),
                  ),
                ],
                if (_totpEnabled) ...[
                  const SizedBox(height: 8),
                  Text(
                    l10n.profile2faActiveHint,
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                  ),
                  if (!_ownerRequired) ...[
                    const SizedBox(height: 12),
                    FButton(
                      variant: .outline,
                      onPress: _loading2fa ? null : _disable2fa,
                      child: Text(l10n.profileDisable2fa),
                    ),
                  ],
                ] else if (_setupSecret != null) ...[
                  const SizedBox(height: 12),
                  Text(l10n.profile2faStep1),
                  const SizedBox(height: 12),
                  if (_setupUri != null)
                    Center(
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: QrImageView(data: _setupUri!, size: 200),
                      ),
                    ),
                  const SizedBox(height: 12),
                  Text(l10n.profile2faStep2),
                  const SizedBox(height: 6),
                  SelectableText(_setupSecret!, style: const TextStyle(fontSize: 12)),
                  const SizedBox(height: 8),
                  FButton(
                    variant: .outline,
                    onPress: () async {
                      await Clipboard.setData(ClipboardData(text: _setupSecret!));
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(content: Text(l10n.profileSecretCopied)),
                        );
                      }
                    },
                    child: Text(l10n.profileCopySecretBtn),
                  ),
                  const SizedBox(height: 12),
                  Text(l10n.profile2faCodeStep),
                  const SizedBox(height: 8),
                  FTextField(
                    control: FTextFieldControl.managed(controller: _code),
                    label: Text(l10n.profile2faCodeLabel),
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                  ),
                  const SizedBox(height: 8),
                  FButton(
                    onPress: _loading2fa ? null : _confirm2fa,
                    child: Text(_loading2fa ? '…' : l10n.profileConfirm2fa),
                  ),
                ] else ...[
                  const SizedBox(height: 8),
                  Text(
                    l10n.profile2faSetupHint,
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                  ),
                  const SizedBox(height: 12),
                  FButton(
                    onPress: _loading2fa ? null : _start2fa,
                    child: Text(_loading2fa ? '…' : l10n.profileEnable2fa),
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),
        Text('Push-устройства', style: context.theme.typography.sm),
        const SizedBox(height: 8),
        if (_pushDevices.isEmpty)
          Text('Нет зарегистрированных устройств', style: TextStyle(color: AppColors.textSecondary))
        else
          ..._pushDevices.take(10).map((d) {
            final id = (d['id'] as num?)?.toInt();
            final platform = d['platform']?.toString() ?? '—';
            final ver = d['app_version']?.toString();
            final prefix = d['token_prefix']?.toString() ?? '—';
            final busy = id != null && _revokingDeviceId == id;
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      '$platform${ver != null && ver.isNotEmpty ? ' · $ver' : ''} · $prefix',
                      style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                    ),
                  ),
                  if (id != null)
                    FButton(
                      variant: .outline,
                      onPress: busy ? null : () => _revokePushDevice(id),
                      child: Text(busy ? '…' : 'Отвязать'),
                    ),
                ],
              ),
            );
          }),
        const SizedBox(height: 24),
        Text(l10n.profileSessionsSection, style: context.theme.typography.sm),
        const SizedBox(height: 8),
        if (_loadingSessions)
          const Center(child: Padding(padding: EdgeInsets.all(12), child: CircularProgressIndicator()))
        else if (_sessions.isEmpty)
          Text(l10n.profileSessionsEmpty, style: TextStyle(color: AppColors.textSecondary))
        else ...[
          ..._sessions.map((s) {
            final id = (s['id'] as num?)?.toInt();
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('#${id ?? '—'}', style: context.theme.typography.sm),
                        Text(
                          '${_sessionWhen(s['created_at']?.toString())} → ${_sessionWhen(s['expires_at']?.toString())}',
                          style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  if (id != null)
                    FButton(
                      variant: .outline,
                      onPress: () => _revokeSession(id),
                      child: Text(l10n.profileSessionRevoke),
                    ),
                ],
              ),
            );
          }),
          FButton(
            variant: .outline,
            onPress: _sessions.length < 2 ? null : _revokeOtherSessions,
            child: Text(l10n.profileSessionsRevokeOthers),
          ),
        ],
        const SizedBox(height: 24),
        FButton(
          variant: .destructive,
          onPress: _deleting ? null : _deleteAccount,
          child: Text(_deleting ? '…' : l10n.profileDeleteAccount),
        ),
        const SizedBox(height: 12),
        FTile(
          title: Text(l10n.profileLogout),
          prefix: const Icon(FIcons.logOut),
          variant: .destructive,
          onPress: widget.onLogout,
        ),
      ],
    );
  }
}
