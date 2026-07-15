import 'dart:io';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:forui/forui.dart';
import 'package:go_router/go_router.dart';
import 'package:http/http.dart' as http;
import 'package:kwork_mobile/core/api.dart';
import 'package:kwork_mobile/core/session.dart';
import 'package:kwork_mobile/core/theme.dart';
import 'package:kwork_mobile/domain/catalog.dart';
import 'package:kwork_mobile/services/local_model_library.dart';

/// Импорт готового GLB Owner компании §6.10.
class ImportModelScreen extends StatefulWidget {
  const ImportModelScreen({
    super.key,
    required this.api,
    required this.session,
  });

  final ApiClient api;
  final AppSession session;

  @override
  State<ImportModelScreen> createState() => _ImportModelScreenState();
}

class _ImportModelScreenState extends State<ImportModelScreen> {
  static const _maxBytes = 50 * 1024 * 1024;

  final _nameCtrl = TextEditingController();
  ProductCategory _category = ProductCategory.other;
  String? _filePath;
  String? _fileName;
  int? _fileSize;
  double _progress = 0;
  bool _busy = false;
  String? _error;
  int? _importPriceRub;

  @override
  void initState() {
    super.initState();
    _loadPrice();
  }

  Future<void> _loadPrice() async {
    if (!widget.session.isOwner) return;
    try {
      final p = await widget.api.importModelPrice();
      if (mounted) {
        setState(() => _importPriceRub = (p['amount_rub'] as num?)?.toInt());
      }
    } catch (_) {}
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    final res = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['glb'],
      withData: false,
    );
    if (res == null || res.files.isEmpty) return;
    final f = res.files.first;
    final path = f.path;
    if (path == null) return;
    final size = f.size > 0 ? f.size : await File(path).length();
    if (size > _maxBytes) {
      setState(() => _error = 'Файл больше 50 МБ (§6.10)');
      return;
    }
    setState(() {
      _filePath = path;
      _fileName = f.name;
      _fileSize = size;
      _error = null;
    });
  }

  Future<void> _submit() async {
    if (_busy || _filePath == null) return;
    if (!widget.session.isOwner || widget.session.companyId == null) {
      setState(() => _error = 'Импорт доступен только Owner компании (§6.10)');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _progress = 0;
    });
    try {
      final prep = await widget.api.prepareModelImport();
      final uploadUrl = prep['upload_url']?.toString();
      final key = prep['key']?.toString();
      final modelUuid = prep['model_uuid']?.toString();
      final companyId = (prep['company_id'] as num?)?.toInt() ?? widget.session.companyId!;
      final priceRub = (prep['import_price_rub'] as num?)?.toInt() ?? _importPriceRub;
      if (priceRub != null && mounted) setState(() => _importPriceRub = priceRub);
      if (uploadUrl == null || key == null || modelUuid == null) {
        throw StateError('Сервер не вернул параметры загрузки');
      }

      final bytes = await File(_filePath!).readAsBytes();
      setState(() => _progress = 0.15);
      final put = await http.put(
        Uri.parse(uploadUrl),
        headers: {'Content-Type': 'model/gltf-binary'},
        body: bytes,
      );
      if (put.statusCode < 200 || put.statusCode >= 300) {
        throw HttpException('Загрузка GLB: HTTP ${put.statusCode}');
      }
      setState(() => _progress = 0.7);

      final imported = await widget.api.importModel(
        glbKey: key,
        companyId: companyId,
        category: _category.api,
        displayName: _nameCtrl.text.trim(),
        modelUuid: modelUuid,
      );
      setState(() => _progress = 1);

      final status = imported['status']?.toString();
      final orderId = (imported['order_id'] as num?)?.toInt();
      if (!mounted) return;
      if (status == 'import_validating' && orderId != null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Модель на проверке (GLB 2.0 / PBR / Draco)…')),
        );
        context.go('/home/queue/$orderId');
        return;
      }

      final uuid = imported['uuid']?.toString() ?? modelUuid;
      await LocalModelLibrary.instance.downloadGlb(api: widget.api, modelUuid: uuid);

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Модель импортирована')),
      );
      context.go('/home/models/$uuid');
    } catch (e) {
      if (mounted) {
        setState(() => _error = formatApiError(e));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  String _formatSize(int? bytes) {
    if (bytes == null) return '—';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }

  @override
  Widget build(BuildContext context) {
    return FScaffold(
      header: FHeader.nested(
        title: const Text('Импорт модели'),
        prefixes: [FHeaderAction.back(onPress: () => context.pop())],
      ),
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text(
            'Загрузите готовый GLB (до 50 МБ). Доступно только Owner компании §6.10.',
            style: TextStyle(color: AppColors.textSecondary),
          ),
          if (_importPriceRub != null && _importPriceRub! > 0) ...[
            const SizedBox(height: 8),
            Text(
              'Стоимость импорта: $_importPriceRub ₽ (списание с баланса компании)',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ] else if (_importPriceRub == 0) ...[
            const SizedBox(height: 8),
            Text(
              'Импорт бесплатный',
              style: TextStyle(color: AppColors.success, fontWeight: FontWeight.w600),
            ),
          ],
          const SizedBox(height: 16),
          FTextField(
            control: FTextFieldControl.managed(controller: _nameCtrl),
            label: const Text('Название'),
          ),
          const SizedBox(height: 12),
          FSelect<String>(
            label: const Text('Категория'),
            enabled: !_busy,
            control: FSelectControl.managed(
              initial: _category.api,
              onChange: _busy
                  ? null
                  : (v) {
                      if (v == null) return;
                      setState(() {
                        _category = ProductCategory.values.firstWhere((c) => c.api == v);
                      });
                    },
            ),
            items: {
              for (final c in ProductCategory.values) c.label: c.api,
            },
          ),
          const SizedBox(height: 16),
          FButton(
            variant: .outline,
            onPress: _busy ? null : _pickFile,
            prefix: const Icon(FIcons.upload),
            child: Text(_fileName ?? 'Выбрать .glb'),
          ),
          if (_fileSize != null) ...[
            const SizedBox(height: 8),
            Text('Размер: ${_formatSize(_fileSize)}', style: context.theme.typography.sm),
          ],
          if (_busy) ...[
            const SizedBox(height: 16),
            LinearProgressIndicator(value: _progress > 0 ? _progress : null),
          ],
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: AppColors.error)),
          ],
          const SizedBox(height: 20),
          FButton(
            onPress: (_busy || _filePath == null) ? null : _submit,
            child: Text(_busy ? 'Импорт…' : 'Импортировать${priceLabel()}'),
          ),
        ],
      ),
    );
  }

  String priceLabel() {
    if (_importPriceRub == null || _importPriceRub! <= 0) return '';
    return ' · $_importPriceRub ₽';
  }
}
