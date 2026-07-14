import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:forui/forui.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/router.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/push_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final api = ApiClient();
  final session = AppSession();
  final push = PushService(api);
  runApp(KworkApp(api: api, session: session, push: push));
}

class KworkApp extends StatelessWidget {
  const KworkApp({
    super.key,
    required this.api,
    required this.session,
    required this.push,
  });

  final ApiClient api;
  final AppSession session;
  final PushService push;

  @override
  Widget build(BuildContext context) {
    final foruiTheme = buildForuiTheme();
    final router = createRouter(api: api, session: session, push: push);
    push.bindRouter(router);

    return MaterialApp.router(
      title: 'KWork Mob',
      theme: buildMaterialTheme(foruiTheme),
      routerConfig: router,
      locale: const Locale('ru'),
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
        data: foruiTheme,
        child: FToaster(child: child ?? const SizedBox.shrink()),
      ),
    );
  }
}
