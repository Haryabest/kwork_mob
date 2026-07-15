import 'package:flutter_test/flutter_test.dart';
import 'package:kwork_mobile/services/upload_progress_service.dart';

void main() {
  test('uploadedIndices parses saved list', () {
    final svc = UploadProgressService.instance;
    expect(svc.uploadedIndices(null), isEmpty);
    expect(
      svc.uploadedIndices({'uploaded_indices': [0, 1, 5]}),
      [0, 1, 5],
    );
  });
}
