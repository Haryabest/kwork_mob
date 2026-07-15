import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/services/scale_calibration_service.dart';
import 'package:url_launcher/url_launcher.dart';

/// Калибровка масштаба §3.7 — карта / A4 / QR / ручной ввод.
class CalibrationWizardScreen extends StatefulWidget {
  const CalibrationWizardScreen({super.key, this.returnTo});

  /// Куда вернуться после успеха (optional).
  final String? returnTo;

  @override
  State<CalibrationWizardScreen> createState() => _CalibrationWizardScreenState();
}

class _CalibrationWizardScreenState extends State<CalibrationWizardScreen> {
  final _svc = ScaleCalibrationService.instance;
  String _method = 'card';
  final _widthFrac = TextEditingController(text: '0.55');
  final _heightFrac = TextEditingController(text: '0.35');
  final _w = TextEditingController(text: '0.40');
  final _h = TextEditingController(text: '0.30');
  final _d = TextEditingController(text: '0.25');
  final _qrSide = TextEditingController(text: '100');
  bool _busy = false;
  Map<String, dynamic>? _existing;

  @override
  void initState() {
    super.initState();
    _loadExisting();
  }

  Future<void> _loadExisting() async {
    final c = await _svc.load();
    if (!mounted) return;
    setState(() => _existing = c);
  }

  @override
  void dispose() {
    _widthFrac.dispose();
    _heightFrac.dispose();
    _w.dispose();
    _h.dispose();
    _d.dispose();
    _qrSide.dispose();
    super.dispose();
  }

  Future<void> _save(Map<String, dynamic> scale, String method) async {
    setState(() => _busy = true);
    try {
      await _svc.save(
        method: method,
        scaleCalibration: scale,
        referenceWidthM: method == 'card'
            ? ScaleCalibrationService.cardWidthM
            : method == 'a4'
                ? ScaleCalibrationService.a4WidthM
                : method == 'qr'
                    ? (double.tryParse(_qrSide.text) ?? 100) / 1000
                    : null,
      );
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Калибровка сохранена на 30 дней')),
      );
      if (widget.returnTo != null && widget.returnTo!.isNotEmpty) {
        context.go(widget.returnTo!);
      } else {
        context.pop(true);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _saveReference(String method, double refW, double refH) async {
    final wf = double.tryParse(_widthFrac.text.replaceAll(',', '.'));
    final hf = double.tryParse(_heightFrac.text.replaceAll(',', '.'));
    if (wf == null || hf == null || wf <= 0 || hf <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Укажите долю эталона в кадре (0.1–0.9)')),
      );
      return;
    }
    final scale = _svc.objectFromReference(
      refWidthM: refW,
      refHeightM: refH,
      objectWidthFraction: wf,
      objectHeightFraction: hf,
    );
    scale['calibration_method'] = method;
    await _save(scale, method);
  }

  Future<void> _saveManual() async {
    final width = double.tryParse(_w.text.replaceAll(',', '.'));
    final height = double.tryParse(_h.text.replaceAll(',', '.'));
    final depth = double.tryParse(_d.text.replaceAll(',', '.'));
    if (width == null || height == null || depth == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Введите размеры в метрах')),
      );
      return;
    }
    await _save(
      {
        'width': width,
        'height': height,
        'depth': depth,
        'calibration_method': 'manual',
      },
      'manual',
    );
  }

