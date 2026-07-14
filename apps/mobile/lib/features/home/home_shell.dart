import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/features/models/model_viewer_screen.dart';
import 'package:kwork_mobile/features/support/faq_support_screen.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/push_service.dart';

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

  @override
  void initState() {
    super.initState();
    widget.session.addListener(_onSession);
    _refresh();
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
    final choice = await showModalBottomSheet<Object>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: const Text('Личный'),
              selected: !session.corporate,
              onTap: () => Navigator.pop(ctx, 'personal'),
            ),
            ...session.companies.map(
              (c) => ListTile(
                title: Text(c['name']?.toString() ?? 'Компания'),
                subtitle: Text(c['role']?.toString() ?? ''),
                selected: session.corporate && session.companyId == c['id'],
                onTap: () => Navigator.pop(ctx, c),
              ),
            ),
          ],
        ),
      ),
    );
    if (choice == null) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Сменить режим?'),
        content: const Text('Подтвердите переключение Личный / Компания'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Отмена')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Подтвердить')),
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
        session: session,
        onSwitchMode: _switchMode,
        onShoot: () => context.push('/home/shoot'),
        onQueue: () => context.push('/home/queue'),
        onShootLink: session.canManageTeam
            ? () => context.push('/home/shoot-link')
            : null,
      ),
      ModelsScreen(api: widget.api),
      _OrdersTab(api: widget.api),
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

    return FScaffold(
      child: pages[_index],
      footer: FBottomNavigationBar(
        index: _index,
        onChange: (i) => setState(() => _index = i),
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
    );
  }
}

class _HomeTab extends StatelessWidget {
  const _HomeTab({
    required this.session,
    required this.onSwitchMode,
    required this.onShoot,
    required this.onQueue,
    this.onShootLink,
  });

  final AppSession session;
  final VoidCallback onSwitchMode;
  final VoidCallback onShoot;
  final VoidCallback onQueue;
  final VoidCallback? onShootLink;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final modeLabel = session.corporate
        ? (session.companyName ?? l10n.corporateMode)
        : l10n.personalMode;

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 48, 20, 100),
      children: [
        Text(l10n.appName, style: context.theme.typography.xl.copyWith(fontWeight: FontWeight.bold)),
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
          onPress: onSwitchMode,
          child: Text('Режим: $modeLabel'),
        ),
        const SizedBox(height: 24),
        FButton(
          onPress: onShoot,
          prefix: const Icon(FIcons.camera),
          child: Text(l10n.shoot),
        ),
        const SizedBox(height: 12),
        FButton(
          variant: .secondary,
          onPress: onQueue,
          prefix: const Icon(FIcons.hourglass),
          child: Text(l10n.queue),
        ),
        if (onShootLink != null) ...[
          const SizedBox(height: 12),
          FButton(
            variant: .outline,
            onPress: onShootLink,
            prefix: const Icon(FIcons.qrCode),
            child: const Text('Съёмка по ссылке (QR)'),
          ),
        ],
      ],
    );
  }
}

class _OrdersTab extends StatefulWidget {
  const _OrdersTab({required this.api});
  final ApiClient api;

  @override
  State<_OrdersTab> createState() => _OrdersTabState();
}

class _OrdersTabState extends State<_OrdersTab> {
  List<Map<String, dynamic>> _items = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      _items = await widget.api.listOrders();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_items.isEmpty) return const Center(child: Text('Нет заказов'));
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(16, 48, 16, 16),
      itemCount: _items.length,
      itemBuilder: (context, i) {
        final o = _items[i];
        return ListTile(
          title: Text('#${o['id']} · ${o['status']}'),
          subtitle: Text('${o['category']} · ${o['tier']}'),
          onTap: () => context.push('/home/queue/${o['id']}'),
        );
      },
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
  final _code = TextEditingController();

  static const _prefLabels = {
    'generation_done': 'Генерация готова',
    'refund': 'Возврат средств',
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
    super.dispose();
  }

  Future<void> _boot() async {
    final prefs = await widget.push.loadPrefs();
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

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 48, 20, 20),
      children: [
        Text(l10n.profile, style: context.theme.typography.xl),
        const SizedBox(height: 12),
        ListTile(title: Text(widget.session.email ?? '—'), subtitle: const Text('Аккаунт')),
        ListTile(
          title: const Text('Режим Личный / Компания'),
          leading: const Icon(Icons.swap_horiz),
          onTap: widget.onSwitchMode,
        ),
        const Divider(),
        Text('Уведомления (push) §3.4.3', style: context.theme.typography.sm),
        const SizedBox(height: 4),
        ..._prefLabels.entries.map(
          (e) => SwitchListTile(
            title: Text(e.value),
            value: _prefs[e.key] ?? true,
            onChanged: (v) => _togglePref(e.key, v),
          ),
        ),
        const Divider(),
        Text('Двухфакторная аутентификация', style: context.theme.typography.sm),
        if (_ownerRequired)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: Text(
              'Для Owner 2FA обязательна (§10.7.5)',
              style: TextStyle(color: AppColors.warning),
            ),
          ),
        ListTile(
          title: Text(_totpEnabled ? '2FA включена' : '2FA выключена'),
          subtitle: Text(_totpEnabled ? 'TOTP активен' : 'Google Authenticator / аналог'),
          trailing: _totpEnabled
              ? const Icon(Icons.verified_user, color: AppColors.success)
              : FButton(
                  onPress: _loading2fa ? null : _start2fa,
                  child: Text(_loading2fa ? '…' : 'Включить'),
                ),
        ),
        if (_setupSecret != null) ...[
          SelectableText('Секрет: $_setupSecret', style: const TextStyle(fontSize: 12)),
          const SizedBox(height: 8),
          TextField(
            controller: _code,
            keyboardType: TextInputType.number,
            maxLength: 6,
            decoration: const InputDecoration(
              labelText: 'Код подтверждения',
              border: OutlineInputBorder(),
              counterText: '',
            ),
          ),
          const SizedBox(height: 8),
          FButton(
            onPress: _loading2fa ? null : _confirm2fa,
            child: const Text('Подтвердить 2FA'),
          ),
        ],
        const Divider(),
        ListTile(
          title: const Text('Выйти'),
          leading: const Icon(Icons.logout),
          onTap: widget.onLogout,
        ),
      ],
    );
  }
}
