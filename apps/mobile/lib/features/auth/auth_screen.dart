import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
import 'package:kwork_mobile/services/oauth_audit_hints.dart';
import 'package:kwork_mobile/services/oauth_pending.dart';
import 'package:kwork_mobile/services/push_service.dart';
import 'package:url_launcher/url_launcher.dart';

enum _AuthStep { login, register, verifyEmail, accountType, forgot, resetConfirm, twoFa }

class AuthScreen extends StatefulWidget {
  const AuthScreen({
    super.key,
    required this.api,
    required this.session,
    required this.push,
    this.initialMode,
  });

  final ApiClient api;
  final AppSession session;
  final PushService push;
  final String? initialMode;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  late _AuthStep _step;
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _passwordConfirm = TextEditingController();
  final _code = TextEditingController();
  final _totp = TextEditingController();
  final _resetToken = TextEditingController();
  final _newPassword = TextEditingController();
  final _newPasswordConfirm = TextEditingController();
  final _fullName = TextEditingController();
  final _companyName = TextEditingController();
  final _inn = TextEditingController();
  final _ogrn = TextEditingController();
  final _legalAddress = TextEditingController();
  final _directorName = TextEditingController();
  final _bankName = TextEditingController();
  final _bik = TextEditingController();
  final _checkingAccount = TextEditingController();

  bool _loading = false;
  bool _rememberMe = true;
  bool _consents = false;
  String _accountType = 'individual';
  String? _error;
  String? _challengeToken;
  String? _devCode;
  String? _devResetToken;
  String? _info;
  List<Map<String, String>> _oauthProviders = [];

  static const _oauthConsents = ['terms', 'privacy', 'offer', 'rights', 'nsfw_rules'];

  @override
  void initState() {
    super.initState();
    _step = widget.initialMode == 'register'
        ? _AuthStep.register
        : widget.initialMode == 'account-type'
            ? _AuthStep.accountType
            : _AuthStep.login;
    _loadOAuthProviders();
    OAuthPending.instance.bind(_onOAuthPending);
  }

  @override
  void dispose() {
    OAuthPending.instance.unbind();
    _email.dispose();
    _password.dispose();
    _passwordConfirm.dispose();
    _code.dispose();
    _totp.dispose();
    _resetToken.dispose();
    _newPassword.dispose();
    _newPasswordConfirm.dispose();
    _fullName.dispose();
    _companyName.dispose();
    _inn.dispose();
    _ogrn.dispose();
    _legalAddress.dispose();
    _directorName.dispose();
    _bankName.dispose();
    _bik.dispose();
    _checkingAccount.dispose();
    super.dispose();
  }

  Future<void> _loadOAuthProviders() async {
    try {
      final items = await widget.api.listOAuthProviders();
      if (mounted) setState(() => _oauthProviders = items);
    } catch (_) {}
  }

