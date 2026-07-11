import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key, required this.api});

  final ApiClient api;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  bool _corporate = false;
  String? _email;

  @override
  void initState() {
    super.initState();
    widget.api.me().then((me) {
      if (mounted) setState(() => _email = me['email']?.toString());
    }).catchError((_) {});
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final pages = [
      _HomeTab(
        email: _email,
        corporate: _corporate,
        onToggleMode: (v) => setState(() => _corporate = v),
        onShoot: () => context.push('/home/shoot'),
      ),
      const _Stub(icon: Icons.view_in_ar_outlined),
      const _Stub(icon: Icons.receipt_long_outlined),
      const _Stub(icon: Icons.support_agent_outlined),
      _ProfileTab(
        email: _email,
        onLogout: () async {
          await widget.api.clearTokens();
          if (context.mounted) context.go('/auth');
        },
      ),
    ];

    return Scaffold(
      body: pages[_index],
      floatingActionButton: _index == 0
          ? FloatingActionButton.extended(
              onPressed: () => context.push('/home/shoot'),
              icon: const Icon(Icons.camera_alt),
              label: Text(l10n.shoot),
            )
          : null,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          NavigationDestination(icon: const Icon(Icons.home_outlined), label: l10n.home),
          NavigationDestination(icon: const Icon(Icons.view_in_ar_outlined), label: l10n.models),
          NavigationDestination(icon: const Icon(Icons.receipt_long_outlined), label: l10n.orders),
          NavigationDestination(icon: const Icon(Icons.support_agent_outlined), label: l10n.support),
          NavigationDestination(icon: const Icon(Icons.person_outline), label: l10n.profile),
        ],
      ),
    );
  }
}

class _HomeTab extends StatelessWidget {
  const _HomeTab({
    required this.email,
    required this.corporate,
    required this.onToggleMode,
    required this.onShoot,
  });

  final String? email;
  final bool corporate;
  final ValueChanged<bool> onToggleMode;
  final VoidCallback onShoot;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(l10n.appName, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 4),
          Text(email ?? '…', style: TextStyle(color: AppColors.textSecondary)),
          const SizedBox(height: 16),
          SegmentedButton<bool>(
            segments: [
              ButtonSegment(value: false, label: Text(l10n.personalMode)),
              ButtonSegment(value: true, label: Text(l10n.corporateMode)),
            ],
            selected: {corporate},
            onSelectionChanged: (s) => onToggleMode(s.first),
          ),
          const SizedBox(height: 24),
          Card(
            child: ListTile(
              leading: const Icon(Icons.camera_alt, color: AppColors.wbPrimary),
              title: Text(l10n.shoot),
              subtitle: const Text('12 ракурсов · серверное удаление фона'),
              onTap: onShoot,
            ),
          ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.hourglass_top, color: AppColors.ozonPrimary),
              title: Text(l10n.queue),
              subtitle: Text(l10n.comingSoon),
              onTap: () => context.push('/home/queue'),
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileTab extends StatelessWidget {
  const _ProfileTab({required this.email, required this.onLogout});

  final String? email;
  final VoidCallback onLogout;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(l10n.profile, style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 12),
          ListTile(title: Text(email ?? '—'), subtitle: const Text('Аккаунт')),
          ListTile(
            title: const Text('Выйти'),
            leading: const Icon(Icons.logout),
            onTap: onLogout,
          ),
        ],
      ),
    );
  }
}

class _Stub extends StatelessWidget {
  const _Stub({required this.icon});
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 48, color: AppColors.textSecondary),
          const SizedBox(height: 12),
          Text(l10n.comingSoon),
        ],
      ),
    );
  }
}
