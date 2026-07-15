import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/l10n/catalog_l10n.dart';
import 'package:kwork_mobile/domain/catalog.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('ProductCategory localized ru', () async {
    final l = lookupAppLocalizations(const Locale('ru'));
    expect(ProductCategory.adult.localized(l), contains('18'));
    expect(Tier.small.localized(l), isNotEmpty);
  });

  test('ProductCategory localized en', () async {
    final l = lookupAppLocalizations(const Locale('en'));
    expect(ProductCategory.furniture.localized(l).toLowerCase(), contains('furniture'));
  });
}
