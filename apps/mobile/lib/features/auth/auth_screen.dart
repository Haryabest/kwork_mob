import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/push_service.dart';

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

  @override
  void initState() {
    super.initState();
    _step = widget.initialMode == 'register' ? _AuthStep.register : _AuthStep.login;
  }

  @override
  void dispose() {
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
    if (!_consents) {
      setState(() => _error = 'Примите условия сервиса');
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
        const SnackBar(content: Text('Пароль обновлён. Войдите с новым паролем')),
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
        return 'Создайте аккаунт';
      case _AuthStep.verifyEmail:
        return 'Подтверждение email';
      case _AuthStep.accountType:
        return 'Тип аккаунта';
      case _AuthStep.forgot:
        return 'Восстановление пароля';
      case _AuthStep.resetConfirm:
        return 'Новый пароль';
      case _AuthStep.twoFa:
        return 'Введите код 2FA';
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
        return 'Подтвердить';
      case _AuthStep.accountType:
        return 'Продолжить';
      case _AuthStep.forgot:
        return 'Отправить ссылку';
      case _AuthStep.resetConfirm:
        return 'Сохранить пароль';
      case _AuthStep.twoFa:
        return 'Подтвердить';
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
                    Text('Dev-код: $_devCode', style: const TextStyle(color: AppColors.ozonPrimary)),
                  ],
                  if (_devResetToken != null && _step == _AuthStep.resetConfirm) ...[
                    const SizedBox(height: 8),
                    Text('Dev-токен: $_devResetToken', style: const TextStyle(color: AppColors.ozonPrimary)),
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
            label: const Text('Запомнить меня'),
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
            label: const Text('Подтверждение пароля'),
            autofillHints: const [AutofillHints.newPassword],
            textInputAction: TextInputAction.done,
          ),
          const SizedBox(height: 8),
          FCheckbox(
            value: _consents,
            onChange: (v) => setState(() => _consents = v),
            label: const Text(
              'Принимаю соглашение, политику ПДн, оферту, подтверждение прав и правила запрещённого контента',
            ),
          ),
        ];
      case _AuthStep.verifyEmail:
        return [
          FTextField(
            control: FTextFieldControl.managed(controller: _code),
            label: const Text('Код из письма (6 цифр)'),
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
                  child: const Text('Физ. лицо'),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FButton(
                  variant: _accountType == 'legal' ? .primary : .outline,
                  onPress: () => setState(() => _accountType = 'legal'),
                  child: const Text('Юр. лицо / ИП'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          if (_accountType == 'individual')
            FTextField(
              control: FTextFieldControl.managed(controller: _fullName),
              label: const Text('ФИО (необязательно)'),
              textInputAction: TextInputAction.done,
            )
          else ...[
            _legalField(_companyName, 'Наименование организации'),
            _legalField(_inn, 'ИНН', digits: true),
            _legalField(_ogrn, 'ОГРН / ОГРНИП', digits: true),
            _legalField(_legalAddress, 'Юридический адрес'),
            _legalField(_directorName, 'ФИО руководителя'),
            _legalField(_bankName, 'Банк'),
            _legalField(_bik, 'БИК', digits: true),
            _legalField(_checkingAccount, 'Расчётный счёт', digits: true),
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
            label: const Text('Токен из письма'),
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 12),
          FTextField.password(
            control: FTextFieldControl.managed(controller: _newPassword),
            label: const Text('Новый пароль'),
            autofillHints: const [AutofillHints.newPassword],
            textInputAction: TextInputAction.next,
          ),
          const SizedBox(height: 12),
          FTextField.password(
            control: FTextFieldControl.managed(controller: _newPasswordConfirm),
            label: const Text('Подтверждение пароля'),
            autofillHints: const [AutofillHints.newPassword],
            textInputAction: TextInputAction.done,
          ),
        ];
      case _AuthStep.twoFa:
        return [
          FTextField(
            control: FTextFieldControl.managed(controller: _totp),
            label: const Text('Код из Authenticator'),
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
            child: const Text('Уже есть аккаунт? Войти'),
          ),
        ];
      case _AuthStep.verifyEmail:
        return [
          FButton(
            variant: .ghost,
            onPress: () => _setStep(_AuthStep.register),
            child: const Text('Назад'),
          ),
        ];
      case _AuthStep.accountType:
        return [
          FButton(
            variant: .ghost,
            onPress: () => _setStep(_AuthStep.verifyEmail),
            child: const Text('Назад'),
          ),
        ];
      case _AuthStep.forgot:
        return [
          FButton(
            variant: .ghost,
            onPress: () => _setStep(_AuthStep.login),
            child: const Text('Назад ко входу'),
          ),
        ];
      case _AuthStep.resetConfirm:
        return [
          FButton(
            variant: .ghost,
            onPress: () => _setStep(_AuthStep.login),
            child: const Text('Назад ко входу'),
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
            child: const Text('Назад'),
          ),
        ];
    }
  }
}
