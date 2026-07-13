import 'package:kwork_mobile/core/ar/ar_pose.dart';
import 'package:kwork_mobile/domain/catalog.dart';

/// AR bbox → scale_calibration + подсказка тарифа (§3 / апсейл real_scale).
class ArTariffHint {
  const ArTariffHint({
    required this.tier,
    required this.scaleCalibration,
    required this.reason,
  });

  final Tier tier;
  final Map<String, double> scaleCalibration;
  final String reason;
}

/// Порог «крупный» товар: max габарит ≥ 0.8 м (мебель/крупная техника).
const double kLargeTierMaxEdgeM = 0.8;

ArTariffHint? hintFromArPose(ArPose? pose) {
  if (pose == null) return null;
  final l = pose.bboxLengthM;
  final w = pose.bboxWidthM;
  final h = pose.bboxHeightM;
  if (l == null || w == null || h == null) return null;
  if (l <= 0 || w <= 0 || h <= 0) return null;

  final maxEdge = [l, w, h].reduce((a, b) => a > b ? a : b);
  final tier = maxEdge >= kLargeTierMaxEdgeM ? Tier.large : Tier.small;
  return ArTariffHint(
    tier: tier,
    scaleCalibration: {
      'width': w,
      'height': h,
      'depth': l,
    },
    reason: tier == Tier.large
        ? 'По AR-габаритам (~${maxEdge.toStringAsFixed(2)} м) рекомендован тариф «Крупный»'
        : 'По AR-габаритам (~${maxEdge.toStringAsFixed(2)} м) подойдёт тариф «Малый»',
  );
}
