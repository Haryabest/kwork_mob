import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/features/auth/auth_screen.dart';
import 'package:kwork_mobile/features/company/shoot_link_screen.dart';
import 'package:kwork_mobile/features/company/team_screen.dart';
import 'package:kwork_mobile/features/profile/balance_screen.dart';
import 'package:kwork_mobile/features/profile/storage_settings_screen.dart';
import 'package:kwork_mobile/features/home/home_shell.dart';
import 'package:kwork_mobile/features/models/model_viewer_screen.dart';
import 'package:kwork_mobile/features/models/trash_screen.dart';
import 'package:kwork_mobile/features/onboarding/onboarding_screen.dart';
import 'package:kwork_mobile/features/legal/consent_gate_screen.dart';
import 'package:kwork_mobile/features/queue/queue_screen.dart';
import 'package:kwork_mobile/features/shoot/category_screen.dart';
import 'package:kwork_mobile/features/shoot/guided_dome_screen.dart';
import 'package:kwork_mobile/features/shoot/guest_shoot_screen.dart';
import 'package:kwork_mobile/features/shoot/quality_review_screen.dart';
import 'package:kwork_mobile/features/shoot/upload_checkout_screen.dart';
import 'package:kwork_mobile/features/shoot/order_checkout_screen.dart';
import 'package:kwork_mobile/features/calibration/calibration_wizard_screen.dart';
import 'package:kwork_mobile/features/notifications/notifications_screen.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';
import 'package:kwork_mobile/services/device_benchmark.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';
import 'package:kwork_mobile/services/push_service.dart';
import 'package:shared_preferences/shared_preferences.dart';

GoRouter createRouter({
  required ApiClient api,
  required AppSession session,
  required PushService push,
}) {
  return GoRouter(
    initialLocation: '/splash',
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => _SplashScreen(api: api, session: session, push: push),
      ),
      GoRoute(
        path: '/onboarding',
        builder: (context, state) => const OnboardingScreen(),
      ),
      GoRoute(
        path: '/auth',
        builder: (context, state) => AuthScreen(
          api: api,
          session: session,
          push: push,
          initialMode: state.uri.queryParameters['mode'],
        ),
      ),
      GoRoute(
        path: '/legal/consent',
        builder: (context, state) => LegalConsentGateScreen(api: api),
      ),
      // §3.15 Deep link: https://…/shoot/{token} или kworkmob://open/shoot/{token}
      GoRoute(
        path: '/shoot/:token',
        builder: (context, state) => GuestShootGateScreen(
          api: api,
          token: state.pathParameters['token']!,
        ),
        routes: [
          GoRoute(
            path: 'dome',
            builder: (context, state) {
              final token = state.pathParameters['token']!;
              final base = '/shoot/$token';
              final extra = state.extra;
              if (extra is Map) {
                return GuidedDomeScreen(
                  modelUuid: extra['uuid'] as String,
                  reshootIndex: extra['reshoot'] as int?,
                  flowBase: base,
                );
              }
              return GuidedDomeScreen(
                modelUuid: extra as String,
                flowBase: base,
              );
            },
          ),
          GoRoute(
            path: 'review',
            builder: (context, state) {
              final token = state.pathParameters['token']!;
              return QualityReviewScreen(
                modelUuid: state.extra as String,
                flowBase: '/shoot/$token',
              );
            },
          ),
          GoRoute(
            path: 'upload',
            builder: (context, state) {
              final token = state.pathParameters['token']!;
              return GuestShootUploadScreen(
                api: api,
                token: token,
                modelUuid: state.extra as String,
              );
            },
          ),
        ],
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => HomeShell(
          api: api,
          session: session,
          push: push,
        ),
        routes: [
          GoRoute(
            path: 'shoot',
            builder: (context, state) => CategoryScreen(api: api, session: session),
          ),
          GoRoute(
            path: 'shoot/dome',
            builder: (context, state) {
              final extra = state.extra;
              if (extra is Map) {
                return GuidedDomeScreen(
                  modelUuid: extra['uuid'] as String,
                  reshootIndex: extra['reshoot'] as int?,
                );
              }
              return GuidedDomeScreen(modelUuid: extra as String);
            },
          ),
          GoRoute(
            path: 'shoot/review',
            builder: (context, state) =>
                QualityReviewScreen(modelUuid: state.extra as String),
          ),
          GoRoute(
            path: 'shoot/upload',
            builder: (context, state) => UploadCheckoutScreen(
              api: api,
              session: session,
              modelUuid: state.extra as String,
            ),
          ),
          GoRoute(
            path: 'shoot/checkout',
            builder: (context, state) => OrderCheckoutScreen(
              api: api,
              session: session,
              modelUuid: state.extra as String,
            ),
          ),
          GoRoute(
            path: 'calibration',
            builder: (context, state) => CalibrationWizardScreen(
              returnTo: state.extra as String?,
            ),
          ),
          GoRoute(
            path: 'shoot-link',
            builder: (context, state) => ShootLinkScreen(api: api, session: session),
          ),
          GoRoute(
            path: 'queue',
            builder: (context, state) =>
                QueueScreen(api: api, session: session),
          ),
          GoRoute(
            path: 'queue/:orderId',
            builder: (context, state) => QueueScreen(
              api: api,
              session: session,
              orderId: int.parse(state.pathParameters['orderId']!),
            ),
          ),
          GoRoute(
            path: 'models/trash',
            builder: (context, state) => ModelsTrashScreen(api: api),
          ),
          GoRoute(
            path: 'balance',
            builder: (context, state) => BalanceScreen(api: api, session: session),
          ),
          GoRoute(
            path: 'notifications',
            builder: (context, state) => NotificationsScreen(api: api),
          ),
          GoRoute(
            path: 'team',
            builder: (context, state) => TeamScreen(api: api, session: session),
          ),
          GoRoute(
            path: 'storage',
            builder: (context, state) => StorageSettingsScreen(api: api),
          ),
          GoRoute(
            path: 'models/:uuid',
            builder: (context, state) => ModelViewerScreen(
              api: api,
              modelUuid: state.pathParameters['uuid']!,
              model: state.extra is Map
                  ? Map<String, dynamic>.from(state.extra! as Map)
                  : null,
            ),
          ),
        ],
      ),
    ],
  );
}

