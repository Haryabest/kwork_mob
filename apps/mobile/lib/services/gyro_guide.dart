import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
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

  ({bool ok, String? hint, double deltaYawDeg}) check(DomeAngle angle, AppLocalizations l) {
    final targetPitch = -angle.elevationDeg;
    final pitchErr = (pitchDeg - targetPitch).abs();
    final rel = relativeYaw();
    final delta = angle.azimuthDeg - rel;
    final yawErr = delta.abs();
    final yawWrapped = math.min(yawErr, 360 - yawErr);

    if (pitchErr > kGyroToleranceDeg) {
      final dir = pitchDeg > targetPitch ? l.gyroTiltDown : l.gyroTiltUp;
      return (
        ok: false,
        hint: l.gyroTurnPitch(dir, targetPitch.toStringAsFixed(0)),
        deltaYawDeg: delta,
      );
    }
    if (_refYaw != null && yawWrapped > kGyroToleranceDeg) {
      final dir = delta > 0 ? l.gyroLeft : l.gyroRight;
      return (
        ok: false,
        hint: l.gyroTurnDegrees(delta.abs().toStringAsFixed(0), dir),
        deltaYawDeg: delta,
      );
    }
    return (ok: true, hint: null, deltaYawDeg: delta);
  }

  @override
  void dispose() {
    stop();
    super.dispose();
  }
}
