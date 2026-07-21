import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';

/// Эффективные политики компании для текущего пользователя (§3.5.4, §3.12).
class CompanyAccessPolicy {
  const CompanyAccessPolicy({
    this.allowedCategories,
    this.allowDownload = true,
    this.allowShareLinks = true,
  });

  /// `null` или пусто — все категории.
  final List<String>? allowedCategories;
  final bool allowDownload;
  final bool allowShareLinks;

  bool get restrictsCategories =>
      allowedCategories != null && allowedCategories!.isNotEmpty;

  bool isCategoryAllowed(String apiName) {
    if (!restrictsCategories) return true;
    return allowedCategories!.contains(apiName);
  }

  static Future<CompanyAccessPolicy> load(ApiClient api, AppSession session) async {
    if (!session.corporate) {
      return const CompanyAccessPolicy();
    }

    var allowDownload = true;
    var allowShareLinks = true;
    List<String>? allowed;

    try {
      final settings = await api.getCompanySettings();
      final pol = settings['policies'];
      if (pol is Map) {
        final cats = pol['default_allowed_categories'];
        if (cats is List && cats.isNotEmpty) {
          allowed = cats.map((e) => e.toString()).toList();
        }
        if (session.companyRole == 'photographer') {
          allowDownload = pol['allow_photographer_download'] != false;
          allowShareLinks = pol['allow_photographer_add_links'] != false;
        }
      }

      if (session.companyRole == 'photographer') {
        final membersData = await api.listCompanyMembers();
        final members = (membersData['items'] as List?)?.cast<Map>() ?? [];
        final myId = session.userId;
        for (final m in members) {
          if (m['user_id'] == myId) {
            final mc = m['allowed_categories'];
            if (mc is List && mc.isNotEmpty) {
              allowed = mc.map((e) => e.toString()).toList();
            }
            break;
          }
        }
      }
    } catch (_) {}

    return CompanyAccessPolicy(
      allowedCategories: allowed,
      allowDownload: allowDownload,
      allowShareLinks: allowShareLinks,
    );
  }
}
