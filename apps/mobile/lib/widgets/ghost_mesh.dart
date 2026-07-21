import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/catalog.dart';

enum GhostMeshShape {
  oval,
  torso,
  shoe,
  phone,
  box,
  sphere,
}

GhostMeshShape ghostShapeForCategory(ProductCategory c) {
  switch (c) {
    case ProductCategory.clothing:
      return GhostMeshShape.torso;
    case ProductCategory.shoes:
      return GhostMeshShape.shoe;
    case ProductCategory.electronics:
      return GhostMeshShape.phone;
    case ProductCategory.furniture:
      return GhostMeshShape.box;
    case ProductCategory.decor:
    case ProductCategory.toys:
    case ProductCategory.adult:
    case ProductCategory.other:
      return GhostMeshShape.sphere;
  }
}

/// Ghost Mesh §3.11 — форма по категории + pinch-масштаб.
class GhostMeshOverlay extends StatelessWidget {
  const GhostMeshOverlay({
    super.key,
    required this.category,
    required this.scale,
    required this.aligned,
    this.fitOk = true,
    this.shapeOverride,
    this.onScaleUpdate,
    this.interactive = true,
  });

  final ProductCategory category;
  final double scale;
  final bool aligned;
  final bool fitOk;
  final GhostMeshShape? shapeOverride;
  final ValueChanged<double>? onScaleUpdate;
  final bool interactive;

  @override
  Widget build(BuildContext context) {
    final shape = shapeOverride ?? ghostShapeForCategory(category);
    final size = MediaQuery.sizeOf(context);
    final baseW = size.width * 0.55;
    final baseH = size.height * 0.45;
    final (w, h) = _dims(shape, baseW, baseH, scale);
    final color = !fitOk
        ? AppColors.error
        : aligned
            ? AppColors.success
            : AppColors.accent;

    Widget mesh = CustomPaint(
      painter: _GhostPainter(shape: shape, color: color.withValues(alpha: 0.5)),
      child: SizedBox(width: w, height: h),
    );

    if (interactive && onScaleUpdate != null) {
      mesh = GestureDetector(
        onScaleUpdate: (d) {
          if (d.scale == 1.0) return;
          onScaleUpdate!( (scale * d.scale).clamp(0.5, 2.5));
        },
        child: mesh,
      );
    }

    return Center(child: mesh);
  }

  (double, double) _dims(GhostMeshShape s, double bw, double bh, double sc) {
    switch (s) {
      case GhostMeshShape.torso:
        return (bw * 0.7 * sc, bh * 1.05 * sc);
      case GhostMeshShape.shoe:
        return (bw * 1.1 * sc, bh * 0.45 * sc);
      case GhostMeshShape.phone:
        return (bw * 0.42 * sc, bh * 0.95 * sc);
      case GhostMeshShape.box:
        return (bw * 1.0 * sc, bh * 0.85 * sc);
      case GhostMeshShape.sphere:
        final side = math.min(bw, bh) * 0.85 * sc;
        return (side, side);
      case GhostMeshShape.oval:
        return (bw * sc, bh * sc);
    }
  }
}

class _GhostPainter extends CustomPainter {
  _GhostPainter({required this.shape, required this.color});

  final GhostMeshShape shape;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final fill = Paint()
      ..color = color.withValues(alpha: 0.12)
      ..style = PaintingStyle.fill;
    final stroke = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2;

    final rect = Offset.zero & size;
    switch (shape) {
      case GhostMeshShape.torso:
        final path = Path()
          ..moveTo(size.width * 0.35, size.height * 0.08)
          ..lineTo(size.width * 0.65, size.height * 0.08)
          ..lineTo(size.width * 0.78, size.height * 0.35)
          ..lineTo(size.width * 0.72, size.height * 0.92)
          ..lineTo(size.width * 0.28, size.height * 0.92)
          ..lineTo(size.width * 0.22, size.height * 0.35)
          ..close();
        canvas.drawPath(path, fill);
        canvas.drawPath(path, stroke);
      case GhostMeshShape.shoe:
        final r = RRect.fromRectAndRadius(
          Rect.fromLTWH(size.width * 0.05, size.height * 0.25, size.width * 0.9, size.height * 0.5),
          const Radius.circular(28),
        );
        canvas.drawRRect(r, fill);
        canvas.drawRRect(r, stroke);
      case GhostMeshShape.phone:
        final r = RRect.fromRectAndRadius(
          Rect.fromCenter(
            center: rect.center,
            width: size.width * 0.55,
            height: size.height * 0.92,
          ),
          const Radius.circular(18),
        );
        canvas.drawRRect(r, fill);
        canvas.drawRRect(r, stroke);
      case GhostMeshShape.box:
        canvas.drawRRect(RRect.fromRectAndRadius(rect.deflate(4), const Radius.circular(8)), fill);
        canvas.drawRRect(RRect.fromRectAndRadius(rect.deflate(4), const Radius.circular(8)), stroke);
      case GhostMeshShape.sphere:
      case GhostMeshShape.oval:
        canvas.drawOval(rect.deflate(6), fill);
        canvas.drawOval(rect.deflate(6), stroke);
    }
  }

  @override
  bool shouldRepaint(covariant _GhostPainter old) =>
      old.shape != shape || old.color != color;
}
