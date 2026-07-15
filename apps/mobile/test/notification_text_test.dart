import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/notification_inbox.dart';
import 'package:kwork_mobile/services/notification_text.dart';

void main() {
  test('NotificationText resolves generation_done', () {
    final l = lookupAppLocalizations(const Locale('ru'));
    final n = InboxNotification(
      id: '1',
      title: '',
      body: '',
      createdAt: DateTime.now(),
      orderId: '42',
      type: 'generation_done',
      titleKey: 'notification.generation_done',
      bodyKey: 'notification.generation_done',
    );
    expect(NotificationText.title(l, n), isNotEmpty);
    expect(NotificationText.body(l, n), contains('42'));
  });
}
