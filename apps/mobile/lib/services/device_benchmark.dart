import 'dart:math';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Бенчмарк устройства §3.8 — FPS/память → ResolutionPreset + AR-рекомендация.
class DeviceBenchmark {
  DeviceBenchmark._();
  static final DeviceBenchmark instance = DeviceBenchmark._();

  static const _keyDone = 'device_benchmark_done';
  static const _keyScore = 'device_benchmark_score';
  static const _keyPreset = 'device_camera_preset';
  static const _keyArOk = 'device_ar_recommended';

  double? _score;
  ResolutionPreset _preset = ResolutionPreset.high;
  bool _arRecommended = true;

  double? get score => _score;
  ResolutionPreset get cameraPreset => _preset;
  bool get arRecommended => _arRecommended;

  Future<void> loadPersisted() async {
    final prefs = await SharedPreferences.getInstance();
    _score = prefs.getDouble(_keyScore);
    _arRecommended = prefs.getBool(_keyArOk) ?? true;
    final p = prefs.getString(_keyPreset);
    _preset = switch (p) {
      'medium' => ResolutionPreset.medium,
      'low' => ResolutionPreset.low,
      'veryHigh' => ResolutionPreset.veryHigh,
      _ => ResolutionPreset.high,
    };
  }

  Future<bool> get needsRun async {
    final prefs = await SharedPreferences.getInstance();
    return !(prefs.getBool(_keyDone) ?? false);
  }

  Future<double> run() async {
    final t0 = DateTime.now();
    final score = await compute(_cpuProbe, 180000);
    final elapsedMs = DateTime.now().difference(t0).inMilliseconds.clamp(1, 60000);
    // выше score / ниже время → лучше устройство
    final normalized = (score / elapsedMs).clamp(0.0, 100.0);
    _score = normalized;
    if (normalized < 8) {
      _preset = ResolutionPreset.medium;
      _arRecommended = false;
    } else if (normalized < 20) {
      _preset = ResolutionPreset.high;
      _arRecommended = true;
    } else {
      _preset = ResolutionPreset.veryHigh;
      _arRecommended = true;
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyDone, true);
    await prefs.setDouble(_keyScore, normalized);
    await prefs.setString(
      _keyPreset,
      switch (_preset) {
        ResolutionPreset.medium => 'medium',
        ResolutionPreset.low => 'low',
        ResolutionPreset.veryHigh => 'veryHigh',
        _ => 'high',
      },
    );
    await prefs.setBool(_keyArOk, _arRecommended);
    return normalized;
  }

  String presetLabel() {
    return switch (_preset) {
      ResolutionPreset.medium => 'medium',
      ResolutionPreset.low => 'low',
      ResolutionPreset.veryHigh => 'veryHigh',
      _ => 'high',
    };
  }
}

double _cpuProbe(int n) {
  var acc = 0.0;
  final rnd = Random(42);
  for (var i = 0; i < n; i++) {
    acc += sin(rnd.nextDouble() * pi) * cos(i * 0.001);
  }
  return acc.abs() + n.toDouble();
}
