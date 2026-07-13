/// Поза устройства / товара в AR-пространстве (метры, радианы).
class ArPose {
  const ArPose({
    required this.yaw,
    required this.pitch,
    required this.roll,
    this.tx = 0,
    this.ty = 0,
    this.tz = 0,
    this.bboxLengthM,
    this.bboxWidthM,
    this.bboxHeightM,
  });

  final double yaw;
  final double pitch;
  final double roll;
  final double tx;
  final double ty;
  final double tz;

  /// Оценочные габариты bounding box товара (ТЗ §3 / масштаб 1:1).
  final double? bboxLengthM;
  final double? bboxWidthM;
  final double? bboxHeightM;
}

enum ArBackend { nativeArCore, nativeArKit, gyroFallback }
