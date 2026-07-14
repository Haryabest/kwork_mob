// Firebase options — заполняются из dart-define или из google-services (§3.4.3).
// Без реальных ключей PushService тихо отключается.
//
// flutter run \
//   --dart-define=FIREBASE_API_KEY=... \
//   --dart-define=FIREBASE_APP_ID=... \
//   --dart-define=FIREBASE_MESSAGING_SENDER_ID=... \
//   --dart-define=FIREBASE_PROJECT_ID=...

import 'package:firebase_core/firebase_core.dart' show FirebaseOptions;
import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

class DefaultFirebaseOptions {
  static FirebaseOptions? get currentPlatform {
    if (kIsWeb) return null;
    final apiKey = const String.fromEnvironment('FIREBASE_API_KEY');
    final appId = const String.fromEnvironment('FIREBASE_APP_ID');
    final senderId = const String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID');
    final projectId = const String.fromEnvironment('FIREBASE_PROJECT_ID');
    if (apiKey.isEmpty || appId.isEmpty || senderId.isEmpty || projectId.isEmpty) {
      return null;
    }
    switch (defaultTargetPlatform) {
      case TargetPlatform.android:
        return FirebaseOptions(
          apiKey: apiKey,
          appId: appId,
          messagingSenderId: senderId,
          projectId: projectId,
          storageBucket: const String.fromEnvironment(
            'FIREBASE_STORAGE_BUCKET',
            defaultValue: '',
          ),
        );
      case TargetPlatform.iOS:
        return FirebaseOptions(
          apiKey: apiKey,
          appId: appId,
          messagingSenderId: senderId,
          projectId: projectId,
          iosBundleId: const String.fromEnvironment(
            'FIREBASE_IOS_BUNDLE_ID',
            defaultValue: 'com.kworkmob.kworkMobile',
          ),
          storageBucket: const String.fromEnvironment(
            'FIREBASE_STORAGE_BUCKET',
            defaultValue: '',
          ),
        );
      default:
        return null;
    }
  }
}