class _SplashScreen extends StatefulWidget {
  const _SplashScreen({
    required this.api,
    required this.session,
    required this.push,
  });

  final ApiClient api;
  final AppSession session;
  final PushService push;

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
    await widget.session.loadPersisted();
    final prefs = await SharedPreferences.getInstance();
    final onboarded = prefs.getBool('onboarded') ?? false;
    final loggedIn = await widget.api.hasToken;

    // §3.8: бенчмарк при первом запуске (фон)
    try {
      final bench = DeviceBenchmark.instance;
      await bench.loadPersisted();
      if (await bench.needsRun) {
        // ignore: unawaited_futures
        bench.run();
      }
    } catch (_) {}

    if (loggedIn) {
      try {
        final me = await widget.api.me();
        widget.session.applyMe(me);
        await widget.session.setCompanies(await widget.api.myCompanies());
        await widget.push.init();
      } catch (_) {}
    }
    if (!mounted) return;
    if (!onboarded) {
      context.go('/onboarding');
    } else if (!loggedIn) {
      context.go('/auth');
    } else {
      // §2.8.2: блок до принятия новых версий
      try {
        final pending = await widget.api.legalPending();
        if (!mounted) return;
        if (pending.isNotEmpty) {
          context.go('/legal/consent');
          return;
        }
      } catch (_) {}
      if (!mounted) return;
      final resumed = await _maybeResumeDraft();
      if (!mounted) return;
      if (resumed) return;
      await _goAuthenticatedHome();
    }
  }

  Future<void> _goAuthenticatedHome() async {
    if (!mounted) return;
    if (await widget.push.applyPendingRoute(GoRouter.of(context))) return;
    context.go('/home');
  }

  Future<bool> _maybeResumeDraft() async {
    if (!await ShootStorage.instance.hasResumableDraft()) return false;
    final draft = await ShootStorage.instance.loadActiveDraft();
    if (draft == null || !mounted) return false;
    final count = await ShootStorage.instance.capturedCount(draft.modelUuid);
    final choice = await showFDialog<String>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: const Text('Незавершённая съёмка'),
        body: Text(
          'У вас есть черновик (${draft.category.label}, $count/$kGuidedDomeCount кадров). '
          'Продолжить или начать заново?',
        ),
        actions: [
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, 'discard'), child: const Text('Заново')),
          FButton(variant: .outline, onPress: () => Navigator.pop(ctx, 'cancel'), child: const Text('Отмена')),
          FButton(onPress: () => Navigator.pop(ctx, 'continue'), child: const Text('Продолжить')),
        ],
      ),
    );
    if (!mounted || choice == null || choice == 'cancel') {
      context.go('/home');
      return true;
    }
    if (choice == 'discard') {
      await ShootStorage.instance.discardDraft(draft.modelUuid);
      if (mounted) context.go('/home');
      return true;
    }
    final idx = await ShootStorage.instance.resumeIndex(draft.modelUuid);
    if (!mounted) return true;
    context.go('/home/shoot/dome', extra: {'uuid': draft.modelUuid, 'reshoot': idx});
    return true;
  }

  @override
  Widget build(BuildContext context) {
    return const FScaffold(
      child: Center(child: CircularProgressIndicator()),
    );
  }
}
