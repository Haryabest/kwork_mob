import 'dart:math' as math;

import 'package:kwork_mobile/core/ar/ar_pose.dart';
import 'package:kwork_mobile/core/ar/ar_session.dart';
import 'package:kwork_mobile/services/gyro_guide.dart';

/// Gyro-fallback AR (§3.1.1): устройства без ARKit/ARCore или по предпочтению.
class GyroArSession extends ArSession {
  GyroArSession({GyroGuide? guide}) : _gyro = guide ?? GyroGuide();

  final GyroGuide _gyro;

  @override
  ArBackend get backend => ArBackend.gyroFallback;

  @override
  bool get isAvailable => true;

  @override
  ArPose? get pose {
    if (!_gyro.ready) return null;
    return ArPose(
      yaw: _gyro.relativeYaw() * math.pi / 180,
      pitch: _gyro.pitchDeg * math.pi / 180,
      roll: _gyro.rollDeg * math.pi / 180,
    );
  }

  GyroGuide get guide => _gyro;

  @override
  Future<bool> start() async {
    _gyro.start();
    _gyro.addListener(notifyListeners);
    _gyro.calibrateYaw();
    return true;
  }

  @override
  Future<void> stop() async {
    _gyro.removeListener(notifyListeners);
    _gyro.stop();
  }

  @override
  void calibrate() => _gyro.calibrateYaw();

  @override
  bool isAligned({
    required double targetYawDeg,
    required double targetPitchDeg,
    double toleranceDeg = 15,
  }) {
    final pitchErr = (_gyro.pitchDeg - targetPitchDeg).abs();
    final yawErr = (_gyro.relativeYaw() - targetYawDeg).abs();
    final yawWrapped = math.min(yawErr, 360 - yawErr);
    return pitchErr <= toleranceDeg && yawWrapped <= toleranceDeg;
  }

  @override
  void dispose() {
    stop();
    _gyro.dispose();
    super.dispose();
  }
}
