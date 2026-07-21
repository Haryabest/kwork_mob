/// Цвета §19.1 + бренд 3dvektor + Forui-тема.
library;

import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:forui/forui.dart';

/// SF Pro Text — iOS системный, Android через fontresoft.
abstract final class AppFonts {
  static String get family {
    if (!kIsWeb && Platform.isIOS) return '.SF Pro Text';
    return 'SFProText';
  }
}

abstract final class AppColors {
  /// Акцент 3dvektor — глубокий синий.
  static const accent = Color(0xFF0057B8);
  static const accentBright = Color(0xFF0381E9);
  static const accentLight = Color(0xFF00ADFE);
  static const accentPurple = Color(0xFF9403FD);

  static const accentGradient = LinearGradient(
    colors: [accent, accentBright],
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
  );

  static const accentGradientWide = LinearGradient(
    colors: [accent, accentPurple],
    begin: Alignment.centerLeft,
    end: Alignment.centerRight,
  );

  /// Wildberries / FAB §19.1.2
  static const wbPrimary = Color(0xFF6D3B6B);
  static const wbLight = Color(0xFF8B4F89);

  /// Ozon / вторичный.
  static const ozonPrimary = Color(0xFF005B9F);
  static const ozonLight = Color(0xFF0073B7);

  static const brand = Color(0xFF0B7A73);
  static const success = Color(0xFF2E7D32);
  static const error = Color(0xFFC62828);
  static const warning = Color(0xFFF9A825);
  static const background = Color(0xFFFFFFFF);
  static const surface = Color(0xFFF9FAFB);
  static const textPrimary = Color(0xFF374151);
  static const textSecondary = Color(0xFF6D6C77);

  /// §19.1 тёмная тема
  static const backgroundDark = Color(0xFF121212);
  static const surfaceDark = Color(0xFF1E1E1E);
  static const textPrimaryDark = Color(0xFFE0E0E0);
  static const textSecondaryDark = Color(0xFF9E9E9E);
}

FThemeData buildForuiTheme({bool dark = false}) {
  final base = dark ? FThemes.neutral.dark.touch : FThemes.neutral.light.touch;
  final colors = base.colors.copyWith(
    primary: AppColors.accent,
    primaryForeground: const Color(0xFFFFFFFF),
    secondary: AppColors.accentBright,
    secondaryForeground: const Color(0xFFFFFFFF),
    destructive: AppColors.error,
    background: dark ? AppColors.backgroundDark : AppColors.background,
    foreground: dark ? AppColors.textPrimaryDark : AppColors.textPrimary,
    muted: dark ? AppColors.surfaceDark : AppColors.surface,
    mutedForeground: dark ? AppColors.textSecondaryDark : AppColors.textSecondary,
  );
  final typography = FTypography.inherit(
    colors: colors,
    touch: true,
    defaultFontFamily: AppFonts.family,
  );
  final tabsStyle = FTabsStyle.inherit(
    colors: colors,
    typography: typography,
    style: base.style,
  ).copyWith(
    indicatorDecoration: DecorationDelta.value(
      ShapeDecoration(
        shape: RoundedSuperellipseBorder(borderRadius: base.style.borderRadius.md),
        gradient: AppColors.accentGradient,
      ),
    ),
    labelTextStyle: FVariants.from(
      typography.sm.copyWith(
        fontWeight: FontWeight.w500,
        fontFamily: AppFonts.family,
        color: colors.mutedForeground,
      ),
      variants: {
        [FTabVariant.selected]: TextStyleDelta.delta(color: colors.primaryForeground),
      },
    ),
  );
  return base.copyWith(
    colors: colors,
    typography: typography,
    tabsStyle: tabsStyle,
  );
}

ThemeData buildMaterialTheme(FThemeData forui) {
  final material = forui.toApproximateMaterialTheme();
  return material.copyWith(
    textTheme: material.textTheme.apply(fontFamily: AppFonts.family),
    primaryTextTheme: material.primaryTextTheme.apply(fontFamily: AppFonts.family),
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: AppColors.wbPrimary,
      foregroundColor: Colors.white,
    ),
    colorScheme: ColorScheme.fromSeed(
      seedColor: AppColors.accent,
      primary: AppColors.accent,
      secondary: AppColors.accentBright,
      error: AppColors.error,
      surface: AppColors.surface,
    ),
  );
}
