import 'dart:io';

import 'package:camera/camera.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';
import 'package:kwork_mobile/l10n/app_localizations.dart';
import 'package:kwork_mobile/l10n/guided_dome_l10n.dart';
import 'package:kwork_mobile/core/ar/ar.dart';
import 'package:kwork_mobile/core/ar/native_ar_bridge.dart';
import 'package:kwork_mobile/services/ar_tariff.dart';
import 'package:kwork_mobile/services/device_benchmark.dart';
import 'package:kwork_mobile/services/gyro_guide.dart';
import 'package:kwork_mobile/services/quality_analyzer.dart';
import 'package:kwork_mobile/services/analytics_service.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';
import 'package:kwork_mobile/services/cloud_draft_backup_service.dart';
import 'package:kwork_mobile/services/thermal_monitor.dart';
import 'package:kwork_mobile/widgets/native_ar_preview.dart';
import 'package:kwork_mobile/widgets/ar_markers_overlay.dart';
import 'package:kwork_mobile/widgets/ghost_mesh.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:vibration/vibration.dart';

/// Debug/emulator: `flutter run --dart-define=SHOOT_BYPASS_QUALITY=true`
bool get _bypassQualityGate =>
    kDebugMode || const bool.fromEnvironment('SHOOT_BYPASS_QUALITY');

/// Debug/emulator: `flutter run --dart-define=SHOOT_BYPASS_GYRO=true`
bool get _bypassGyroGate =>
    kDebugMode || const bool.fromEnvironment('SHOOT_BYPASS_GYRO');

/// Guided Dome: камера + AR-абстракция (ARKit/ARCore или gyro) ±15° (§3.1 / §3.2).
class GuidedDomeScreen extends StatefulWidget {
  const GuidedDomeScreen({
    super.key,
    required this.modelUuid,
    this.reshootIndex,
    this.flowBase = '/home/shoot',
    this.api,
  });

  final String modelUuid;
  final int? reshootIndex;
  /// Префикс маршрута: `/home/shoot` или `/shoot/{token}`.
  final String flowBase;
  final ApiClient? api;

  @override
  State<GuidedDomeScreen> createState() => _GuidedDomeScreenState();
}

class _GuidedDomeScreenState extends State<GuidedDomeScreen> {
  CameraController? _cam;
  CameraDescription? _cameraDesc;
  ArSession? _ar;
  GyroGuide? _gyro;
  ArBackend _arBackend = ArBackend.gyroFallback;
  final _thermal = ThermalMonitor();
  int _index = 0;
  bool _busy = false;
  bool _ready = false;
  String? _error;
  String? _gateMsg;
  bool _crosshairOk = true;
  bool _gyroOk = true;
  bool _arTariffApplied = false;
  bool _criticalDialogOpen = false;
  bool _thermalLowRes = false;
  DateTime? _lastShutterAt;
  ProductCategory _category = ProductCategory.other;
  double _ghostScale = 1.0;
  File? _prevFrame;
  double _yawOffsetDeg = 0;
  int? _arTextureId;
  bool _nativeCamera = false;

  @override
  void initState() {
    super.initState();
    AnalyticsService.instance.track('screen_view', {'screen': 'shoot_dome'});
    _index = widget.reshootIndex ?? 0;
    _loadDraftMeta();
    _boot();
  }

  Future<void> _loadDraftMeta() async {
    final draft = await ShootStorage.instance.loadDraft(widget.modelUuid);
    if (draft == null) return;
    if (!mounted) return;
    setState(() {
      _category = draft.category;
      _ghostScale = draft.ghostScale;
    });
    await _loadPrevFrame();
  }

  Future<void> _loadPrevFrame() async {
    if (_index <= 0) {
      if (mounted) setState(() => _prevFrame = null);
      return;
    }
    final prev = await ShootStorage.instance.photoFile(widget.modelUuid, _index - 1);
    if (await prev.exists()) {
      if (mounted) setState(() => _prevFrame = prev);
    }
  }

  Future<void> _persistGhostScale() async {
    final draft = await ShootStorage.instance.loadDraft(widget.modelUuid);
    if (draft == null) return;
    draft.ghostScale = _ghostScale;
    await ShootStorage.instance.writeMetadata(draft);
  }

