import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Тёмная / светлая / системная тема §19.14.3.
enum AppThemePreference { system, light, dark }

class AppThemeController extends ChangeNotifier {
  AppThemeController._();
  static final instance = AppThemeController._();

  AppThemePreference _preference = AppThemePreference.system;

  AppThemePreference get preference => _preference;

  ThemeMode get themeMode => switch (_preference) {
        AppThemePreference.light => ThemeMode.light,
        AppThemePreference.dark => ThemeMode.dark,
        AppThemePreference.system => ThemeMode.system,
      };

  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString('app_theme') ?? 'system';
    _preference = switch (raw) {
      'light' => AppThemePreference.light,
      'dark' => AppThemePreference.dark,
      _ => AppThemePreference.system,
    };
    notifyListeners();
  }

  Future<void> setPreference(AppThemePreference value) async {
    _preference = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(
      'app_theme',
      switch (value) {
        AppThemePreference.light => 'light',
        AppThemePreference.dark => 'dark',
        AppThemePreference.system => 'system',
      },
    );
    notifyListeners();
  }
}
