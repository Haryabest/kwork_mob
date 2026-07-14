import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/services/push_service.dart';

class AuthScreen extends StatefulWidget {
  const AuthScreen({
    super.key,
    required this.api,
    required this.session,
    required this.push,
  });

  final ApiClient api;
  final AppSession session;
  final PushService push;

  @override
  State<AuthScreen> createState() => _AuthScreenState();
}

class _AuthScreenState extends State<AuthScreen> {
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _totp = TextEditingController();
  bool _loading = false;
  String? _error;
  String? _challengeToken;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _totp.dispose();
    super.dispose();
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
    if (mounted) context.go('/home');
  }

  Future<void> _submit() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      if (_challengeToken != null) {
        await widget.api.verifyLogin2fa(
          challengeToken: _challengeToken!,
          code: _totp.text.trim(),
        );
        await _finishLogin();
        return;
      }
      final data = await widget.api.login(_email.text.trim(), _password.text);
      if (data['requires_2fa'] == true) {
        setState(() {
          _challengeToken = data['challenge_token']?.toString();
          _loading = false;
        });
        return;
      }
      await _finishLogin();
    } on DioException catch (e) {
      setState(() => _error = e.response?.data?['detail']?.toString() ?? e.message);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final need2fa = _challengeToken != null;
    return FScaffold(
      child: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 420),
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    l10n.appName,
                    style: context.theme.typography.xl2.copyWith(fontWeight: FontWeight.bold),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    need2fa ? 'Введите код 2FA' : l10n.authTitle,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: AppColors.textSecondary),
                  ),
                  const SizedBox(height: 32),
                  if (!need2fa) ...[
                    TextField(
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      decoration: InputDecoration(
                        labelText: l10n.email,
                        border: const OutlineInputBorder(),
                      ),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _password,
                      obscureText: true,
                      decoration: InputDecoration(
                        labelText: l10n.password,
                        border: const OutlineInputBorder(),
                      ),
                    ),
                  ] else
                    TextField(
                      controller: _totp,
                      keyboardType: TextInputType.number,
                      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                      maxLength: 6,
                      decoration: const InputDecoration(
                        labelText: 'Код из Authenticator',
                        border: OutlineInputBorder(),
                        counterText: '',
                      ),
                    ),
                  if (_error != null) ...[
                    const SizedBox(height: 12),
                    Text(_error!, style: const TextStyle(color: AppColors.error)),
                  ],
                  const SizedBox(height: 20),
                  FButton(
                    onPress: _loading ? null : _submit,
                    child: Text(_loading ? '…' : (need2fa ? 'Подтвердить' : l10n.continueBtn)),
                  ),
                  if (need2fa)
                    TextButton(
                      onPressed: () => setState(() {
                        _challengeToken = null;
                        _totp.clear();
                        _error = null;
                      }),
                      child: const Text('Назад'),
                    ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
