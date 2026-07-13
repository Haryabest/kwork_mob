/// Категории и запрещённые — §3.5.4 / schemas.orders.
library;

enum ProductCategory {
  clothing('clothing', 'Одежда'),
  shoes('shoes', 'Обувь'),
  electronics('electronics', 'Электроника'),
  furniture('furniture', 'Мебель'),
  decor('decor', 'Декор / Интерьер'),
  toys('toys', 'Игрушки'),
  adult('adult', 'Интимные товары (18+)'),
  other('other', 'Другое');

  const ProductCategory(this.api, this.label);
  final String api;
  final String label;

  bool get requiresScaleCalibration =>
      this == ProductCategory.furniture;

  bool get requiresAgeGate => this == ProductCategory.adult;
}

enum ForbiddenCategory {
  intimate('intimate', 'Интим'),
  weapons('weapons', 'Оружие'),
  drugs('drugs', 'Наркотики');

  const ForbiddenCategory(this.api, this.label);
  final String api;
  final String label;
}

enum Tier {
  small('small', 'Малый', 2990),
  large('large', 'Крупный', 5990);

  const Tier(this.api, this.label, this.priceRub);
  final String api;
  final String label;
  final int priceRub;
}
