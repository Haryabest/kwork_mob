import 'package:flutter_test/flutter_test.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';

void main() {
  test('Guided Dome has 12 angles per TZ §3.1.2', () {
    expect(kGuidedDomeAngles.length, 12);
    expect(kGuidedDomeAngles.where((a) => a.elevationDeg == 0).length, 8);
    expect(kGuidedDomeAngles.where((a) => a.elevationDeg == 45).length, 4);
    expect(kGuidedDomeAngles.first.filename, 'view_00.jpg');
    expect(kGuidedDomeAngles.last.filename, 'view_11.jpg');
  });

  test('gyro tolerance is ±15°', () {
    expect(kGyroToleranceDeg, 15);
  });
}
