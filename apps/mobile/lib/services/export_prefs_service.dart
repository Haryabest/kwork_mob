import 'package:shared_preferences/shared_preferences.dart';

/// Предпочтительный формат экспорта §19.14.3.
enum ExportFormat { glb, usdz }

class ExportPrefsService {
  ExportPrefsService._();
  static final instance = ExportPrefsService._();

  static const _key = 'export_format_pref';

  ExportFormat _cached = ExportFormat.glb;

  ExportFormat get format => _cached;

  Future<void> load({String? fromServer}) async {
    if (fromServer == 'usdz') {
      _cached = ExportFormat.usdz;
      return;
    }
    if (fromServer == 'glb') {
      _cached = ExportFormat.glb;
      return;
    }
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key) ?? 'glb';
    _cached = raw == 'usdz' ? ExportFormat.usdz : ExportFormat.glb;
  }

  Future<void> setFormat(ExportFormat value) async {
    _cached = value;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_key, value == ExportFormat.usdz ? 'usdz' : 'glb');
  }

  String get apiFormat => _cached == ExportFormat.usdz ? 'usdz' : 'glb';
}
