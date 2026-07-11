import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/router.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(KworkApp(api: ApiClient()));
}

class KworkApp extends StatelessWidget {
  const KworkApp({super.key, required this.api});

  final ApiClient api;

  @override
  Widget build(BuildContext context) {
    final router = createRouter(api);
    return MaterialApp.router(
      title: 'KWork Mob',
      theme: buildAppTheme(),
      routerConfig: router,
      locale: const Locale('ru'),
      supportedLocales: AppLocalizations.supportedLocales,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
    );
  }
}
