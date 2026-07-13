import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';
import 'package:kwork_mobile/core/ar/ar.dart';
import 'package:kwork_mobile/core/ar/gyro_ar_session.dart';
import 'package:kwork_mobile/services/ar_tariff.dart';
import 'package:kwork_mobile/services/device_benchmark.dart';
import 'package:kwork_mobile/services/gyro_guide.dart';
import 'package:kwork_mobile/services/quality_analyzer.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:vibration/vibration.dart';

/// Guided Dome: камера + AR-абстракция (ARKit/ARCore или gyro) ±15° (§3.1 / §3.2).
class GuidedDomeScreen extends StatefulWidget {
  const GuidedDomeScreen({
    super.key,
    required this.modelUuid,
    this.reshootIndex,
  });

  final String modelUuid;
  final int? reshootIndex;

  @override
  State<GuidedDomeScreen> createState() => _GuidedDomeScreenState();
}

class _GuidedDomeScreenState extends State<GuidedDomeScreen> {
  CameraController? _cam;
  ArSession? _ar;
  GyroGuide? _gyro;
  ArBackend _arBackend = ArBackend.gyroFallback;
  int _index = 0;
  bool _busy = false;
  bool _ready = false;
  String? _error;
  String? _gateMsg;
  bool _crosshairOk = true;
  bool _gyroOk = true;
  bool _arTariffApplied = false;

  @override
  void initState() {
    super.initState();
    _index = widget.reshootIndex ?? 0;
    _boot();
  }

