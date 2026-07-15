import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

/// Калибровка масштаба §3.7 — card / A4 / QR / manual, TTL 30 дней.
class ScaleCalibrationService {
  ScaleCalibrationService._();
  static final instance = ScaleCalibrationService._();

  static const _key = 'scale_calibration_v1';
  static const ttlDays = 30;

  /// ISO card 85.6×53.98 mm
  static const cardWidthM = 0.0856;
  static const cardHeightM = 0.05398;

  /// A4 210×297 mm
  static const a4WidthM = 0.21;
  static const a4HeightM = 0.297;

  /// Эталон QR с сайта (PDF) — сторона 100 мм
  static const qrSideM = 0.1;

  Map<String, dynamic>? _cached;

  Future<Map<String, dynamic>?> load() async {
    if (_cached != null) return _cached;
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null || raw.isEmpty) return null;
    try {
      final j = jsonDecode(raw) as Map<String, dynamic>;
      _cached = j;
      return j;
    } catch (_) {
      return null;
    }
  }

  Future<void> save({
    required String method,
    required Map<String, dynamic> scaleCalibration,
    double? referenceWidthM,
    double? referenceHeightM,
  }) async {
    final now = DateTime.now().toUtc();
    final payload = {
      'method': method,
      'scale_calibration': scaleCalibration,
      'reference_width_m': referenceWidthM,
      'reference_height_m': referenceHeightM,
      'calibrated_at': now.toIso8601String(),
      'expires_at': now.add(const Duration(days: ttlDays)).toIso8601String(),
    };
    _cached = payload;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, jsonEncode(payload));
  }

  Future<void> clear() async {
    _cached = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }

  Future<bool> isValid() async {
    final c = await load();
    if (c == null) return false;
    final exp = DateTime.tryParse(c['expires_at']?.toString() ?? '');
    if (exp == null) return false;
    return DateTime.now().toUtc().isBefore(exp);
  }

  Future<int?> daysLeft() async {
    final c = await load();
    if (c == null) return null;
    final exp = DateTime.tryParse(c['expires_at']?.toString() ?? '');
    if (exp == null) return null;
    return exp.difference(DateTime.now().toUtc()).inDays;
  }

  Future<Map<String, dynamic>?> scaleForOrder() async {
    if (!await isValid()) return null;
    final c = await load();
    final sc = c?['scale_calibration'];
    if (sc is Map) return Map<String, dynamic>.from(sc);
    return null;
  }

  /// Объект W×H×D (м) из эталона и доли экрана (0..1).
  Map<String, dynamic> objectFromReference({
    required double refWidthM,
    required double refHeightM,
    required double objectWidthFraction,
    required double objectHeightFraction,
    double depthFraction = 0.5,
  }) {
    final ow = refWidthM / objectWidthFraction.clamp(0.05, 0.95);
    final oh = refHeightM / objectHeightFraction.clamp(0.05, 0.95);
    final od = (ow + oh) / 2 * depthFraction.clamp(0.2, 1.0);
    return {
      'width': double.parse(ow.toStringAsFixed(4)),
      'height': double.parse(oh.toStringAsFixed(4)),
      'depth': double.parse(od.toStringAsFixed(4)),
      'method': 'reference_fraction',
    };
  }
}
