import 'package:kwork_mobile/l10n/app_localizations.dart';

String domeAngleLabel(AppLocalizations l, int index) {
  switch (index) {
    case 0:
      return l.angle00;
    case 1:
      return l.angle01;
    case 2:
      return l.angle02;
    case 3:
      return l.angle03;
    case 4:
      return l.angle04;
    case 5:
      return l.angle05;
    case 6:
      return l.angle06;
    case 7:
      return l.angle07;
    case 8:
      return l.angle08;
    case 9:
      return l.angle09;
    case 10:
      return l.angle10;
    case 11:
      return l.angle11;
    default:
      return '#$index';
  }
}
