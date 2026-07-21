import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';

/// §3.2 — круговая диаграмма 12 ракурсов (режим без AR).
class AngleDiagramOverlay extends StatelessWidget {
  const AngleDiagramOverlay({
    super.key,
    required this.currentIndex,
    this.size = 96,
  });

  final int currentIndex;
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _AngleDiagramPainter(currentIndex: currentIndex),
      ),
    );
  }
}

class _AngleDiagramPainter extends CustomPainter {
  _AngleDiagramPainter({required this.currentIndex});

  final int currentIndex;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = size.shortestSide / 2 - 6;
    final bg = Paint()
      ..color = Colors.black.withValues(alpha: 0.45)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(center, radius + 4, bg);

    for (var i = 0; i < kGuidedDomeCount; i++) {
      final angle = kGuidedDomeAngles[i];
      final rad = (angle.azimuthDeg - 90) * math.pi / 180;
      final dotR = i == currentIndex ? 5.5 : 3.5;
      final dist = radius * 0.78;
      final pos = Offset(
        center.dx + math.cos(rad) * dist,
        center.dy + math.sin(rad) * dist,
      );
      final fill = Paint()
        ..color = i == currentIndex ? AppColors.accent : Colors.white.withValues(alpha: 0.55)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(pos, dotR, fill);
      if (i == currentIndex) {
        final ring = Paint()
          ..color = Colors.white
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5;
        canvas.drawCircle(pos, dotR + 2, ring);
      }
    }
    final hub = Paint()..color = Colors.white.withValues(alpha: 0.35);
    canvas.drawCircle(center, 3, hub);
  }

  @override
  bool shouldRepaint(covariant _AngleDiagramPainter old) => old.currentIndex != currentIndex;
}
