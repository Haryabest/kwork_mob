import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
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

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final pages = [l10n.onboarding1, l10n.onboarding2, l10n.onboarding3, l10n.onboarding4];

    return FScaffold(
      child: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: pages.length,
                onPageChanged: (i) => setState(() => _page = i),
                itemBuilder: (_, i) => Padding(
                  padding: const EdgeInsets.all(32),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text('${i + 1} / ${pages.length}', style: context.theme.typography.sm),
                      const SizedBox(height: 24),
                      Text(
                        pages[i],
                        textAlign: TextAlign.center,
                        style: context.theme.typography.xl,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(24),
              child: FButton(
                onPress: () async {
                  if (_page < pages.length - 1) {
                    _controller.nextPage(
                      duration: const Duration(milliseconds: 250),
                      curve: Curves.easeOut,
                    );
                    return;
                  }
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.setBool('onboarded', true);
                  if (context.mounted) context.go('/auth');
                },
                child: Text(l10n.continueBtn),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
