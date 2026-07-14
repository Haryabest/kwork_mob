import 'dart:async';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// Режимы энергосбережения при съёмке (§3.8.2).
enum ThermalLevel {
  /// < 40°C — норма.
  normal,

  /// ≥ 40°C — FPS 15, без тяжёлых AR-эффектов.
  powerSave,

  /// > 45°C — предупреждение, предложить прервать.
  critical,
}

/// Мониторинг температуры батареи / thermal state.
class ThermalMonitor extends ChangeNotifier {
  ThermalMonitor();

  static const _method = MethodChannel('kwork/thermal');
  static const _events = EventChannel('kwork/thermal/stream');

  StreamSubscription? _sub;
  double? _celsius;
  ThermalLevel _level = ThermalLevel.normal;
  bool _criticalAcknowledged = false;
  bool _effectsReduced = false;

  double? get celsius => _celsius;
  ThermalLevel get level => _level;
  bool get powerSave => _level != ThermalLevel.normal || _criticalAcknowledged;
  bool get effectsReduced => _effectsReduced || powerSave;
  bool get needsCriticalPrompt =>
      _level == ThermalLevel.critical && !_criticalAcknowledged;

  /// Целевой FPS preview: 30 норма / 15 энергосбережение.
  int get targetFps => powerSave ? 15 : 30;

  Future<void> start() async {
    await stop();
    try {
      final v = await _method.invokeMethod<dynamic>('getBatteryCelsius');
      if (v is num) _apply(v.toDouble());
    } catch (e) {
      debugPrint('ThermalMonitor method: $e');
    }
    try {
      _sub = _events.receiveBroadcastStream().listen((event) {
        if (event is num) _apply(event.toDouble());
      });
    } catch (e) {
      debugPrint('ThermalMonitor stream: $e');
      // iOS / desktop: ProcessInfo.thermalState через тот же канал (если нет — polling null)
      if (!Platform.isAndroid) {
        _sub = Stream.periodic(const Duration(seconds: 5)).listen((_) async {
          try {
            final v = await _method.invokeMethod<dynamic>('getBatteryCelsius');
            if (v is num) _apply(v.toDouble());
          } catch (_) {}
        });
      }
    }
  }

  Future<void> stop() async {
    await _sub?.cancel();
    _sub = null;
  }

  void acknowledgeCriticalContinue() {
    _criticalAcknowledged = true;
    _effectsReduced = true;
    notifyListeners();
  }

  void resetSessionFlags() {
    _criticalAcknowledged = false;
    notifyListeners();
  }

  void _apply(double c) {
    _celsius = c;
    final next = c > 45
        ? ThermalLevel.critical
        : c >= 40
            ? ThermalLevel.powerSave
            : ThermalLevel.normal;
    if (next != ThermalLevel.critical) {
      _criticalAcknowledged = false;
    }
    _effectsReduced = next != ThermalLevel.normal;
    if (next != _level) {
      _level = next;
      notifyListeners();
    } else {
      notifyListeners();
    }
  }

  @override
  void dispose() {
    stop();
    super.dispose();
  }
}
