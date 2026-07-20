/// Delivers OAuth callback code/state to AuthScreen or ProfileTab.
enum OAuthFlow { login, register, link }

class OAuthPending {
  OAuthPending._();
  static final instance = OAuthPending._();

  void Function(String provider, String code, String state, OAuthFlow flow)? handler;
  String? pendingProvider;
  OAuthFlow pendingFlow = OAuthFlow.login;
  String? pendingCode;
  String? pendingState;

  void start(String provider, {OAuthFlow flow = OAuthFlow.login}) {
    pendingProvider = provider;
    pendingFlow = flow;
  }

  void deliver(String code, String state) {
    final provider = pendingProvider;
    if (provider == null) return;
    if (handler != null) {
      handler!(provider, code, state, pendingFlow);
      clear();
    } else {
      pendingCode = code;
      pendingState = state;
    }
  }

  void bind(void Function(String provider, String code, String state, OAuthFlow flow) fn) {
    handler = fn;
    final provider = pendingProvider;
    final code = pendingCode;
    final state = pendingState;
    final flow = pendingFlow;
    if (provider != null && code != null && state != null) {
      clearPending();
      fn(provider, code, state, flow);
    }
  }

  void unbind() {
    handler = null;
  }

  void clear() {
    pendingProvider = null;
    pendingFlow = OAuthFlow.login;
    pendingCode = null;
    pendingState = null;
  }

  void clearPending() {
    pendingCode = null;
    pendingState = null;
  }
}
