import 'package:flutter_test/flutter_test.dart';
import 'package:kwork_mobile/services/scale_calibration_service.dart';

void main() {
  test('card reference dimensions §3.7.2', () {
    expect(ScaleCalibrationService.cardWidthM, closeTo(0.0856, 0.0001));
    expect(ScaleCalibrationService.a4WidthM, closeTo(0.21, 0.001));
  });

  test('objectFromReference produces meters', () {
    final scale = ScaleCalibrationService.instance.objectFromReference(
      refWidthM: 0.0856,
      refHeightM: 0.054,
      objectWidthFraction: 0.5,
      objectHeightFraction: 0.3,
    );
    expect(scale['width'], isA<double>());
    expect((scale['width'] as double) > 0.1, isTrue);
  });
}
