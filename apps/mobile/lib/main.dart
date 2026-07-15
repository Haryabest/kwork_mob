import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/locale_controller.dart';
import 'package:kwork_mobile/core/router.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/core/theme_controller.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/local_model_library.dart';
import 'package:kwork_mobile/services/push_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final api = ApiClient();
  final session = AppSession();
  final push = PushService(api);
  final scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();
  push.bindMessenger(scaffoldMessengerKey);
  push.bindNavigationGuard(() => api.hasToken);
  await AppLocaleController.instance.load();
  await AppThemeController.instance.load();
  await LocalModelLibrary.instance.loadAutoDownloadEnabled();
  runApp(KworkApp(
    api: api,
    session: session,
    push: push,
    scaffoldMessengerKey: scaffoldMessengerKey,
  ));
}

class KworkApp extends StatelessWidget {
  const KworkApp({
    super.key,
    required this.api,
    required this.session,
    required this.push,
    required this.scaffoldMessengerKey,
  });

  final ApiClient api;
  final AppSession session;
  final PushService push;
  final GlobalKey<ScaffoldMessengerState> scaffoldMessengerKey;

  @override
  Widget build(BuildContext context) {
    final locale = AppLocaleController.instance;
    final themeCtrl = AppThemeController.instance;
    final foruiLight = buildForuiTheme();
    final foruiDark = buildForuiTheme(dark: true);
    final router = createRouter(api: api, session: session, push: push);
    push.bindRouter(router);

    return ListenableBuilder(
      listenable: Listenable.merge([locale, themeCtrl]),
      builder: (context, _) {
        final foruiTheme =
            themeCtrl.themeMode == ThemeMode.dark ? foruiDark : foruiLight;
        return MaterialApp.router(
          title: 'KWork Mob',
          scaffoldMessengerKey: scaffoldMessengerKey,
          theme: buildMaterialTheme(foruiLight),
          darkTheme: buildMaterialTheme(foruiDark),
          themeMode: themeCtrl.themeMode,
          routerConfig: router,
          locale: locale.locale,
          supportedLocales: [
            ...AppLocalizations.supportedLocales,
            ...FLocalizations.supportedLocales,
          ],
          localizationsDelegates: const [
            AppLocalizations.delegate,
            ...FLocalizations.localizationsDelegates,
            GlobalMaterialLocalizations.delegate,
            GlobalWidgetsLocalizations.delegate,
            GlobalCupertinoLocalizations.delegate,
          ],
          builder: (context, child) => FTheme(
            data: Theme.of(context).brightness == Brightness.dark
                ? foruiDark
                : foruiLight,
            child: Material(
              color: Theme.of(context).colorScheme.surface,
              child: DefaultTextStyle(
                style: (Theme.of(context).brightness == Brightness.dark
                        ? foruiDark
                        : foruiLight)
                    .typography
                    .sm,
                child: FToaster(child: child ?? const SizedBox.shrink()),
              ),
            ),
          ),
        );
      },
    );
  }
}