  Future<void> _boot() async {
    final cam = await Permission.camera.request();
    if (!cam.isGranted) {
      setState(() => _error = 'Нужен доступ к камере');
      return;
    }
    try {
      final cameras = await availableCameras();
      final back = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );
      await DeviceBenchmark.instance.loadPersisted();
      final ctrl = CameraController(
        back,
        DeviceBenchmark.instance.cameraPreset,
        enableAudio: false,
        imageFormatGroup: ImageFormatGroup.jpeg,
      );
      await ctrl.initialize();
      if (!mounted) return;
      _cam = ctrl;
      _ar = await ArSessionFactory.create(preferNative: true);
      _arBackend = _ar!.backend;
      await _ar!.start();
      _ar!.addListener(_onGyro);
      if (_ar is GyroArSession) {
        _gyro = (_ar as GyroArSession).guide;
      } else {
        // native AR: гиро-подсказки через тот же GyroGuide для UI-хинтов
        _gyro = GyroGuide()..start()..calibrateYaw();
        _gyro!.addListener(_onGyro);
      }
      _ready = true;
      setState(() {});
    } catch (e) {
      setState(() => _error = e.toString());
    }
  }

  void _onGyro() {
    if (!mounted || _gyro == null) return;
    final check = _gyro!.check(kGuidedDomeAngles[_index]);
    setState(() {
      _gyroOk = check.ok;
      if (!check.ok) _gateMsg = check.hint;
    });
    _maybeApplyArTariff();
  }

  Future<void> _maybeApplyArTariff() async {
    if (_arTariffApplied) return;
    final pose = _ar?.pose;
    final hint = hintFromArPose(pose);
    if (hint == null) return;
    _arTariffApplied = true;
    final draft = await ShootStorage.instance.loadDraft(widget.modelUuid);
    if (draft == null) return;
    draft.tier = hint.tier;
    draft.scaleCalibration = hint.scaleCalibration;
    await ShootStorage.instance.writeMetadata(draft);
  }

  bool get _canShoot => _ready && !_busy && _gyroOk && _gyro != null;

  Future<void> _shutter() async {
    if (!_canShoot || _cam == null || _gyro == null) return;
    final gyro = _gyro!.check(kGuidedDomeAngles[_index]);
    if (!gyro.ok) {
      setState(() => _gateMsg = gyro.hint);
      return;
    }
    setState(() => _busy = true);
    try {
      final shot = await _cam!.takePicture();
      final bytes = await File(shot.path).readAsBytes();
      final gate = QualityAnalyzer.instance.liveGate(bytes);
      if (!gate.centered || !gate.fillOk) {
        await File(shot.path).delete().catchError((_) => File(shot.path));
        setState(() {
          _busy = false;
          _crosshairOk = false;
          _gateMsg = gate.message;
        });
        return;
      }
      await ShootStorage.instance.savePhoto(widget.modelUuid, _index, bytes);
      await File(shot.path).delete().catchError((_) => File(shot.path));

      if (await Vibration.hasVibrator()) {
        await Vibration.vibrate(duration: 40);
      }
      await SystemSound.play(SystemSoundType.click);

      if (widget.reshootIndex != null) {
        if (mounted) context.pop(true);
        return;
      }

      if (_index >= kGuidedDomeCount - 1) {
        if (mounted) {
          context.pushReplacement(
            '/home/shoot/review',
            extra: widget.modelUuid,
          );
        }
        return;
      }
      setState(() {
        _index++;
        _busy = false;
        _crosshairOk = true;
        _gateMsg = null;
      });
      _ar?.calibrate();
      _gyro?.calibrateYaw();
    } catch (e) {
      setState(() {
        _busy = false;
        _error = e.toString();
      });
    }
  }

  @override
  void dispose() {
    _ar?.removeListener(_onGyro);
    _ar?.dispose();
    _gyro?.removeListener(_onGyro);
    _gyro?.dispose();
    _cam?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final angle = kGuidedDomeAngles[_index];
    final gyro = _gyro?.check(angle);
    final backendLabel = switch (_arBackend) {
      ArBackend.nativeArKit => 'ARKit',
      ArBackend.nativeArCore => 'ARCore',
      ArBackend.gyroFallback => 'Gyro',
    };

    if (_error != null) {
      return FScaffold(
        header: FHeader.nested(title: const Text('Съёмка'), prefixes: [
          FHeaderAction.back(onPress: () => context.pop()),
        ]),
        child: Center(child: Text(_error!)),
      );
    }

    return Scaffold(
      backgroundColor: Colors.black,
      body: SafeArea(
        child: Stack(
          fit: StackFit.expand,
          children: [
            if (_cam != null && _cam!.value.isInitialized)
              Center(child: CameraPreview(_cam!))
            else
              const Center(child: CircularProgressIndicator()),
            // Ghost Mesh — полупрозрачный овал (§3.11)
            IgnorePointer(
              child: Center(
                child: Container(
                  width: MediaQuery.sizeOf(context).width * 0.55,
                  height: MediaQuery.sizeOf(context).height * 0.45,
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: (_crosshairOk ? AppColors.success : AppColors.error)
                          .withValues(alpha: 0.7),
                      width: 2,
                    ),
                    borderRadius: BorderRadius.circular(24),
                    color: Colors.white.withValues(alpha: 0.08),
                  ),
                ),
              ),
            ),
            // Перекрестие §3.1.3
            IgnorePointer(
              child: CustomPaint(
                painter: _CrosshairPainter(
                  color: _crosshairOk ? Colors.white : AppColors.error,
                ),
                child: const SizedBox.expand(),
              ),
            ),
            // Мини-карта 12 сегментов §3.1.4
            Positioned(
              top: 12,
              left: 0,
              right: 0,
              child: Column(
                children: [
                  Text(
                    'Ракурс ${_index + 1}/$kGuidedDomeCount · ${angle.label} · $backendLabel',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 8),
                  _DomeMap(current: _index, modelUuid: widget.modelUuid),
                ],
              ),
            ),
            Positioned(
              left: 16,
              right: 16,
              bottom: 120,
              child: Column(
                children: [
                  if (_gateMsg != null || (gyro?.hint != null))
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.black54,
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        _gateMsg ?? gyro?.hint ?? '',
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.white),
                      ),
                    ),
                ],
              ),
            ),
            Positioned(
              left: 16,
              right: 16,
              bottom: 24,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  FButton(
                    variant: .outline,
                    onPress: () => context.pop(),
                    child: const Text('Выход'),
                  ),
                  GestureDetector(
                    onTap: _canShoot ? _shutter : null,
                    child: Container(
                      width: 76,
                      height: 76,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 4),
                        color: _canShoot
                            ? AppColors.wbPrimary
                            : Colors.grey.shade600,
                      ),
                      child: _busy
                          ? const Padding(
                              padding: EdgeInsets.all(20),
                              child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                            )
                          : null,
                    ),
                  ),
                  FButton(
                    variant: .ghost,
                    onPress: () {
                      _ar?.calibrate();
                      _gyro?.calibrateYaw();
                    },
                    child: const Text('Калибр.'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DomeMap extends StatelessWidget {
  const _DomeMap({required this.current, required this.modelUuid});
  final int current;
  final String modelUuid;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<File?>>(
      future: ShootStorage.instance.listPhotos(modelUuid),
      builder: (context, snap) {
        final photos = snap.data ?? List<File?>.filled(12, null);
        return SizedBox(
          height: 56,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: List.generate(12, (i) {
              final done = photos[i] != null || i < current;
              final active = i == current;
              return Container(
                width: 18,
                height: 18,
                margin: const EdgeInsets.symmetric(horizontal: 2),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: done
                      ? AppColors.success
                      : active
                          ? AppColors.warning
                          : Colors.white24,
                  border: active ? Border.all(color: Colors.white, width: 2) : null,
                ),
                child: Center(
                  child: Text(
                    '${i + 1}',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 8,
                      fontWeight: active ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                ),
              );
            }),
          ),
        );
      },
    );
  }
}

class _CrosshairPainter extends CustomPainter {
  _CrosshairPainter({required this.color});
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()
      ..color = color
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke;
    final c = Offset(size.width / 2, size.height / 2);
    const arm = 28.0;
    canvas.drawLine(Offset(c.dx - arm, c.dy), Offset(c.dx + arm, c.dy), p);
    canvas.drawLine(Offset(c.dx, c.dy - arm), Offset(c.dx, c.dy + arm), p);
    canvas.drawCircle(c, 22, p);
  }

  @override
  bool shouldRepaint(covariant _CrosshairPainter old) => old.color != color;
}
