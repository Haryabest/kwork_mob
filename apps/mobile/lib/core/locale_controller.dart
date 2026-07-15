import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AppLocaleController extends ChangeNotifier {
  AppLocaleController._();
  static final instance = AppLocaleController._();

  Locale _locale = const Locale('ru');

  Locale get locale => _locale;

  static Locale _localeFromCode(String code) {
    return switch (code) {
      'en' => const Locale('en'),
      'kk' => const Locale('kk'),
      'zh' => const Locale('zh'),
      _ => const Locale('ru'),
    };
  }

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final code = prefs.getString('app_locale') ?? 'ru';
    _locale = _localeFromCode(code);
    notifyListeners();
  }

  Future<void> setLocale(Locale locale) async {
    _locale = locale;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('app_locale', locale.languageCode);
    notifyListeners();
  }
}
