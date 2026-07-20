/// Active OAuth link callback (Profile tab registers while linking).
typedef OAuthLinkCompleter = Future<void> Function(String provider, String code, String state);

class OAuthCallbacks {
  static OAuthLinkCompleter? linkCompleter;
}
