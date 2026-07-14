import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

/// E2E шифрование фото §10.6.2 — совместимо с backend/worker `enc:v1:`.
class PhotoEncryptionService {
  PhotoEncryptionService._();

  static final instance = PhotoEncryptionService._();

  static const encPrefix = 'enc:v1:';

  final _aes = AesGcm.with256bits().toSync();

  /// 32-byte key, base64url (без padding) — как backend `_decode_task_key`.
  String generateKeyB64() {
    final rnd = Random.secure();
    final bytes = Uint8List.fromList(List.generate(32, (_) => rnd.nextInt(256)));
    return base64Url.encode(bytes).replaceAll('=', '');
  }

  bool isEncryptedBlob(Uint8List data) {
    return utf8.decode(data, allowMalformed: true).startsWith(encPrefix);
  }

  /// Формат: `enc:v1:` + base64url(nonce[12] + ciphertext + tag[16]).
  Uint8List encryptJpeg(Uint8List plaintext, String keyB64) {
    final keyBytes = Uint8List.fromList(_decodeKey(keyB64));
    final secretKey = SecretKeyData(keyBytes);
    final nonce = _aes.newNonce();
    final box = _aes.encryptSync(
      plaintext,
      secretKeyData: secretKey,
      nonce: nonce,
    );
    final ctLen = box.cipherText.length;
    final tagLen = box.mac.bytes.length;
    final packedLen = nonce.length + ctLen + tagLen;
    final packed = Uint8List(packedLen);
    packed.setRange(0, nonce.length, nonce);
    packed.setRange(nonce.length, nonce.length + ctLen, box.cipherText);
    packed.setRange(nonce.length + ctLen, packedLen, box.mac.bytes);
    final blob = base64Url.encode(packed);
    return Uint8List.fromList(utf8.encode('$encPrefix$blob'));
  }

  List<int> _decodeKey(String keyB64) {
    var normalized = keyB64.trim();
    while (normalized.length % 4 != 0) {
      normalized += '=';
    }
    final raw = base64Url.decode(normalized);
    if (raw.length != 32) {
      throw ArgumentError('photo key must be 32 bytes');
    }
    return raw;
  }
}
