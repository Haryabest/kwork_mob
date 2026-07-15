import 'package:intl/intl.dart';

String formatDateTimeLocal(DateTime d, String languageCode) {
  final l = d.toLocal();
  return DateFormat('dd.MM.yyyy HH:mm', languageCode).format(l);
}

String formatDateLocal(DateTime d, String languageCode) {
  return DateFormat('yyyy-MM-dd', languageCode).format(d.toLocal());
}
