import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/features/auth/auth_screen.dart';
import 'package:kwork_mobile/features/company/shoot_link_screen.dart';
import 'package:kwork_mobile/features/company/team_screen.dart';
import 'package:kwork_mobile/features/profile/company_policies_screen.dart';
import 'package:kwork_mobile/features/profile/company_topup_screen.dart';
import 'package:kwork_mobile/features/profile/balance_screen.dart';
import 'package:kwork_mobile/features/profile/storage_settings_screen.dart';
import 'package:kwork_mobile/features/home/home_shell.dart';
import 'package:kwork_mobile/features/models/import_model_screen.dart';
import 'package:kwork_mobile/features/models/model_viewer_screen.dart';
import 'package:kwork_mobile/features/models/trash_screen.dart';
import 'package:kwork_mobile/features/models/publish_guide_screen.dart';
import 'package:kwork_mobile/features/profile/api_keys_screen.dart';
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
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/l10n/catalog_l10n.dart';
import 'package:kwork_mobile/services/device_benchmark.dart';
import 'package:kwork_mobile/services/cloud_draft_backup_service.dart';
import 'package:kwork_mobile/services/export_prefs_service.dart';
import 'package:kwork_mobile/services/local_model_library.dart';
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
                  api: api,
                );
              }
              return GuidedDomeScreen(
                modelUuid: extra as String,
                flowBase: base,
                api: api,
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
        builder: (context, state) {
          final q = state.uri.queryParameters;
          final ticketId = int.tryParse(q['supportTicket'] ?? '');
          final tab = q['tab'];
          int? initialTab;
          if (tab == 'support' || ticketId != null) initialTab = 3;
          return HomeShell(
            api: api,
            session: session,
            push: push,
            initialTab: initialTab,
            initialSupportTicketId: ticketId,
          );
        },
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
                  api: api,
                );
              }
              return GuidedDomeScreen(modelUuid: extra as String, api: api);
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
            path: 'publish-guide',
            builder: (context, state) => const PublishGuideScreen(),
          ),
          GoRoute(
            path: 'api-keys',
            builder: (context, state) => ApiKeysScreen(api: api),
          ),
          GoRoute(
            path: 'balance',
            builder: (context, state) => BalanceScreen(api: api, session: session),
          ),
          GoRoute(
            path: 'company-topup',
            builder: (context, state) => CompanyTopupScreen(api: api, session: session),
          ),
          GoRoute(
            path: 'company-policies',
            builder: (context, state) => CompanyPoliciesScreen(api: api, session: session),
          ),
          GoRoute(
            path: 'support/ticket/:ticketId',
            redirect: (context, state) {
              final id = state.pathParameters['ticketId'];
              return '/home?tab=support&supportTicket=$id';
            },
          ),
          GoRoute(
            path: 'notifications',
            builder: (context, state) => NotificationsScreen(api: api, session: session),
          ),
          GoRoute(
            path: 'import-model',
            builder: (context, state) => ImportModelScreen(
              api: api,
              session: session,
            ),
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
        if (me['status']?.toString() == 'pending_type') {
          if (!mounted) return;
          context.go('/auth?mode=account-type');
          return;
        }
        await ExportPrefsService.instance.load(
          fromServer: me['export_format']?.toString(),
        );
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
      final cloudRestored = await _maybeCloudRestore();
      if (!mounted) return;
      if (cloudRestored) return;
      // §3.5.3 — auto-download GLB после потери связи
      // ignore: unawaited_futures
      LocalModelLibrary.instance.syncPendingDownloads(
        widget.api,
        companyId: widget.session.corporate ? widget.session.companyId : null,
      );
      await _goAuthenticatedHome();
    }
  }

  Future<bool> _maybeCloudRestore() async {
    try {
      if (!await CloudDraftBackupService.instance.shouldOfferRestore(widget.api)) {
        return false;
      }
    } catch (_) {
      return false;
    }
    final items = await CloudDraftBackupService.instance.listRemote(widget.api);
    if (items.isEmpty || !mounted) return false;

    final l10n = AppLocalizations.of(context)!;
    final choice = await showFDialog<String>(
      context: context,
      builder: (ctx, style, animation) => FDialog(
        title: Text(l10n.draftRestoreTitle),
        body: Text(l10n.draftRestoreBody('${items.length}')),
        actions: [
          FButton(
            variant: .outline,
            onPress: () => Navigator.pop(ctx, 'skip'),
            child: Text(l10n.skip),
          ),
          FButton(
            onPress: () => Navigator.pop(ctx, 'restore'),
            child: Text(l10n.mvRestore),
          ),
        ],
      ),
    );
    await CloudDraftBackupService.instance.markPromptDone();
    if (choice != 'restore' || !mounted) return false;

    for (final item in items) {
      final uuid = item['model_uuid']?.toString();
      if (uuid == null) continue;
      try {
        await CloudDraftBackupService.instance.restore(widget.api, uuid);
      } catch (_) {}
    }
    if (!mounted) return false;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(l10n.draftRestoredSnackbar)),
    );
    final draft = await ShootStorage.instance.loadActiveDraft();
    if (draft != null) {
      final idx = await ShootStorage.instance.resumeIndex(draft.modelUuid);
      context.go('/home/shoot/dome', extra: {'uuid': draft.modelUuid, 'reshoot': idx});
      return true;
    }
    context.go('/home');
    return true;
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
      builder: (ctx, style, animation) {
        final l10n = AppLocalizations.of(ctx)!;
        return FDialog(
          title: Text(l10n.resumeDraftTitle),
          body: Text(
            l10n.resumeDraftBody(
              draft.category.localized(l10n),
              '$count',
              '$kGuidedDomeCount',
            ),
          ),
          actions: [
            FButton(variant: .outline, onPress: () => Navigator.pop(ctx, 'discard'), child: Text(l10n.resumeDraftDiscard)),
            FButton(variant: .outline, onPress: () => Navigator.pop(ctx, 'cancel'), child: Text(l10n.cancel)),
            FButton(onPress: () => Navigator.pop(ctx, 'continue'), child: Text(l10n.resumeDraftContinue)),
          ],
        );
      },
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
