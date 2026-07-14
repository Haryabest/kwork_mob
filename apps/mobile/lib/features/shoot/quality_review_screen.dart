import 'dart:io';

import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/guided_dome.dart';
import 'package:kwork_mobile/services/quality_analyzer.dart';
import 'package:kwork_mobile/services/shoot_storage.dart';

/// Проверка качества 12 кадров (§3.9).
class QualityReviewScreen extends StatefulWidget {
  const QualityReviewScreen({
    super.key,
    required this.modelUuid,
    this.flowBase = '/home/shoot',
  });

  final String modelUuid;
  /// Префикс маршрута: `/home/shoot` или `/shoot/{token}`.
  final String flowBase;

  @override
  State<QualityReviewScreen> createState() => _QualityReviewScreenState();
}

class _QualityReviewScreenState extends State<QualityReviewScreen> {
  List<FrameQuality> _results = [];
  bool _loading = true;
  Map<int, int> _reshoots = {};
  String? _arHint;

  @override
  void initState() {
    super.initState();
    _analyze();
  }

  Future<void> _analyze() async {
    setState(() => _loading = true);
    final draft = await ShootStorage.instance.loadDraft(widget.modelUuid);
    _reshoots = Map.of(draft?.reshootCounts ?? {});
    if (draft?.scaleCalibration != null) {
      final t = draft!.tier;
      _arHint =
          'AR: тариф «${t.label}», габариты ${draft.scaleCalibration}';
    }
    final photos = await ShootStorage.instance.listPhotos(widget.modelUuid);
    final results = <FrameQuality>[];
    for (var i = 0; i < kGuidedDomeCount; i++) {
      final f = photos[i];
      if (f == null) {
        results.add(FrameQuality(index: i, verdict: FrameVerdict.fail, blurry: true));
      } else {
        results.add(await QualityAnalyzer.instance.analyzeFile(i, f));
      }
    }
    if (!mounted) return;
    setState(() {
      _results = results;
      _loading = false;
    });
  }

  Future<void> _reshoot(int index) async {
    final count = _reshoots[index] ?? 0;
    if (count >= kMaxReshootIterations) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Низкое качество фото. Постарайтесь улучшить условия съемки'),
        ),
      );
      return;
    }
    final ok = await context.push<bool>(
      '${widget.flowBase}/dome',
      extra: {'uuid': widget.modelUuid, 'reshoot': index},
    );
    if (ok == true) {
      _reshoots[index] = count + 1;
      final draft = await ShootStorage.instance.loadActiveDraft();
      if (draft != null) {
        draft.reshootCounts = _reshoots;
        await ShootStorage.instance.writeMetadata(draft);
      }
      await _analyze();
    }
  }

  Future<void> _continue({required bool force}) async {
    final fails = _results.where((e) => e.verdict == FrameVerdict.fail).length;
    if (fails > 0 && !force) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Низкое качество'),
          content: const Text(
            'Некоторые кадры имеют низкое качество, это может привести к браку модели. Продолжить?',
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Нет')),
            TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Да')),
          ],
        ),
      );
      if (ok != true) return;
    }

    final blocked = _results.any((e) {
      final n = _reshoots[e.index] ?? 0;
      return e.verdict == FrameVerdict.fail && n >= kMaxReshootIterations;
    });
    if (blocked && !force) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Низкое качество фото. Постарайтесь улучшить условия съемки'),
        ),
      );
      return;
    }

    if (!mounted) return;
    context.push('${widget.flowBase}/upload', extra: widget.modelUuid);
  }

  @override
  Widget build(BuildContext context) {
    return FScaffold(
      header: FHeader.nested(
        title: const Text('Проверка качества'),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
      ),
      child: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(
              children: [
                if (_arHint != null)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
                    child: Text(
                      _arHint!,
                      style: TextStyle(color: AppColors.textSecondary, fontSize: 13),
                    ),
                  ),
                Expanded(
                  child: GridView.builder(
                    padding: const EdgeInsets.all(12),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: 3,
                      crossAxisSpacing: 8,
                      mainAxisSpacing: 8,
                    ),
                    itemCount: _results.length,
                    itemBuilder: (context, i) {
                      final q = _results[i];
                      return FutureBuilder<File?>(
                        future: ShootStorage.instance.photoFile(widget.modelUuid, i).then(
                              (f) async => await f.exists() ? f : null,
                            ),
                        builder: (context, snap) {
                          final pass = q.verdict == FrameVerdict.pass;
                          return InkWell(
                            onTap: () => _reshoot(i),
                            child: Container(
                              decoration: BoxDecoration(
                                border: Border.all(
                                  color: pass ? AppColors.success : AppColors.error,
                                  width: 3,
                                ),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Stack(
                                fit: StackFit.expand,
                                children: [
                                  if (snap.data != null)
                                    ClipRRect(
                                      borderRadius: BorderRadius.circular(5),
                                      child: Image.file(snap.data!, fit: BoxFit.cover),
                                    )
                                  else
                                    const ColoredBox(color: Colors.black12),
                                  Positioned(
                                    left: 4,
                                    top: 4,
                                    child: Text(
                                      '${i + 1}',
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                        shadows: [Shadow(blurRadius: 4)],
                                      ),
                                    ),
                                  ),
                                  if (!pass)
                                    Positioned(
                                      bottom: 4,
                                      left: 4,
                                      right: 4,
                                      child: Text(
                                        q.reason,
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(color: Colors.white, fontSize: 10),
                                      ),
                                    ),
                                ],
                              ),
                            ),
                          );
                        },
                      );
                    },
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      FButton(
                        onPress: () => _continue(force: false),
                        child: const Text('Продолжить к загрузке'),
                      ),
                      const SizedBox(height: 8),
                      FButton(
                        variant: .outline,
                        onPress: () => _continue(force: true),
                        child: const Text('Продолжить, несмотря на ошибки'),
                      ),
                      const SizedBox(height: 8),
                      FButton(
                        variant: .ghost,
                        onPress: () => context.pushReplacement(
                          '${widget.flowBase}/dome',
                          extra: widget.modelUuid,
                        ),
                        child: const Text('Начать съёмку с начала'),
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}
