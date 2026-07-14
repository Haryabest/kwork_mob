import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';

import 'package:cryptography/cryptography.dart';

/// E2E шифрование фото §10.6.2 — совместимо с backend/worker `enc:v1:`.
class PhotoEncryptionService {
  PhotoEncryptionService._();
  static final instance = PhotoEncryptionService._();

  static const encPrefix = 'enc:v1:';
  final _algorithm = AesGcm.with256bits();

  /// 32-byte key, base64url (без padding).
  Future<String> generateKeyB64() async {
    final rnd = Random.secure();
    final bytes = Uint8List.fromList(List.generate(32, (_) => rnd.nextInt(256)));
    return base64Url.encode(bytes).replaceAll('=', '');
  }

  Future<Uint8List> encryptJpeg(Uint8List plaintext, String keyB64) async {
    final keyBytes = _decodeKey(keyB64);
    final secretKey = SecretKey(keyBytes);
    final nonce = _algorithm.newNonce();
    final box = await _algorithm.encrypt(
      plaintext,
      secretKey: secretKey,
      nonce: nonce,
    );
    final packed = Uint8List.fromList([
      ...nonce,
      ...box.cipherText,
      ...box.mac.bytes,
    ]);
    return Uint8List.fromList(utf8.encode('$encPrefix${base64Url.encode(packed)}'));
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
