/// Цвета по ТЗ §19: акценты Wildberries / Ozon.
library;

import 'package:flutter/material.dart';

abstract final class AppColors {
  static const wbPrimary = Color(0xFF6D3B6B);
  static const wbDark = Color(0xFF4A2A49);
  static const ozonPrimary = Color(0xFF005B9F);
  static const ozonLight = Color(0xFF0073B7);
  static const brand = Color(0xFF0B7A73);
  static const success = Color(0xFF2E7D32);
  static const error = Color(0xFFC62828);
  static const background = Color(0xFFFFFFFF);
  static const surface = Color(0xFFF5F5F5);
  static const textPrimary = Color(0xFF1A1A1A);
  static const textSecondary = Color(0xFF666666);
}

ThemeData buildAppTheme() {
  final scheme = ColorScheme.fromSeed(
    seedColor: AppColors.brand,
    primary: AppColors.brand,
    secondary: AppColors.ozonPrimary,
    surface: AppColors.surface,
    error: AppColors.error,
  );
  return ThemeData(
    colorScheme: scheme,
    useMaterial3: true,
    scaffoldBackgroundColor: AppColors.background,
    appBarTheme: const AppBarTheme(
      centerTitle: false,
      backgroundColor: AppColors.background,
      foregroundColor: AppColors.textPrimary,
      elevation: 0,
    ),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: AppColors.wbPrimary,
      foregroundColor: Colors.white,
    ),
  );
}
