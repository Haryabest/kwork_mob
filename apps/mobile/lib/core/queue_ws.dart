import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// WebSocket `/ws/queue/{user_id}` — §3.4.1.
class QueueWsClient extends ChangeNotifier {
  QueueWsClient({required this.wsBaseUrl});

  final String wsBaseUrl;

  WebSocketChannel? _channel;
  StreamSubscription? _sub;
  Timer? _ping;
  Map<String, dynamic>? lastEvent;
  bool connected = false;
  Object? lastError;

  Future<void> connect({required int userId, required String token}) async {
    await disconnect();
    final uri = Uri.parse('$wsBaseUrl/ws/queue/$userId?token=$token');
    try {
      _channel = WebSocketChannel.connect(uri);
      connected = true;
      lastError = null;
      notifyListeners();
      _sub = _channel!.stream.listen(
        (raw) {
          try {
            final data = jsonDecode(raw as String) as Map<String, dynamic>;
            lastEvent = data;
            notifyListeners();
          } catch (_) {}
        },
        onError: (e) {
          lastError = e;
          connected = false;
          notifyListeners();
        },
        onDone: () {
          connected = false;
          notifyListeners();
        },
      );
      _ping = Timer.periodic(const Duration(seconds: 20), (_) {
        _channel?.sink.add(jsonEncode({'type': 'ping'}));
      });
    } catch (e) {
      lastError = e;
      connected = false;
      notifyListeners();
    }
  }

  Future<void> disconnect() async {
    _ping?.cancel();
    _ping = null;
    await _sub?.cancel();
    _sub = null;
    await _channel?.sink.close();
    _channel = null;
    connected = false;
  }

  @override
  void dispose() {
    disconnect();
    super.dispose();
  }
}
