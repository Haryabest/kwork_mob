import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';

/// AR-метки ракурсов (§3.1.2) — кольцо из 12 подсказок + текущая метка.
class ArMarkersOverlay extends StatelessWidget {
  const ArMarkersOverlay({
    super.key,
    required this.currentIndex,
    this.yawOffsetDeg = 0,
    this.compact = false,
  });

  final int currentIndex;
  final double yawOffsetDeg;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    return CustomPaint(
      painter: _ArMarkersPainter(
        currentIndex: currentIndex,
        yawOffsetDeg: yawOffsetDeg,
        compact: compact,
      ),
      child: const SizedBox.expand(),
    );
  }
}

class _ArMarkersPainter extends CustomPainter {
  _ArMarkersPainter({
    required this.currentIndex,
    required this.yawOffsetDeg,
    required this.compact,
  });

  final int currentIndex;
  final double yawOffsetDeg;
  final bool compact;

  @override
  void paint(Canvas canvas, Size size) {
    final c = Offset(size.width / 2, size.height * (compact ? 0.62 : 0.58));
    final radius = math.min(size.width, size.height) * (compact ? 0.22 : 0.28);

    for (var i = 0; i < kGuidedDomeCount; i++) {
      final angle = kGuidedDomeAngles[i];
      final rad = (angle.azimuthDeg - 90) * math.pi / 180;
      final elev = angle.elevationDeg / 90;
      final r = radius * (0.75 + elev * 0.35);
      final p = Offset(c.dx + math.cos(rad) * r, c.dy + math.sin(rad) * r);
      final isCurrent = i == currentIndex;
      final done = i < currentIndex;

      final fill = Paint()
        ..color = isCurrent
            ? AppColors.ozonPrimary
            : done
                ? AppColors.success.withValues(alpha: 0.85)
                : AppColors.accent.withValues(alpha: 0.45)
        ..style = PaintingStyle.fill;

      canvas.drawCircle(p, isCurrent ? 14 : 9, fill);
      if (isCurrent) {
        final ring = Paint()
          ..color = Colors.white
          ..style = PaintingStyle.stroke
          ..strokeWidth = 2;
        canvas.drawCircle(p, 18, ring);
      }

      final tp = TextPainter(
        text: TextSpan(
          text: '${i + 1}',
          style: TextStyle(
            color: Colors.white,
            fontSize: isCurrent ? 11 : 8,
            fontWeight: FontWeight.bold,
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, p - Offset(tp.width / 2, tp.height / 2));
    }

    // Стрелка «куда идти» от центра к текущей метке
    final target = kGuidedDomeAngles[currentIndex];
    final tr = (target.azimuthDeg - 90 + yawOffsetDeg) * math.pi / 180;
    final trRadius = radius * (0.75 + target.elevationDeg / 90 * 0.35);
    final tip = Offset(c.dx + math.cos(tr) * trRadius, c.dy + math.sin(tr) * trRadius);
    final arrow = Paint()
      ..color = Colors.white.withValues(alpha: 0.75)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;
    canvas.drawLine(c, tip, arrow);
  }

  @override
  bool shouldRepaint(covariant _ArMarkersPainter old) =>
      old.currentIndex != currentIndex || old.yawOffsetDeg != yawOffsetDeg;
}
