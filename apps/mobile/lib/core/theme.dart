/// Цвета §19.1 + Forui-тема.
library;

import 'package:flutter/material.dart';
import 'package:forui/forui.dart';

abstract final class AppColors {
  static const wbPrimary = Color(0xFF6D3B6B);
  static const wbDark = Color(0xFF4A2A49);
  static const ozonPrimary = Color(0xFF005B9F);
  static const ozonLight = Color(0xFF0073B7);
  static const brand = Color(0xFF0B7A73);
  static const success = Color(0xFF2E7D32);
  static const error = Color(0xFFC62828);
  static const warning = Color(0xFFF9A825);
  static const background = Color(0xFFFFFFFF);
  static const surface = Color(0xFFF5F5F5);
  static const textPrimary = Color(0xFF1A1A1A);
  static const textSecondary = Color(0xFF666666);
}

FThemeData buildForuiTheme() {
  final base = FThemes.neutral.light.touch;
  return base.copyWith(
    colors: base.colors.copyWith(
      primary: AppColors.wbPrimary,
      primaryForeground: const Color(0xFFFFFFFF),
      secondary: AppColors.ozonPrimary,
      secondaryForeground: const Color(0xFFFFFFFF),
      destructive: AppColors.error,
      background: AppColors.background,
      foreground: AppColors.textPrimary,
      muted: AppColors.surface,
      mutedForeground: AppColors.textSecondary,
    ),
  );
}

ThemeData buildMaterialTheme(FThemeData forui) {
  return forui.toApproximateMaterialTheme().copyWith(
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: AppColors.wbPrimary,
      foregroundColor: Colors.white,
    ),
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.wbPrimary,
      primary: AppColors.wbPrimary,
      secondary: AppColors.ozonPrimary,
      error: AppColors.error,
      surface: AppColors.surface,
    ),
  );
}
