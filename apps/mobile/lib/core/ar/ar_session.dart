import 'package:flutter/foundation.dart';
import 'package:kwork_mobile/core/ar/ar_pose.dart';

/// Единый контракт AR-сессии для Guided Dome (§3.1.1).
abstract class ArSession extends ChangeNotifier {
  ArBackend get backend;
  bool get isAvailable;
  ArPose? get pose;

  Future<bool> start();
  Future<void> stop();
  void calibrate();

  /// Угол цели ракурса (градусы yaw/pitch) → попадание в допуск ±15°.
  bool isAligned({
    required double targetYawDeg,
    required double targetPitchDeg,
    double toleranceDeg = 15,
  });
}
