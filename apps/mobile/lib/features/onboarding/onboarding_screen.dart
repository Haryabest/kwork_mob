import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:shared_preferences/shared_preferences.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _controller = PageController();
  int _page = 0;

  Future<void> _finish({bool register = false}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('onboarded', true);
    if (!mounted) return;
    context.go(register ? '/auth?mode=register' : '/auth');
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final pages = <_OnboardPage>[
      _OnboardPage(
        title: l10n.onboarding1,
        subtitle: l10n.onboardingSub1,
        icon: Icons.view_in_ar,
      ),
      _OnboardPage(
        title: l10n.onboarding2,
        subtitle: l10n.onboardingSub2,
        icon: Icons.threed_rotation,
      ),
      _OnboardPage(
        title: l10n.onboarding3,
        subtitle: l10n.onboardingSub3,
        icon: Icons.storefront,
      ),
      _OnboardPage(
        title: l10n.onboarding4,
        subtitle: l10n.onboardingSub4,
        icon: Icons.device_thermostat,
      ),
    ];
    final last = _page >= pages.length - 1;

    return FScaffold(
      child: SafeArea(
        child: Column(
          children: [
            Align(
              alignment: Alignment.centerRight,
              child: FButton(
                variant: .ghost,
                onPress: () => _finish(),
                child: Text(l10n.skip),
              ),
            ),
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: pages.length,
                onPageChanged: (i) => setState(() => _page = i),
                itemBuilder: (_, i) {
                  final p = pages[i];
                  return Padding(
                    padding: const EdgeInsets.all(32),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(p.icon, size: 72, color: AppColors.wbPrimary),
                        const SizedBox(height: 16),
                        Text(
                          '${i + 1} / ${pages.length}',
                          style: context.theme.typography.sm,
                        ),
                        const SizedBox(height: 24),
                        Text(
                          p.title,
                          textAlign: TextAlign.center,
                          style: context.theme.typography.xl,
                        ),
                        const SizedBox(height: 12),
                        Text(
                          p.subtitle,
                          textAlign: TextAlign.center,
                          style: context.theme.typography.sm.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(
                pages.length,
                (i) => Container(
                  width: 8,
                  height: 8,
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: i == _page ? AppColors.wbPrimary : AppColors.surface,
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  FButton(
                    onPress: () async {
                      if (!last) {
                        _controller.nextPage(
                          duration: const Duration(milliseconds: 250),
                          curve: Curves.easeOut,
                        );
                        return;
                      }
                      await _finish(register: true);
                    },
                    child: Text(last ? l10n.register : l10n.continueBtn),
                  ),
                  if (last) ...[
                    const SizedBox(height: 8),
                    FButton(
                      variant: .ghost,
                      onPress: () => _finish(),
                      child: Text(l10n.alreadyHaveAccount),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OnboardPage {
  const _OnboardPage({
    required this.title,
    required this.subtitle,
    required this.icon,
  });
  final String title;
  final String subtitle;
  final IconData icon;
}