  Future<void> _boot() async {
    final cam = await Permission.camera.request();
    if (!cam.isGranted) {
      if (mounted) {
        setState(() => _error = AppLocalizations.of(context)!.gdCameraRequired);
      }
      return;
    }
    try {
      final cameras = await availableCameras();
      final back = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );
      _cameraDesc = back;
      final nativeFirst = await ArSessionFactory.create(preferNative: true);
      final nativeOk = nativeFirst.backend != ArBackend.gyroFallback;
      if (!nativeOk) {
        await DeviceBenchmark.instance.loadPersisted();
        await _openCamera(
          back,
          DeviceBenchmark.instance.cameraPreset,
        );
      }
      if (!mounted) return;
      await _thermal.start();
      _thermal.addListener(_onThermal);
      try {
        _ar = nativeFirst;
        _arBackend = _ar!.backend;
        if (nativeOk) {
          final started = await _ar!.start();
          if (started) {
            _ar!.addListener(_onArUpdate);
            if (_ar is NativeArBridge) {
              final bridge = _ar as NativeArBridge;
              _arTextureId = bridge.textureId;
              _nativeCamera = true;
              _gyro = GyroGuide()..start()..calibrateYaw();
              _gyro!.addListener(_onArUpdate);
            }
          } else {
            _ar = null;
            await DeviceBenchmark.instance.loadPersisted();
            await _openCamera(back, DeviceBenchmark.instance.cameraPreset);
          }
        } else {
          _gyro = (_ar as GyroArSession).guide;
          _gyro!.addListener(_onArUpdate);
        }
      } catch (_) {
        _ensureGyro();
        if (_cam == null) {
          await DeviceBenchmark.instance.loadPersisted();
          await _openCamera(back, DeviceBenchmark.instance.cameraPreset);
        }
      }
      _ready = true;
      setState(() {});
      await _syncNativeMarker();
    } catch (e) {
      _ensureGyro();
      if (_cam != null && _cam!.value.isInitialized) {
        _ready = true;
        if (mounted) setState(() => _error = null);
        return;
      }
      setState(() => _error = formatApiError(e));
    }
  }

  void _ensureGyro() {
    if (_gyro != null) return;
    _gyro = GyroGuide()..start()..calibrateYaw();
    _gyro!.addListener(_onArUpdate);
    _arBackend = ArBackend.gyroFallback;
  }

  bool get _usesNativeAr =>
      _ar != null && _ar!.backend != ArBackend.gyroFallback;

  void _onArUpdate() {
    if (!mounted) return;
    final l10n = AppLocalizations.of(context)!;
    final angle = kGuidedDomeAngles[_index];
    if (_usesNativeAr) {
      final ok = _ar!.isAligned(
        targetYawDeg: angle.azimuthDeg,
        targetPitchDeg: angle.elevationDeg,
      );
      setState(() {
        _gyroOk = ok;
        _yawOffsetDeg = 0;
        if (!ok) {
          _gateMsg = l10n.gdTurnToMarker(
            '${angle.azimuthDeg.round()}',
            '${angle.elevationDeg.round()}',
          );
        } else {
          _gateMsg = null;
        }
      });
      _maybeApplyArTariff();
      return;
    }
    if (_gyro == null) return;
    final check = _gyro!.check(angle, l10n);
    setState(() {
      _gyroOk = check.ok;
      _yawOffsetDeg = check.deltaYawDeg;
      if (!check.ok) _gateMsg = check.hint;
    });
    _maybeApplyArTariff();
  }

  Future<void> _openCamera(CameraDescription desc, ResolutionPreset preset) async {
    final old = _cam;
    _cam = null;
    await old?.dispose();
    final ctrl = CameraController(
      desc,
      preset,
      enableAudio: false,
      imageFormatGroup: ImageFormatGroup.jpeg,
    );
    await ctrl.initialize();
    if (!mounted) {
      await ctrl.dispose();
      return;
    }
    _cam = ctrl;
  }

  ResolutionPreset _cameraPresetForThermal() {
    if (!_thermal.powerSave) {
      return DeviceBenchmark.instance.cameraPreset;
    }
    final base = DeviceBenchmark.instance.cameraPreset;
    if (base == ResolutionPreset.low) return ResolutionPreset.low;
    return ResolutionPreset.medium;
  }

  void _onThermal() {
    if (!mounted) return;
    _applyThermalCamera();
    setState(() {});
    if (_thermal.needsCriticalPrompt && !_criticalDialogOpen) {
      _showCriticalThermalDialog();
    }
  }

  Future<void> _applyThermalCamera() async {
    final wantLow = _thermal.powerSave;
    if (wantLow != _thermalLowRes && _cameraDesc != null) {
      _thermalLowRes = wantLow;
      final preset = _cameraPresetForThermal();
      await _openCamera(_cameraDesc!, preset);
      if (mounted) setState(() {});
      return;
    }
    final cam = _cam;
    if (cam == null || !cam.value.isInitialized) return;
    try {
      await cam.setExposureMode(ExposureMode.auto);
      if (wantLow) {
        await cam.lockCaptureOrientation();
      }
    } catch (_) {}
  }

  Future<void> _showCriticalThermalDialog() async {
    _criticalDialogOpen = true;
    final temp = _thermal.celsius?.toStringAsFixed(0) ?? '45+';
    final l10n = AppLocalizations.of(context)!;
    final cont = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => AlertDialog(
        title: Text(l10n.shootOverheatTitle),
        content: Text(l10n.shootOverheatBody(temp)),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(l10n.shootAbort),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(l10n.continueBtn),
          ),
        ],
      ),
    );
    _criticalDialogOpen = false;
    if (!mounted) return;
    if (cont == true) {
      _thermal.acknowledgeCriticalContinue();
    } else {
      context.pop();
    }
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

  bool get _canShoot {
    if (!_ready || _busy) return false;
    if (!_nativeCamera && _cam == null) return false;
    if (_bypassGyroGate) return true;
    if (_usesNativeAr) {
      final angle = kGuidedDomeAngles[_index];
      return _ar!.isAligned(
        targetYawDeg: angle.azimuthDeg,
        targetPitchDeg: angle.elevationDeg,
      );
    }
    return _gyroOk && _gyro != null;
  }

  Future<void> _shutter() async {
    if (!_canShoot) return;
    if (!_nativeCamera && _cam == null) return;
    if (!_bypassGyroGate && !_usesNativeAr && _gyro == null) return;
    final l10n = AppLocalizations.of(context)!;
    final minGap = Duration(milliseconds: (1000 / _thermal.targetFps).round());
    final last = _lastShutterAt;
    if (last != null && DateTime.now().difference(last) < minGap) {
      setState(() => _gateMsg = l10n.gdFpsWait('${_thermal.targetFps}'));
      return;
    }
    if (!_bypassGyroGate) {
      if (_usesNativeAr) {
        final angle = kGuidedDomeAngles[_index];
        if (!_ar!.isAligned(
          targetYawDeg: angle.azimuthDeg,
          targetPitchDeg: angle.elevationDeg,
        )) {
          setState(() => _gateMsg = l10n.gdAlignMarker);
          return;
        }
      } else {
        final gyro = _gyro?.check(kGuidedDomeAngles[_index], l10n);
        if (gyro != null && !gyro.ok) {
          setState(() => _gateMsg = gyro.hint);
          return;
        }
      }
    }
    setState(() => _busy = true);
    try {
      _lastShutterAt = DateTime.now();
      late List<int> bytes;
      if (_nativeCamera && _ar is NativeArBridge) {
        final raw = await (_ar as NativeArBridge).capturePhoto();
        if (raw == null) throw StateError('AR capture failed');
        bytes = raw;
      } else {
        final shot = await _cam!.takePicture();
        bytes = await File(shot.path).readAsBytes();
        await File(shot.path).delete().catchError((_) => File(shot.path));
      }
      final gate = QualityAnalyzer.instance.liveGate(bytes, l10n);
      if (!_bypassQualityGate && (!gate.centered || !gate.fillOk)) {
        setState(() {
          _busy = false;
          _crosshairOk = false;
          _gateMsg = gate.message;
        });
        return;
      }
      await ShootStorage.instance.savePhoto(widget.modelUuid, _index, bytes);
      final draft = await ShootStorage.instance.loadDraft(widget.modelUuid);
      if (draft != null && widget.api != null) {
        try {
          await CloudDraftBackupService.instance.syncDraft(widget.api!, draft);
        } catch (_) {}
      }

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
          setState(() => _busy = false);
          await AnalyticsService.instance.track('shoot_complete', {
            'model_uuid': widget.modelUuid,
            'frames': kGuidedDomeCount,
          });
          context.pushReplacement(
            '${widget.flowBase}/review',
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
      await _loadPrevFrame();
      await _syncNativeMarker();
      _ar?.calibrate();
      _gyro?.calibrateYaw();
    } catch (e) {
      setState(() {
        _busy = false;
        _error = formatApiError(e);
      });
    }
  }

  /// Debug: снять кадр без гиро/quality (эмулятор).
  Future<void> _devForceCapture() async {
    if (!kDebugMode || !_ready || _cam == null || _busy) return;
    setState(() => _busy = true);
    try {
      final shot = await _cam!.takePicture();
      final bytes = await File(shot.path).readAsBytes();
      await ShootStorage.instance.savePhoto(widget.modelUuid, _index, bytes);
      await File(shot.path).delete().catchError((_) => File(shot.path));
      if (widget.reshootIndex != null) {
        if (mounted) context.pop(true);
        return;
      }
      if (_index >= kGuidedDomeCount - 1) {
        if (mounted) {
          setState(() => _busy = false);
          await AnalyticsService.instance.track('shoot_complete', {
            'model_uuid': widget.modelUuid,
            'frames': kGuidedDomeCount,
          });
          context.pushReplacement('${widget.flowBase}/review', extra: widget.modelUuid);
        }
        return;
      }
      setState(() {
        _index++;
        _busy = false;
        _gateMsg = null;
      });
      await _loadPrevFrame();
      await _syncNativeMarker();
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = formatApiError(e);
        });
      }
    }
  }

  Future<void> _syncNativeMarker() async {
    final ar = _ar;
    if (ar is! NativeArBridge) return;
    final angle = kGuidedDomeAngles[_index];
    await ar.showMarker(
      index: _index,
      azimuthDeg: angle.azimuthDeg,
      elevationDeg: angle.elevationDeg,
    );
  }

  @override
  void dispose() {
    _thermal.removeListener(_onThermal);
    _thermal.dispose();
    _ar?.removeListener(_onArUpdate);
    _ar?.dispose();
    _gyro?.removeListener(_onArUpdate);
    _gyro?.dispose();
    _cam?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context)!;
    final angle = kGuidedDomeAngles[_index];
    final gyro = _gyro?.check(angle, l10n);
    final backendLabel = switch (_arBackend) {
      ArBackend.nativeArKit => 'ARKit',
      ArBackend.nativeArCore => 'ARCore',
      ArBackend.gyroFallback => 'Gyro',
    };

    if (_error != null) {
      return FScaffold(
        header: FHeader.nested(title: Text(l10n.shootTitle), prefixes: [
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
            if (_arTextureId != null)
              Center(child: NativeArPreview(textureId: _arTextureId!))
            else if (_nativeCamera)
              Center(
                child: Text(
                  l10n.shootArCameraActive,
                  style: TextStyle(color: Colors.white70),
                ),
              )
            else if (_cam != null && _cam!.value.isInitialized)
              Center(child: CameraPreview(_cam!))
            else
              const Center(child: CircularProgressIndicator()),
            // §3.2.3 — полупрозрачный силуэт предыдущего кадра
            if (_prevFrame != null)
              IgnorePointer(
                child: Center(
                  child: Opacity(
                    opacity: 0.35,
                    child: Image.file(
                      _prevFrame!,
                      fit: BoxFit.cover,
                      width: double.infinity,
                      height: double.infinity,
                    ),
                  ),
                ),
              ),
            // AR-метки 12 ракурсов (§3.1.2)
            if (!_thermal.effectsReduced)
              IgnorePointer(
                child: ArMarkersOverlay(
                  currentIndex: _index,
                  yawOffsetDeg: _yawOffsetDeg,
                ),
              ),
            // Ghost Mesh §3.11
            if (!_thermal.effectsReduced)
              GhostMeshOverlay(
                category: _category,
                scale: _ghostScale,
                aligned: _crosshairOk && _gyroOk,
                onScaleUpdate: (s) {
                  setState(() => _ghostScale = s);
                  _persistGhostScale();
                },
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
                    '${l10n.shootAngleLine('${_index + 1}', '$kGuidedDomeCount', domeAngleLabel(l10n, _index), backendLabel)}'
                    '${_thermal.powerSave ? ' · FPS ${_thermal.targetFps}' : ''}'
                    '${_thermal.celsius != null ? ' · ${_thermal.celsius!.toStringAsFixed(0)}°C' : ''}'
                    '${_bypassQualityGate ? ' · DEV' : ''}'
                    '${_bypassGyroGate ? '' : ''}',
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
                    child: Text(l10n.shootExit),
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
                            ? AppColors.accent
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
                    child: Text(l10n.shootCalibrateShort),
                  ),
                  if (kDebugMode)
                    FButton(
                      variant: .ghost,
                      onPress: _devForceCapture,
                      child: const Text('DEV'),
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