  Future<void> _startOAuth(String provider) async {
    if (_step == _AuthStep.register && !_consents) {
      setState(() => _error = AppLocalizations.of(context)!.authAcceptTerms);
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      OAuthPending.instance.start(provider, flow: _step == _AuthStep.register ? OAuthFlow.register : OAuthFlow.login);
      final url = await widget.api.oauthAuthorizeUrl(
        provider: provider,
        mode: _step == _AuthStep.register ? 'register' : 'login',
        consents: _step == _AuthStep.register ? _oauthConsents : null,
        companyId: widget.session.corporate ? widget.session.companyId : null,
      );
      final uri = Uri.parse(url);
      if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
        throw StateError('Не удалось открыть браузер');
      }
    } catch (e) {
      OAuthPending.instance.clear();
      setState(() => _error = formatApiError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _refreshMeOAuth() async {
    try {
      final me = await widget.api.me();
      widget.session.applyMe(me);
    } catch (_) {}
  }

  Future<void> _onOAuthPending(String provider, String code, String state, OAuthFlow flow) async {
    if (flow == OAuthFlow.link) {
      if (await widget.api.hasToken) {
        try {
          await widget.api.oauthLinkComplete(provider: provider, code: code, state: state);
          AnalyticsService.instance.track('screen_view', {'screen': 'oauth_link_$provider'});
          await _refreshMeOAuth();
          await OAuthAuditHints.refresh(widget.api, widget.session);
        } catch (e) {
          if (mounted) setState(() => _error = formatApiError(e));
        }
      }
      OAuthPending.instance.clear();
      if (mounted) context.go('/home?tab=profile');
      return;
    }
    await _onOAuthCallback(provider, code, state);
  }

  Future<void> _onOAuthCallback(String provider, String code, String state) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.oauthCallback(provider: provider, code: code, state: state);
      AnalyticsService.instance.track('screen_view', {'screen': 'oauth_login_$provider'});
      OAuthPending.instance.clear();
      await _refreshMeOAuth();
      await OAuthAuditHints.refresh(widget.api, widget.session);
      if (data['status'] == 'pending_type') {
        if (!mounted) return;
        setState(() => _step = _AuthStep.accountType);
        return;
      }
      await _finishLogin();
    } catch (e) {
      setState(() => _error = formatApiError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<Widget> _oauthButtons() {
    if (_oauthProviders.isEmpty) return [];
    if (_step != _AuthStep.login && _step != _AuthStep.register) return [];
    return [
      const SizedBox(height: 16),
      Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text(
            'Войти через',
            style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
          ),
          if (widget.session.corporate) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: AppColors.accent.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Text(
                'Корп. режим',
                style: TextStyle(color: AppColors.accent, fontSize: 11, fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ],
      ),
      const SizedBox(height: 8),
      ..._oauthProviders.map(
        (p) => Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: FButton(
            variant: .outline,
            onPress: _loading ? null : () => _startOAuth(p['provider'] ?? ''),
            child: Text(p['label'] ?? p['provider'] ?? ''),
          ),
        ),
      ),
    ];
  }

  void _setStep(_AuthStep step) {
    setState(() {
      _step = step;
      _error = null;
      _info = null;
    });
  }

  Future<void> _finishLogin() async {
    final me = await widget.api.me();
    widget.session.applyMe(me);
    await widget.session.setCompanies(await widget.api.myCompanies());
    await widget.push.init();
    try {
      final pending = await widget.api.legalPending();
      if (!mounted) return;
      if (pending.isNotEmpty) {
        context.go('/legal/consent');
        return;
      }
    } catch (_) {}
    if (mounted) await _goAuthenticatedHome();
  }

  Future<void> _goAuthenticatedHome() async {
    if (!mounted) return;
    if (await widget.push.applyPendingRoute(GoRouter.of(context))) return;
    context.go('/home');
  }

  Future<void> _submitLogin() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.login(
        _email.text.trim(),
        _password.text,
        rememberMe: _rememberMe,
      );
      if (data['requires_2fa'] == true) {
        setState(() {
          _challengeToken = data['challenge_token']?.toString();
          _step = _AuthStep.twoFa;
          _loading = false;
        });
        return;
      }
      await _finishLogin();
    } catch (e) {
      setState(() => _error = formatApiError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _submitRegister() async {
    final l10n = AppLocalizations.of(context)!;
    if (!_consents) {
      setState(() => _error = l10n.authAcceptTerms);
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await widget.api.register(
        email: _email.text.trim(),
        password: _password.text,
        passwordConfirm: _passwordConfirm.text,
      );
      setState(() {
        _devCode = res['dev_code']?.toString();
        _info = res['message']?.toString();
        _step = _AuthStep.verifyEmail;
      });
    } catch (e) {
      setState(() => _error = formatApiError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _submitVerifyEmail() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await widget.api.verifyEmail(
        email: _email.text.trim(),
        code: _code.text.trim(),
      );
      setState(() => _step = _AuthStep.accountType);
    } catch (e) {
      setState(() => _error = formatApiError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _submitAccountType() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await widget.api.setAccountType(
        accountType: _accountType,
        fullName: _fullName.text.trim(),
        companyName: _companyName.text.trim(),
        inn: _inn.text.trim(),
        ogrn: _ogrn.text.trim(),
        legalAddress: _legalAddress.text.trim(),
        directorName: _directorName.text.trim(),
        bankName: _bankName.text.trim(),
        bik: _bik.text.trim(),
        checkingAccount: _checkingAccount.text.trim(),
      );
      await _finishLogin();
    } catch (e) {
      setState(() => _error = formatApiError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _submitForgot() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await widget.api.requestPasswordReset(_email.text.trim());
      setState(() {
        _devResetToken = res['dev_token']?.toString();
        _info = res['message']?.toString();
        _step = _AuthStep.resetConfirm;
      });
    } catch (e) {
      setState(() => _error = formatApiError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _submitResetConfirm() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await widget.api.confirmPasswordReset(
        token: _resetToken.text.trim(),
        newPassword: _newPassword.text,
        passwordConfirm: _newPasswordConfirm.text,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context)!.authPasswordUpdated)),
      );
      _password.clear();
      _newPassword.clear();
      _newPasswordConfirm.clear();
      _resetToken.clear();
      _setStep(_AuthStep.login);
    } catch (e) {
      setState(() => _error = formatApiError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _submit2fa() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await widget.api.verifyLogin2fa(
        challengeToken: _challengeToken!,
        code: _totp.text.trim(),
      );
      await _finishLogin();
    } catch (e) {
      setState(() => _error = formatApiError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _submit() async {
    switch (_step) {
      case _AuthStep.login:
        await _submitLogin();
      case _AuthStep.register:
        await _submitRegister();
      case _AuthStep.verifyEmail:
        await _submitVerifyEmail();
      case _AuthStep.accountType:
        await _submitAccountType();
      case _AuthStep.forgot:
        await _submitForgot();
      case _AuthStep.resetConfirm:
        await _submitResetConfirm();
      case _AuthStep.twoFa:
        await _submit2fa();
    }
  }

  String _title(AppLocalizations l10n) {
    switch (_step) {
      case _AuthStep.login:
        return l10n.authTitle;
      case _AuthStep.register:
        return l10n.authCreateAccount;
      case _AuthStep.verifyEmail:
        return l10n.authVerifyEmail;
      case _AuthStep.accountType:
        return l10n.authAccountType;
      case _AuthStep.forgot:
        return l10n.authForgotPasswordTitle;
      case _AuthStep.resetConfirm:
        return l10n.authNewPasswordTitle;
      case _AuthStep.twoFa:
        return l10n.authTwoFaTitle;
    }
  }

  String _primaryLabel(AppLocalizations l10n) {
    if (_loading) return '…';
    switch (_step) {
      case _AuthStep.login:
        return l10n.login;
      case _AuthStep.register:
        return l10n.register;
      case _AuthStep.verifyEmail:
        return l10n.confirm;
      case _AuthStep.accountType:
        return l10n.continueBtn;
      case _AuthStep.forgot:
        return l10n.authSendLink;
      case _AuthStep.resetConfirm:
        return l10n.authSavePassword;
      case _AuthStep.twoFa:
        return l10n.confirm;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    return FScaffold(
      child: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    l10n.appName,
                    style: context.theme.typography.xl2.copyWith(fontWeight: FontWeight.bold),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _title(l10n),
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: AppColors.textSecondary),
                  ),
                  if (_info != null) ...[
                    const SizedBox(height: 12),
                    Text(_info!, style: const TextStyle(color: AppColors.textSecondary, fontSize: 13)),
                  ],
                  if (_devCode != null && _step == _AuthStep.verifyEmail) ...[
                    const SizedBox(height: 8),
                    Text(l10n.authDevCode(_devCode!), style: const TextStyle(color: AppColors.ozonPrimary)),
                  ],
                  if (_devResetToken != null && _step == _AuthStep.resetConfirm) ...[
                    const SizedBox(height: 8),
                    Text(l10n.authDevToken(_devResetToken!), style: const TextStyle(color: AppColors.ozonPrimary)),
                  ],
                  const SizedBox(height: 24),
                  ..._fields(l10n),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(_error!, style: const TextStyle(color: AppColors.error)),
                  ],
                  const SizedBox(height: 20),
                  FButton(
                    onPress: _loading ? null : _submit,
                    child: Text(_primaryLabel(l10n)),
                  ),
                  const SizedBox(height: 12),
                  ..._footer(l10n),
                  ..._oauthButtons(),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  List<Widget> _fields(AppLocalizations l10n) {
    switch (_step) {
      case _AuthStep.login:
        return [
          FTextField(
            control: FTextFieldControl.managed(controller: _email),
            label: Text(l10n.email),
            keyboardType: TextInputType.emailAddress,
            autofillHints: const [AutofillHints.email],
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 12),
          FTextField.password(
            control: FTextFieldControl.managed(controller: _password),
            label: Text(l10n.password),
            textInputAction: TextInputAction.done,
            onSubmit: (_) => _submit(),
          ),
          const SizedBox(height: 8),
          FCheckbox(
            value: _rememberMe,
            onChange: (v) => setState(() => _rememberMe = v),
            label: Text(l10n.authRememberMe),
          ),
        ];
      case _AuthStep.register:
        return [
          FTextField(
            control: FTextFieldControl.managed(controller: _email),
            label: Text(l10n.email),
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 12),
          FTextField.password(
            control: FTextFieldControl.managed(controller: _password),
            label: Text(l10n.password),
            autofillHints: const [AutofillHints.newPassword],
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 12),
          FTextField.password(
            control: FTextFieldControl.managed(controller: _passwordConfirm),
            label: Text(l10n.authPasswordConfirm),
            autofillHints: const [AutofillHints.newPassword],
            textInputAction: TextInputAction.done,
          ),
          const SizedBox(height: 8),
          FCheckbox(
            value: _consents,
            onChange: (v) => setState(() => _consents = v),
            label: Text(l10n.authConsents),
          ),
        ];
      case _AuthStep.verifyEmail:
        return [
          FTextField(
            control: FTextFieldControl.managed(controller: _code),
            label: Text(l10n.authEmailCode),
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            maxLength: 6,
            textInputAction: TextInputAction.done,
          ),
        ];
      case _AuthStep.accountType:
        return [
          Row(
            children: [
              Expanded(
                child: FButton(
                  variant: _accountType == 'individual' ? .primary : .outline,
                  onPress: () => setState(() => _accountType = 'individual'),
                  child: Text(l10n.authIndividual),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FButton(
                  variant: _accountType == 'legal' ? .primary : .outline,
                  onPress: () => setState(() => _accountType = 'legal'),
                  child: Text(l10n.authLegal),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_accountType == 'individual')
            FTextField(
              control: FTextFieldControl.managed(controller: _fullName),
              label: Text(l10n.authFullNameOptional),
              textInputAction: TextInputAction.done,
            )
          else ...[
            _legalField(_companyName, l10n.authOrgName),
            _legalField(_inn, l10n.authInn, digits: true),
            _legalField(_ogrn, l10n.authOgrn, digits: true),
            _legalField(_legalAddress, l10n.authLegalAddress),
            _legalField(_directorName, l10n.authDirectorName),
            _legalField(_bankName, l10n.authBankName),
            _legalField(_bik, l10n.authBik, digits: true),
            _legalField(_checkingAccount, l10n.authCheckingAccount, digits: true),
          ],
        ];
      case _AuthStep.forgot:
        return [
          FTextField(
            control: FTextFieldControl.managed(controller: _email),
            label: Text(l10n.email),
            keyboardType: TextInputType.emailAddress,
            textInputAction: TextInputAction.done,
          ),
        ];
      case _AuthStep.resetConfirm:
        return [
          FTextField(
            control: FTextFieldControl.managed(controller: _resetToken),
            label: Text(l10n.authResetToken),
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 12),
          FTextField.password(
            control: FTextFieldControl.managed(controller: _newPassword),
            label: Text(l10n.authNewPasswordField),
            autofillHints: const [AutofillHints.newPassword],
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 12),
          FTextField.password(
            control: FTextFieldControl.managed(controller: _newPasswordConfirm),
            label: Text(l10n.authPasswordConfirm),
            autofillHints: const [AutofillHints.newPassword],
            textInputAction: TextInputAction.done,
          ),
        ];
      case _AuthStep.twoFa:
        return [
          FTextField(
            control: FTextFieldControl.managed(controller: _totp),
            label: Text(l10n.authAuthenticatorCode),
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            maxLength: 6,
            textInputAction: TextInputAction.done,
          ),
        ];
    }
  }

  Widget _legalField(TextEditingController c, String label, {bool digits = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: FTextField(
        control: FTextFieldControl.managed(controller: c),
        label: Text(label),
        keyboardType: digits ? TextInputType.number : TextInputType.text,
        inputFormatters: digits ? [FilteringTextInputFormatter.digitsOnly] : null,
        textInputAction: TextInputAction.next,
      ),
    );
  }

  List<Widget> _footer(AppLocalizations l10n) {
    switch (_step) {
      case _AuthStep.login:
        return [
          FButton(
            variant: .ghost,
            onPress: () => _setStep(_AuthStep.forgot),
            child: Text(l10n.forgotPassword),
          ),
          FButton(
            variant: .outline,
            onPress: () => _setStep(_AuthStep.register),
            child: Text(l10n.register),
          ),
        ];
      case _AuthStep.register:
        return [
          FButton(
            variant: .ghost,
            onPress: () => _setStep(_AuthStep.login),
            child: Text(l10n.alreadyHaveAccount),
          ),
        ];
      case _AuthStep.verifyEmail:
        return [
          FButton(
            variant: .ghost,
            onPress: () => _setStep(_AuthStep.register),
            child: Text(l10n.authBack),
          ),
        ];
      case _AuthStep.accountType:
        return [
          FButton(
            variant: .ghost,
            onPress: () => _setStep(_AuthStep.verifyEmail),
            child: Text(l10n.authBack),
          ),
        ];
      case _AuthStep.forgot:
        return [
          FButton(
            variant: .ghost,
            onPress: () => _setStep(_AuthStep.login),
            child: Text(l10n.authBackToLogin),
          ),
        ];
      case _AuthStep.resetConfirm:
        return [
          FButton(
            variant: .ghost,
            onPress: () => _setStep(_AuthStep.login),
            child: Text(l10n.authBackToLogin),
          ),
        ];
      case _AuthStep.twoFa:
        return [
          FButton(
            variant: .ghost,
            onPress: () => setState(() {
              _challengeToken = null;
              _totp.clear();
              _step = _AuthStep.login;
              _error = null;
            }),
            child: Text(l10n.authBack),
          ),
        ];
    }
  }
}
