import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';
import 'package:sensors_plus/sensors_plus.dart';

/// Ориентация телефона для Guided Dome (§3.2.2): допуск ±15°.
class GyroGuide extends ChangeNotifier {
  StreamSubscription? _accelSub;
  StreamSubscription? _magSub;

  double pitchDeg = 0;
  double rollDeg = 0;
  double yawDeg = 0;
  double? _refYaw;
  bool ready = false;

  void start() {
    _accelSub = accelerometerEventStream().listen((e) {
      // pitch: наклон вперёд/назад; roll: боковой
      pitchDeg = math.atan2(-e.x, math.sqrt(e.y * e.y + e.z * e.z)) * 180 / math.pi;
      rollDeg = math.atan2(e.y, e.z) * 180 / math.pi;
      ready = true;
      notifyListeners();
    });
    _magSub = magnetometerEventStream().listen((e) {
      yawDeg = math.atan2(e.y, e.x) * 180 / math.pi;
      notifyListeners();
    });
  }

  void stop() {
    _accelSub?.cancel();
    _magSub?.cancel();
    _accelSub = null;
    _magSub = null;
  }

  void calibrateYaw() {
    _refYaw = yawDeg;
  }

  double relativeYaw() {
    if (_refYaw == null) return 0;
    var d = yawDeg - _refYaw!;
    while (d > 180) {
      d -= 360;
    }
    while (d < -180) {
      d += 360;
    }
    return d;
  }

  /// Цель: pitch по elevation; yaw относительно калибровки = azimuth.
  ({bool ok, String? hint}) check(DomeAngle angle) {
    final targetPitch = -angle.elevationDeg; // верхнее кольцо — наклон вниз
    final pitchErr = (pitchDeg - targetPitch).abs();
    final yawErr = (relativeYaw() - angle.azimuthDeg).abs();
    final yawWrapped = math.min(yawErr, 360 - yawErr);

    if (pitchErr > kGyroToleranceDeg) {
      final dir = pitchDeg > targetPitch ? 'наклоните телефон вниз' : 'поднимите телефон';
      return (ok: false, hint: 'Поверните телефон: $dir (~${targetPitch.toStringAsFixed(0)}°)');
    }
    if (_refYaw != null && yawWrapped > kGyroToleranceDeg) {
      final delta = angle.azimuthDeg - relativeYaw();
      final dir = delta > 0 ? 'влево' : 'вправо';
      return (
        ok: false,
        hint: 'Поверните телефон примерно на ${delta.abs().toStringAsFixed(0)}° $dir',
      );
    }
    return (ok: true, hint: null);
  }

  @override
  void dispose() {
    stop();
    super.dispose();
  }
}
