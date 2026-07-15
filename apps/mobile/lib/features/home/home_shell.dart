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
import 'package:kwork_mobile/services/push_service.dart';
import 'package:kwork_mobile/services/export_prefs_service.dart';
import 'package:kwork_mobile/services/local_model_library.dart';
import 'package:kwork_mobile/services/notification_inbox.dart';
import 'package:kwork_mobile/services/upload_progress_service.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({
    super.key,
    required this.api,
    required this.session,
    required this.push,
  });

  final ApiClient api;
  final AppSession session;
  final PushService push;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  int _unread = 0;
  final _homeTabKey = GlobalKey<_HomeTabState>();

  @override
  void initState() {
    super.initState();
    widget.session.addListener(_onSession);
    _refresh();
    _loadUnread();
    LocalModelLibrary.instance.runAutoCleanup();
    LocalModelLibrary.instance.syncPendingDownloads(
      widget.api,
      companyId: widget.session.corporate ? widget.session.companyId : null,
    );
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
    final session = widget.session;
    if (session.companies.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Нет привязанных компаний')),
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
              title: const Text('Личный'),
              selected: !session.corporate,
              onPress: () => Navigator.pop(ctx, 'personal'),
            ),
            ...session.companies.map(
              (c) => FTile(
                title: Text(c['name']?.toString() ?? 'Компания'),
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
        title: const Text('Сменить режим?'),
        body: const Text('Подтвердите переключение Личный / Компания'),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
          FButton(onPress: () => Navigator.pop(ctx, true), child: const Text('Подтвердить')),
        ],
      ),
    );
    if (confirmed != true) return;
    if (choice == 'personal') {
      await session.setPersonal();
    } else {
      await session.setCompany(choice as Map<String, dynamic>);
    }
  }

  @override
  void dispose() {
    widget.session.removeListener(_onSession);
    super.dispose();
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
            ? () => context.push('/home/shoot-link')
            : null,
      ),
      ModelsScreen(
        api: widget.api,
        companyId: session.corporate ? session.companyId : null,
        onNotifications: () async {
          await context.push('/home/notifications');
          await _loadUnread();
        },
        unread: _unread,
      ),
      _OrdersTab(api: widget.api, session: session),
      FaqSupportScreen(api: widget.api),
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
    if (mounted) setState(() => _pendingUpload = summary);
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
                          'Незавершённая загрузка фото '
                          '(${_pendingUpload!.uploaded}/${_pendingUpload!.total})',
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
                    'Загрузка прервалась. Можно продолжить с последнего кадра.',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                  ),
                  const SizedBox(height: 10),
                  FButton(
                    onPress: () async {
                      await context.push(
                        '/home/shoot/upload',
                        extra: _pendingUpload!.modelUuid,
                      );
                      await refreshPending();
                    },
                    child: const Text('Продолжить загрузку'),
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
            'Баланс: ${session.balance!.toStringAsFixed(0)} ₽',
            style: const TextStyle(color: AppColors.ozonPrimary, fontWeight: FontWeight.w600),
          ),
        ],
        const SizedBox(height: 16),
        FButton(
          variant: .outline,
          onPress: widget.onSwitchMode,
          child: Text('Режим: $modeLabel'),
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
            child: const Text('Съёмка по ссылке (QR)'),
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

  static const _statusLabel = {
    'pending': 'Новый',
    'awaiting_payment': 'Ожидает оплаты',
    'queued': 'В очереди',
    'processing': 'В обработке',
    'completed': 'Готов',
    'failed': 'Ошибка',
    'cancelled': 'Отменён',
    'paid': 'Оплачен',
    'blocked_nsfw': 'NSFW блок',
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

  String _statusText(String? status) => _statusLabel[status ?? ''] ?? status ?? '—';

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
    if (_loading) return const Center(child: CircularProgressIndicator());
    return Column(
      children: [
        if (widget.session.canFilterCompanyOrders && _members.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 48, 16, 0),
            child: FSelect<int>(
              label: const Text('Исполнитель §3.16.2'),
              control: FSelectControl.managed(
                initial: _authorFilter,
                onChange: (v) {
                  setState(() => _authorFilter = v ?? -1);
                  _load();
                },
              ),
              items: {
                'Все сотрудники': -1,
                for (final m in _members)
                  _authorLabel(m['user_id'] as int?): m['user_id'] as int,
              },
            ),
          ),
        Expanded(
          child: _items.isEmpty
              ? const Center(child: Text('Нет заказов'))
              : ListView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                  itemCount: _items.length,
                  itemBuilder: (context, i) {
                    final o = _items[i];
                    final status = o['status']?.toString();
                    return FTile(
                      title: Text('#${o['id']} · ${_statusText(status)}'),
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

class _ProfileTabState extends State<_ProfileTab> {
  Map<String, bool> _prefs = {};
  bool _totpEnabled = false;
  bool _ownerRequired = false;
  bool _loading2fa = false;
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

  static const _masterPrefLabels = {
    'push_enabled': 'Push-уведомления',
    'email_enabled': 'Email-уведомления',
  };

  static const _prefLabels = {
    'generation_done': 'Генерация готова',
    'refund': 'Возврат средств',
    'nsfw_blocked': 'NSFW-блокировка',
    'source_expire': 'Истечение исходников',
    'cleanup': 'Очистка хранилища',
    'publish_reminder': 'Напоминание опубликовать',
  };

  @override
  void initState() {
    super.initState();
    _boot();
  }

  @override
  void dispose() {
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
    if (mounted) setState(() => _prefs = prefs);
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
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
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
          const SnackBar(content: Text('2FA включена')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
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
          const SnackBar(content: Text('Профиль сохранён')),
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
    try {
      await widget.api.updateProfile({'export_format': fmt == ExportFormat.usdz ? 'usdz' : 'glb'});
    } catch (_) {}
    if (mounted) setState(() {});
  }

  Future<void> _changePassword() async {
    final ok = await showFDialog<bool>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: const Text('Изменить пароль'),
        body: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            FTextField(
              control: FTextFieldControl.managed(controller: _oldPass),
              label: const Text('Текущий пароль'),
              obscureText: true,
            ),
            const SizedBox(height: 8),
            FTextField(
              control: FTextFieldControl.managed(controller: _newPass),
              label: const Text('Новый пароль'),
              obscureText: true,
            ),
            const SizedBox(height: 8),
            FTextField(
              control: FTextFieldControl.managed(controller: _newPass2),
              label: const Text('Подтверждение'),
              obscureText: true,
            ),
          ],
        ),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
          FButton(onPress: () => Navigator.pop(ctx, true), child: const Text('Сохранить')),
        ],
      ),
    );
    if (ok != true) return;
    if (_newPass.text.length < 8) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Минимум 8 символов')),
      );
      return;
    }
    if (_newPass.text != _newPass2.text) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Пароли не совпадают')),
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
          const SnackBar(content: Text('Пароль изменён')),
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
    final ok = await showFDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx, style, animation) => FDialog(
        title: const Text('Удалить аккаунт?'),
        body: const Text(
          'Все модели и персональные данные будут удалены в течение 30 дней (§2.8.3). '
          'Финансовые записи анонимизируются и хранятся 5 лет.',
        ),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
          FButton(
            variant: .destructive,
            onPress: () => Navigator.pop(ctx, true),
            child: const Text('Удалить'),
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
          SnackBar(content: Text(res['message']?.toString() ?? 'Запрос принят')),
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
              subtitle: const Text('Аккаунт'),
            ),
            if (widget.session.isOwner && widget.session.corporate)
              FTile(
                title: const Text('Баланс компании'),
                subtitle: const Text('Пополнение счёта · §19.14.2'),
                prefix: const Icon(FIcons.wallet),
                onPress: () => context.push('/home/company-topup'),
              ),
            if (!widget.session.hidePrices)
              FTile(
                title: Text('Баланс: ${widget.session.balance?.toStringAsFixed(0) ?? '—'} ₽'),
                prefix: const Icon(FIcons.wallet),
                onPress: () => context.push('/home/balance'),
              ),
            if (widget.session.canManageTeam)
              FTile(
                title: const Text('Команда'),
                prefix: const Icon(FIcons.users),
                onPress: () => context.push('/home/team'),
              ),
            if (widget.session.isOwner)
              FTile(
                title: const Text('Импорт модели'),
                subtitle: const Text('Готовый GLB · §6.10'),
                prefix: const Icon(FIcons.upload),
                onPress: () => context.push('/home/import-model'),
              ),
            FTile(
              title: const Text('Режим Личный / Компания'),
              prefix: const Icon(FIcons.arrowLeftRight),
              onPress: widget.onSwitchMode,
            ),
            FTile(
              title: const Text('Локальное хранилище'),
              subtitle: const Text('GLB, автоочистка, экспорт ZIP'),
              prefix: const Icon(FIcons.hardDrive),
              onPress: () => context.push('/home/storage'),
            ),
            FTile(
              title: const Text('Калибровка масштаба'),
              subtitle: const Text('Карта / A4 / QR · §3.7'),
              prefix: const Icon(FIcons.ruler),
              onPress: () => context.push('/home/calibration'),
            ),
            FTile(
              title: const Text('Язык'),
              prefix: const Icon(FIcons.languages),
            ),
          ],
        ),
        const SizedBox(height: 12),
        FTextField(
          control: FTextFieldControl.managed(controller: _fullName),
          label: const Text('ФИО (необязательно) §19.14.1'),
        ),
        const SizedBox(height: 8),
        FTextField(
          control: FTextFieldControl.managed(controller: _inn),
          label: const Text('ИНН (необязательно) §19.14.1'),
          keyboardType: TextInputType.number,
        ),
        const SizedBox(height: 8),
        FTextField(
          control: FTextFieldControl.managed(controller: _phone),
          label: const Text('Телефон (необязательно) §19.14.1'),
          keyboardType: TextInputType.phone,
        ),
        const SizedBox(height: 8),
        FButton(onPress: _saveProfile, child: const Text('Сохранить профиль')),
        const SizedBox(height: 16),
        FSelect<String>(
          label: const Text('Формат экспорта §19.14.3'),
          control: FSelectControl.managed(
            initial: ExportPrefsService.instance.format == ExportFormat.usdz ? 'usdz' : 'glb',
            onChange: (v) async {
              if (v == null) return;
              await _saveExportFormat(v == 'usdz' ? ExportFormat.usdz : ExportFormat.glb);
            },
          ),
          items: const {
            '.glb (Ozon / универсальный)': 'glb',
            '.usdz (Wildberries / AR)': 'usdz',
          },
        ),
        const SizedBox(height: 8),
        FSelect<String>(
          label: const Text('Тема оформления §19.14.3'),
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
          items: const {
            'Системная': 'system',
            'Светлая': 'light',
            'Тёмная': 'dark',
          },
        ),
        const SizedBox(height: 8),
        FSelect<String>(
          label: const Text('Язык интерфейса'),
          control: FSelectControl.managed(
            initial: AppLocaleController.instance.locale.languageCode,
            onChange: (v) async {
              if (v == null) return;
              await AppLocaleController.instance.setLocale(Locale(v));
              if (mounted) setState(() {});
            },
          ),
          items: const {
            'Русский': 'ru',
            'English': 'en',
          },
        ),
        const SizedBox(height: 16),
        Text('Уведомления §19.14.3', style: context.theme.typography.sm),
        const SizedBox(height: 8),
        ..._masterPrefLabels.entries.map(
          (e) => Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: FSwitch(
              label: Text(e.value),
              value: _prefs[e.key] ?? true,
              onChange: (v) => _togglePref(e.key, v),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text('События §3.4.3', style: context.theme.typography.xs.copyWith(color: AppColors.textSecondary)),
        const SizedBox(height: 8),
        ..._prefLabels.entries.map(
          (e) {
            final channelsOn =
                (_prefs['push_enabled'] ?? true) || (_prefs['email_enabled'] ?? true);
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: FSwitch(
                label: Text(e.value),
                value: _prefs[e.key] ?? true,
                onChange: channelsOn ? (v) => _togglePref(e.key, v) : null,
              ),
            );
          },
        ),
        const SizedBox(height: 16),
        Text('Безопасность §19.14.4', style: context.theme.typography.sm),
        const SizedBox(height: 8),
        FTile(
          title: const Text('Изменить пароль'),
          prefix: const Icon(FIcons.key),
          onPress: _changingPass ? null : _changePassword,
        ),
        const SizedBox(height: 16),
        Text('Двухфакторная аутентификация §19.14.4', style: context.theme.typography.sm),
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
                        _totpEnabled ? '2FA включена' : '2FA выключена',
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
                if (_ownerRequired) ...[
                  const SizedBox(height: 8),
                  const Text(
                    'Для Owner 2FA обязательна (§10.7.5)',
                    style: TextStyle(color: AppColors.warning, fontSize: 13),
                  ),
                ],
                if (_totpEnabled) ...[
                  const SizedBox(height: 8),
                  Text(
                    'TOTP активен — Google Authenticator, 1Password или аналог.',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                  ),
                ] else if (_setupSecret != null) ...[
                  const SizedBox(height: 12),
                  const Text('1. Отсканируйте QR в приложении-аутентификаторе'),
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
                  const Text('2. Или введите секрет вручную'),
                  const SizedBox(height: 6),
                  SelectableText(_setupSecret!, style: const TextStyle(fontSize: 12)),
                  const SizedBox(height: 8),
                  FButton(
                    variant: .outline,
                    onPress: () async {
                      await Clipboard.setData(ClipboardData(text: _setupSecret!));
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Секрет скопирован')),
                        );
                      }
                    },
                    child: const Text('Скопировать секрет'),
                  ),
                  const SizedBox(height: 12),
                  const Text('3. Введите 6-значный код'),
                  const SizedBox(height: 8),
                  FTextField(
                    control: FTextFieldControl.managed(controller: _code),
                    label: const Text('Код подтверждения'),
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                  ),
                  const SizedBox(height: 8),
                  FButton(
                    onPress: _loading2fa ? null : _confirm2fa,
                    child: Text(_loading2fa ? '…' : 'Подтвердить 2FA'),
                  ),
                ] else ...[
                  const SizedBox(height: 8),
                  Text(
                    'Защитите аккаунт одноразовыми кодами при входе.',
                    style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                  ),
                  const SizedBox(height: 12),
                  FButton(
                    onPress: _loading2fa ? null : _start2fa,
                    child: Text(_loading2fa ? '…' : 'Настроить 2FA'),
                  ),
                ],
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),
        FButton(
          variant: .destructive,
          onPress: _deleting ? null : _deleteAccount,
          child: Text(_deleting ? '…' : 'Удалить аккаунт'),
        ),
        const SizedBox(height: 12),
        FTile(
          title: const Text('Выйти'),
          prefix: const Icon(FIcons.logOut),
          variant: .destructive,
          onPress: widget.onLogout,
        ),
      ],
    );
  }
}
