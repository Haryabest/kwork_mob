import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

extension ProductCategoryL10n on ProductCategory {
  String localized(AppLocalizations l) {
    switch (this) {
      case ProductCategory.clothing:
        return l.catClothing;
      case ProductCategory.shoes:
        return l.catShoes;
      case ProductCategory.electronics:
        return l.catElectronics;
      case ProductCategory.furniture:
        return l.catFurniture;
      case ProductCategory.decor:
        return l.catDecor;
      case ProductCategory.toys:
        return l.catToys;
      case ProductCategory.adult:
        return l.catAdult;
      case ProductCategory.other:
        return l.catOther;
    }
  }
}

extension TierL10n on Tier {
  String localized(AppLocalizations l) => this == Tier.small ? l.tierSmall : l.tierLarge;
}

extension ForbiddenCategoryL10n on ForbiddenCategory {
  String localized(AppLocalizations l) {
    switch (this) {
      case ForbiddenCategory.intimate:
        return l.forbIntimate;
      case ForbiddenCategory.weapons:
        return l.forbWeapons;
      case ForbiddenCategory.drugs:
        return l.forbDrugs;
    }
  }
}

Map<String, ProductCategory> productCategorySelectItems(AppLocalizations l) => {
      for (final c in ProductCategory.values) c.localized(l): c,
    };

Map<String, Tier> tierSelectItems(AppLocalizations l) => {
      for (final t in Tier.values) t.localized(l): t,
    };
