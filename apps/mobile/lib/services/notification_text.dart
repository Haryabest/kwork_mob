import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/notification_inbox.dart';

/// Локализация push/inbox по ключу или типу (§16.2.2).
class NotificationText {
  static String title(AppLocalizations l, InboxNotification n) {
    if (n.titleKey != null) return _titleFromKey(l, n.titleKey!, n);
    if (n.title.isNotEmpty && !_looksLikeKey(n.title)) return n.title;
    return _fromType(l, n, isTitle: true);
  }

  static String body(AppLocalizations l, InboxNotification n) {
    if (n.bodyKey != null) return _bodyFromKey(l, n.bodyKey!, n);
    if (n.body.isNotEmpty && !_looksLikeKey(n.body)) return n.body;
    return _fromType(l, n, isTitle: false);
  }

  static bool _looksLikeKey(String s) => s.contains('.') && !s.contains(' ');

  static String _titleFromKey(AppLocalizations l, String key, InboxNotification n) {
    switch (key) {
      case 'notification.model_ready':
      case 'notification.generation_done':
        return l.notifGenDoneTitle;
      case 'notification.refund':
        return l.notifRefundTitle;
      case 'notification.nsfw_blocked':
        return l.notifNsfwTitle;
      case 'notification.generation_failed':
        return l.notifGenFailedTitle;
      case 'notification.cancelled':
        return l.notifCancelledTitle;
      case 'notification.topup_failed':
        return l.prefTopupFailed;
      case 'notification.support_reply':
        return l.prefSupportReply;
      default:
        return l.notificationDefault;
    }
  }

  static String _bodyFromKey(AppLocalizations l, String key, InboxNotification n) {
    final id = n.orderId ?? '—';
    switch (key) {
      case 'notification.model_ready':
      case 'notification.generation_done':
        return l.notifGenDoneBody(id);
      case 'notification.refund':
        return l.notifRefundBody(id);
      case 'notification.nsfw_blocked':
        return l.notifNsfwBody(id);
      case 'notification.generation_failed':
        return n.body.isNotEmpty ? n.body : l.notifGenFailedBody(id);
      case 'notification.cancelled':
        return l.notifCancelledBody(id);
      default:
        return n.body;
    }
  }

  static String _fromType(AppLocalizations l, InboxNotification n, {required bool isTitle}) {
    final id = n.orderId ?? '—';
    switch (n.type) {
      case 'generation_done':
        return isTitle ? l.notifGenDoneTitle : l.notifGenDoneBody(id);
      case 'nsfw_blocked':
        return isTitle ? l.notifNsfwTitle : l.notifNsfwBody(id);
      case 'generation_failed':
        return isTitle ? l.notifGenFailedTitle : (n.body.isNotEmpty ? n.body : l.notifGenFailedBody(id));
      case 'refund':
        return isTitle ? l.notifRefundTitle : l.notifRefundBody(id);
      case 'cancelled':
        return isTitle ? l.notifCancelledTitle : l.notifCancelledBody(id);
      case 'topup_failed':
        return isTitle ? l.prefTopupFailed : n.body;
      case 'support_reply':
        return isTitle ? l.prefSupportReply : n.body;
      case 'company_invite':
        return isTitle ? l.notifCompanyInviteTitle : n.body;
      default:
        return isTitle
            ? (n.title.isNotEmpty ? n.title : l.notificationDefault)
            : n.body;
    }
  }
}
