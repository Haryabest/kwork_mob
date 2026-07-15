import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:image/image.dart' as img;
import 'package:kwork_mobile/domain/guided_dome.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';

enum FrameVerdict { pass, fail }

class FrameQuality {
  FrameQuality({
    required this.index,
    required this.verdict,
    this.blurry = false,
    this.offCenter = false,
    this.overexposed = false,
    this.laplacian = 0,
    this.centerOffset = 0,
    this.fillRatio = 0,
  });

  final int index;
  final FrameVerdict verdict;
  final bool blurry;
  final bool offCenter;
  final bool overexposed;
  final double laplacian;
  final double centerOffset;
  final double fillRatio;

  String localizedReason(AppLocalizations l) {
    final parts = <String>[];
    if (blurry) parts.add(l.qaBlur);
    if (offCenter) parts.add(l.qaOffCenter);
    if (overexposed) parts.add(l.qaOverexposed);
    return parts.isEmpty ? l.qaOk : parts.join(', ');
  }

  String get reason {
    final parts = <String>[];
    if (blurry) parts.add('размытие');
    if (offCenter) parts.add('не по центру');
    if (overexposed) parts.add('пересвет');
    return parts.isEmpty ? 'ok' : parts.join(', ');
  }
}

/// Анализ кадра §3.9.1 (без нейросетей).
class QualityAnalyzer {
  QualityAnalyzer._();
  static final instance = QualityAnalyzer._();

  static const laplacianThreshold = 100.0;

  Future<FrameQuality> analyzeFile(int index, File file) async {
    final bytes = await file.readAsBytes();
    return analyzeBytes(index, bytes);
  }

  FrameQuality analyzeBytes(int index, List<int> jpegBytes) {
    final decoded = img.decodeImage(Uint8List.fromList(jpegBytes));
    if (decoded == null) {
      return FrameQuality(index: index, verdict: FrameVerdict.fail, blurry: true);
    }
    final small = img.copyResize(decoded, width: 320);
    final gray = img.grayscale(small);

    final lap = _laplacianVariance(gray);
    final contour = _simpleContour(gray);
    final cx = contour.$1;
    final cy = contour.$2;
    final fill = contour.$3;
    final dx = (cx - 0.5).abs();
    final dy = (cy - 0.5).abs();
    final offset = math.max(dx, dy);

    final blurry = lap < laplacianThreshold;
    final offCenter = offset > 0.10;
    final overexposed = _overexposedRatio(gray) > 0.05;
    final fail = blurry || offCenter || overexposed;

    return FrameQuality(
      index: index,
      verdict: fail ? FrameVerdict.fail : FrameVerdict.pass,
      blurry: blurry,
      offCenter: offCenter,
      overexposed: overexposed,
      laplacian: lap,
      centerOffset: offset,
      fillRatio: fill,
    );
  }

  /// Центрирование + доля контура для блокировки спуска (§3.1.3).
  ({bool centered, bool fillOk, double offset, double fill, String? message})
      liveGate(List<int> jpegBytes, AppLocalizations l) {
    final q = analyzeBytes(0, jpegBytes);
    final centered = q.centerOffset <= kCenterMaxOffsetRatio;
    final fillOk =
        q.fillRatio >= kContourMinFill && q.fillRatio <= kContourMaxFill;
    String? msg;
    if (!centered) {
      msg = l.qaCenterPhone;
    } else if (q.fillRatio < kContourMinFill) {
      msg = l.qaCloser;
    } else if (q.fillRatio > kContourMaxFill) {
      msg = l.qaFarther;
    }
    return (
      centered: centered,
      fillOk: fillOk,
      offset: q.centerOffset,
      fill: q.fillRatio,
      message: msg,
    );
  }

  double _laplacianVariance(img.Image gray) {
    var sum = 0.0;
    var sumSq = 0.0;
    var n = 0;
    for (var y = 1; y < gray.height - 1; y++) {
      for (var x = 1; x < gray.width - 1; x++) {
        final c = gray.getPixel(x, y).r.toDouble();
        final v = gray.getPixel(x - 1, y).r +
            gray.getPixel(x + 1, y).r +
            gray.getPixel(x, y - 1).r +
            gray.getPixel(x, y + 1).r -
            4 * c;
        sum += v;
        sumSq += v * v;
        n++;
      }
    }
    if (n == 0) return 0;
    final mean = sum / n;
    return sumSq / n - mean * mean;
  }

  /// Упрощённый контур: порог по яркости относительно фона.
  (double cx, double cy, double fill) _simpleContour(img.Image gray) {
    var sumL = 0.0;
    final total = gray.width * gray.height;
    for (final p in gray) {
      sumL += p.r;
    }
    final mean = sumL / total;
    final threshold = mean * 0.85;
    var sx = 0.0, sy = 0.0, count = 0;
    for (var y = 0; y < gray.height; y++) {
      for (var x = 0; x < gray.width; x++) {
        if (gray.getPixel(x, y).r < threshold) {
          sx += x;
          sy += y;
          count++;
        }
      }
    }
    if (count == 0) return (0.5, 0.5, 0);
    return (sx / count / gray.width, sy / count / gray.height, count / total);
  }

  double _overexposedRatio(img.Image gray) {
    var hot = 0;
    final total = gray.width * gray.height;
    for (final p in gray) {
      if (p.r > 242) hot++;
    }
    return hot / total;
  }
}
