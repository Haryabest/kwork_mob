import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';

String? _oauthAuditHint(String prefix, Map<String, dynamic> row) {
  final details = row['details'];
  final provider = details is Map ? details['provider']?.toString() : null;
  final at = row['created_at']?.toString();
  if (provider == null || provider.isEmpty) return null;
  return at != null && at.isNotEmpty ? '$prefix: $provider · $at' : '$prefix: $provider';
}

/// Личные oauth_* подсказки из `/user/audit` §16.
class OAuthAuditHints {
  static Future<void> refresh(ApiClient api, AppSession session) async {
    String? login;
    String? link;
    String? unlink;
    try {
      final res = await api.userAudit(actionPrefix: 'oauth_', limit: 50);
      final items = res['items'] as List?;
      if (items == null || items.isEmpty) {
        session.setOAuthAuditHints();
        return;
      }
      for (final raw in items) {
        final row = Map<String, dynamic>.from(raw as Map);
        final action = row['action']?.toString();
        if (action == 'oauth_login' && login == null) {
          login = _oauthAuditHint('Последний вход', row);
        } else if (action == 'oauth_link' && link == null) {
          link = _oauthAuditHint('Последняя привязка', row);
        } else if (action == 'oauth_unlink' && unlink == null) {
          unlink = _oauthAuditHint('Последняя отвязка', row);
        }
        if (login != null && link != null && unlink != null) break;
      }
    } catch (_) {}
    session.setOAuthAuditHints(login: login, link: link, unlink: unlink);
  }
}
