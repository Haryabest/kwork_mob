import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:path_provider/path_provider.dart';

/// Проверка свободного места перед съёмкой (§3.3.2 / §3.5).
class StorageSpaceGuard {
  StorageSpaceGuard._();
  static final instance = StorageSpaceGuard._();

  static const minFreeMb = 500;
  static const _channel = MethodChannel('kwork/storage');

  Future<int?> freeMb() async {
    try {
      final bytes = await _channel.invokeMethod<int>('getFreeBytes');
      if (bytes != null) return bytes ~/ (1024 * 1024);
    } catch (e) {
      debugPrint('StorageSpaceGuard channel: $e');
    }
    if (Platform.isAndroid || Platform.isIOS) {
      try {
        final dir = await getApplicationDocumentsDirectory();
        final stat = await _statvfsEstimate(dir.path);
        if (stat != null) return stat;
      } catch (_) {}
    }
    return null;
  }

  Future<int?> _statvfsEstimate(String path) async {
    if (!Platform.isAndroid) return null;
    try {
      final r = await Process.run('df', ['-k', path]);
      if (r.exitCode != 0) return null;
      final lines = (r.stdout as String).trim().split('\n');
      if (lines.length < 2) return null;
      final parts = lines.last.split(RegExp(r'\s+'));
      if (parts.length < 4) return null;
      final availKb = int.tryParse(parts[3]);
      if (availKb == null) return null;
      return availKb ~/ 1024;
    } catch (_) {
      return null;
    }
  }

  Future<bool> hasEnoughForShoot() async {
    final mb = await freeMb();
    if (mb == null) return true;
    return mb >= minFreeMb;
  }
}
