/// Delivers OAuth callback code/state to AuthScreen.
class OAuthPending {
  OAuthPending._();
  static final instance = OAuthPending._();

  void Function(String provider, String code, String state)? handler;
  String? pendingProvider;
  String? pendingCode;
  String? pendingState;

  void start(String provider) {
    pendingProvider = provider;
  }

  void deliver(String code, String state) {
    final provider = pendingProvider;
    if (provider == null) return;
    if (handler != null) {
      handler!(provider, code, state);
      clear();
    } else {
      pendingCode = code;
      pendingState = state;
    }
  }

  void bind(void Function(String provider, String code, String state) fn) {
    handler = fn;
    final provider = pendingProvider;
    final code = pendingCode;
    final state = pendingState;
    if (provider != null && code != null && state != null) {
      clearPending();
      fn(provider, code, state);
    }
  }

  void unbind() {
    handler = null;
  }

  void clear() {
    pendingProvider = null;
    pendingCode = null;
    pendingState = null;
  }

  void clearPending() {
    pendingCode = null;
    pendingState = null;
  }
}