  @override
  Widget build(BuildContext context) {
    final exp = _existing;
    return FScaffold(
      header: FHeader.nested(
        title: const Text('Калибровка масштаба'),
        prefixes: [FHeaderAction.back(onPress: _busy ? null : () => context.pop())],
      ),
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (exp != null) ...[
            Text(
              'Текущая: ${exp['method']} · до ${(exp['expires_at']?.toString() ?? '').substring(0, 10)}',
              style: const TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 8),
            FButton(
              variant: .outline,
              onPress: _busy
                  ? null
                  : () async {
                      await _svc.clear();
                      await _loadExisting();
                    },
              child: const Text('Сбросить калибровку'),
            ),
            const SizedBox(height: 20),
          ],
          const Text(
            'Для опции «Масштаб 1:1» и мебели нужна калибровка (§3.7). '
            'Положите эталон рядом с товаром и укажите, какую долю кадра он занимает.',
          ),
          const SizedBox(height: 16),
          FSelect<String>(
            label: const Text('Способ'),
            control: FSelectControl.managed(
              initial: _method,
              onChange: (v) => setState(() => _method = v ?? 'card'),
            ),
            items: const {
              'Банковская карта (85.6×54 мм)': 'card',
              'Лист A4 (210×297 мм)': 'a4',
              'QR-код с PDF (100 мм)': 'qr',
              'Ручной ввод размеров (м)': 'manual',
            },
          ),
          const SizedBox(height: 16),
          if (_method == 'card' || _method == 'a4') ...[
            FTextField(
              control: FTextFieldControl.managed(controller: _widthFrac),
              label: const Text('Ширина эталона в кадре (0.1–0.9)'),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
            const SizedBox(height: 8),
            FTextField(
              control: FTextFieldControl.managed(controller: _heightFrac),
              label: const Text('Высота эталона в кадре (0.1–0.9)'),
              keyboardType: const TextInputType.numberWithOptions(decimal: true),
            ),
            const SizedBox(height: 12),
            FButton(
              onPress: _busy
                  ? null
                  : () => _saveReference(
                        _method,
                        _method == 'card'
                            ? ScaleCalibrationService.cardWidthM
                            : ScaleCalibrationService.a4WidthM,
                        _method == 'card'
                            ? ScaleCalibrationService.cardHeightM
                            : ScaleCalibrationService.a4HeightM,
                      ),
              child: const Text('Сохранить калибровку'),
            ),
          ],
          if (_method == 'qr') ...[
            const Text(
              'Скачайте PDF с QR-кодом эталона (100×100 мм), распечатайте и положите рядом с товаром.',
              style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
            ),
            const SizedBox(height: 8),
            FButton(
              variant: .outline,
              onPress: () async {
                final uri = Uri.parse('https://3d.app/calibration/qr.pdf');
                await launchUrl(uri, mode: LaunchMode.externalApplication);
              },
              child: const Text('Скачать PDF QR'),
            ),
            const SizedBox(height: 12),
            FTextField(
              control: FTextFieldControl.managed(controller: _qrSide),
              label: const Text('Сторона QR (мм)'),
              keyboardType: TextInputType.number,
              inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            ),
            const SizedBox(height: 8),
            FTextField(
              control: FTextFieldControl.managed(controller: _widthFrac),
              label: const Text('QR в кадре — ширина (доля)'),
            ),
            const SizedBox(height: 8),
            FTextField(
              control: FTextFieldControl.managed(controller: _heightFrac),
              label: const Text('QR в кадре — высота (доля)'),
            ),
            const SizedBox(height: 12),
            FButton(
              onPress: _busy
                  ? null
                  : () {
                      final sideMm = double.tryParse(_qrSide.text) ?? 100;
                      _saveReference('qr', sideMm / 1000, sideMm / 1000);
                    },
              child: const Text('Сохранить по QR'),
            ),
          ],
          if (_method == 'manual') ...[
            FTextField(
              control: FTextFieldControl.managed(controller: _w),
              label: const Text('Ширина товара (м)'),
            ),
            const SizedBox(height: 8),
            FTextField(
              control: FTextFieldControl.managed(controller: _h),
              label: const Text('Высота товара (м)'),
            ),
            const SizedBox(height: 8),
            FTextField(
              control: FTextFieldControl.managed(controller: _d),
              label: const Text('Глубина товара (м)'),
            ),
            const SizedBox(height: 12),
            FButton(onPress: _busy ? null : _saveManual, child: const Text('Сохранить')),
          ],
        ],
      ),
    );
  }
}
