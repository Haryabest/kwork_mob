import 'package:flutter/material.dart';

/// AR-камера через нативную Texture (ARCore/ARKit) §3.1.1.
class NativeArPreview extends StatelessWidget {
  const NativeArPreview({super.key, required this.textureId});

  final int textureId;

  @override
  Widget build(BuildContext context) {
    return Texture(textureId: textureId);
  }
}
