import 'package:flutter_test/flutter_test.dart';
import 'package:kwork_mobile/core/theme.dart';

void main() {
  test('theme builds', () {
    final theme = buildAppTheme();
    expect(theme.useMaterial3, isTrue);
    expect(theme.colorScheme.primary, AppColors.brand);
  });
}
