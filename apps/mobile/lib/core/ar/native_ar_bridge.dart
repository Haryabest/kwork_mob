import 'dart:async';
import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:kwork_mobile/core/ar/ar_pose.dart';
import 'package:kwork_mobile/core/ar/ar_session.dart';
import 'package:kwork_mobile/core/ar/gyro_ar_session.dart';

/// MethodChannel-мост к нативному ARKit (iOS) / ARCore (Android).
///
/// Нативный код подключается в android/ios; до готовности [isAvailable]=false
/// и [ArSessionFactory] выбирает gyro-fallback (ТЗ §3.1.1).
class NativeArBridge extends ArSession {
  NativeArBridge() : _channel = const MethodChannel('com.kwork.mob/ar');

  final MethodChannel _channel;
  ArPose? _pose;
  bool _available = false;
  bool _started = false;
  StreamSubscription? _eventSub;

  static const _events = EventChannel('com.kwork.mob/ar_events');

  @override
  ArBackend get backend =>
      Platform.isIOS ? ArBackend.nativeArKit : ArBackend.nativeArCore;

  @override
  bool get isAvailable => _available;

  @override
  ArPose? get pose => _pose;

  Future<bool> probe() async {
    try {
      final ok = await _channel.invokeMethod<bool>('isSupported');
      _available = ok == true;
    } on MissingPluginException {
      _available = false;
    } catch (e) {
      debugPrint('NativeArBridge.probe: $e');
      _available = false;
    }
    return _available;
  }

  @override
  Future<bool> start() async {
    if (!_available && !await probe()) return false;
    try {
      await _channel.invokeMethod('startSession');
      _eventSub = _events.receiveBroadcastStream().listen(_onEvent);
      _started = true;
      return true;
    } catch (e) {
      debugPrint('NativeArBridge.start: $e');
      _started = false;
      return false;
    }
  }

  void _onEvent(dynamic raw) {
    if (raw is! Map) return;
    final m = Map<String, dynamic>.from(raw);
    _pose = ArPose(
      yaw: (m['yaw'] as num?)?.toDouble() ?? 0,
      pitch: (m['pitch'] as num?)?.toDouble() ?? 0,
      roll: (m['roll'] as num?)?.toDouble() ?? 0,
      tx: (m['tx'] as num?)?.toDouble() ?? 0,
      ty: (m['ty'] as num?)?.toDouble() ?? 0,
      tz: (m['tz'] as num?)?.toDouble() ?? 0,
      bboxLengthM: (m['bboxLengthM'] as num?)?.toDouble(),
      bboxWidthM: (m['bboxWidthM'] as num?)?.toDouble(),
      bboxHeightM: (m['bboxHeightM'] as num?)?.toDouble(),
    );
    notifyListeners();
  }

  @override
  Future<void> stop() async {
    await _eventSub?.cancel();
    _eventSub = null;
    if (_started) {
      try {
        await _channel.invokeMethod('stopSession');
      } catch (_) {}
    }
    _started = false;
  }

  /// Показать AR-метку ракурса в нативной сцене (§3.1.2).
  Future<void> showMarker({
    required int index,
    required double azimuthDeg,
    required double elevationDeg,
  }) async {
    if (!_started) return;
    try {
      await _channel.invokeMethod('showMarker', {
        'index': index,
        'azimuthDeg': azimuthDeg,
        'elevationDeg': elevationDeg,
      });
    } catch (_) {}
  }

  @override
  void calibrate() {
    _channel.invokeMethod('calibrate').catchError((_) => null);
  }

  @override
  bool isAligned({
    required double targetYawDeg,
    required double targetPitchDeg,
    double toleranceDeg = 15,
  }) {
    final p = _pose;
    if (p == null) return false;
    final dy = _deltaDeg(p.yaw * 180 / math.pi, targetYawDeg);
    final dp = (p.pitch * 180 / math.pi) - targetPitchDeg;
    return dy.abs() <= toleranceDeg && dp.abs() <= toleranceDeg;
  }

  double _deltaDeg(double a, double b) {
    var d = (a - b) % 360;
    if (d > 180) d -= 360;
    if (d < -180) d += 360;
    return d;
  }

  @override
  void dispose() {
    stop();
    super.dispose();
  }
}

/// Выбор бэкенда: native AR если доступен, иначе гироскоп (§3.1.1).
class ArSessionFactory {
  static Future<ArSession> create({bool preferNative = true}) async {
    if (preferNative && (Platform.isAndroid || Platform.isIOS)) {
      final native = NativeArBridge();
      if (await native.probe()) {
        return native;
      }
    }
    return GyroArSession();
  }
}
