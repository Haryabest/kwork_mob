import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/features/auth/auth_screen.dart';
import 'package:kwork_mobile/features/home/home_shell.dart';
import 'package:kwork_mobile/features/onboarding/onboarding_screen.dart';
import 'package:kwork_mobile/features/placeholder/placeholder_screen.dart';
import 'package:kwork_mobile/features/shoot/category_screen.dart';
import 'package:shared_preferences/shared_preferences.dart';

GoRouter createRouter(ApiClient api) {
  return GoRouter(
    initialLocation: '/splash',
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => _SplashScreen(api: api),
      ),
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: '/auth',
        builder: (context, state) => AuthScreen(api: api),
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => HomeShell(api: api),
        routes: [
          GoRoute(
            path: 'shoot',
            builder: (context, state) => const CategoryScreen(),
          ),
          GoRoute(
            path: 'queue',
            builder: (context, state) => const PlaceholderScreen(titleKey: 'queue'),
          ),
          GoRoute(
            path: 'orders',
            builder: (context, state) => const PlaceholderScreen(titleKey: 'orders'),
          ),
          GoRoute(
            path: 'support',
            builder: (context, state) => const PlaceholderScreen(titleKey: 'support'),
          ),
          GoRoute(
            path: 'profile',
            builder: (context, state) => const PlaceholderScreen(titleKey: 'profile'),
          ),
        ],
      ),
    ],
  );
}

class _SplashScreen extends StatefulWidget {
  const _SplashScreen({required this.api});
  final ApiClient api;

  @override
  State<_SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<_SplashScreen> {
  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    final prefs = await SharedPreferences.getInstance();
    final onboarded = prefs.getBool('onboarded') ?? false;
    final loggedIn = await widget.api.hasToken;
    if (!mounted) return;
    if (!onboarded) {
      context.go('/onboarding');
    } else if (!loggedIn) {
      context.go('/auth');
    } else {
      context.go('/home');
    }
  }

  @override
  Widget build(BuildContext context) {
    return const Scaffold(body: Center(child: CircularProgressIndicator()));
  }
}
