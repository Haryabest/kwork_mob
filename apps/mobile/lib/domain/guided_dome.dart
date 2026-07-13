/// Guided Dome: 12 ракурсов по ТЗ §3.1.2.
library;

class DomeAngle {
  const DomeAngle({
    required this.index,
    required this.label,
    required this.azimuthDeg,
    required this.elevationDeg,
    required this.filename,
  });

  final int index;
  final String label;
  /// Азимут вокруг товара (0 = фронт), градусы.
  final double azimuthDeg;
  /// 0 = горизонт, 45 = сверху.
  final double elevationDeg;
  final String filename;

  bool get isUpperRing => elevationDeg >= 30;
}

/// Нижнее кольцо 8 + верхнее 4 (§3.1.2). Файлы → view_00…11.jpg (API).
const List<DomeAngle> kGuidedDomeAngles = [
  DomeAngle(index: 0, label: 'Низ 0° (фронт)', azimuthDeg: 0, elevationDeg: 0, filename: 'view_00.jpg'),
  DomeAngle(index: 1, label: 'Низ 45°', azimuthDeg: 45, elevationDeg: 0, filename: 'view_01.jpg'),
  DomeAngle(index: 2, label: 'Низ 90° (лево)', azimuthDeg: 90, elevationDeg: 0, filename: 'view_02.jpg'),
  DomeAngle(index: 3, label: 'Низ 135°', azimuthDeg: 135, elevationDeg: 0, filename: 'view_03.jpg'),
  DomeAngle(index: 4, label: 'Низ 180° (тыл)', azimuthDeg: 180, elevationDeg: 0, filename: 'view_04.jpg'),
  DomeAngle(index: 5, label: 'Низ 225°', azimuthDeg: 225, elevationDeg: 0, filename: 'view_05.jpg'),
  DomeAngle(index: 6, label: 'Низ 270° (право)', azimuthDeg: 270, elevationDeg: 0, filename: 'view_06.jpg'),
  DomeAngle(index: 7, label: 'Низ 315°', azimuthDeg: 315, elevationDeg: 0, filename: 'view_07.jpg'),
  DomeAngle(index: 8, label: 'Верх вперёд 45°', azimuthDeg: 0, elevationDeg: 45, filename: 'view_08.jpg'),
  DomeAngle(index: 9, label: 'Верх вправо 45°', azimuthDeg: 90, elevationDeg: 45, filename: 'view_09.jpg'),
  DomeAngle(index: 10, label: 'Верх назад 45°', azimuthDeg: 180, elevationDeg: 45, filename: 'view_10.jpg'),
  DomeAngle(index: 11, label: 'Верх влево 45°', azimuthDeg: 270, elevationDeg: 45, filename: 'view_11.jpg'),
];

const int kGuidedDomeCount = 12;
const double kGyroToleranceDeg = 15;
const double kCenterMaxOffsetRatio = 0.15;
const double kContourMinFill = 0.60;
const double kContourMaxFill = 0.85;
const int kMaxReshootIterations = 3;
