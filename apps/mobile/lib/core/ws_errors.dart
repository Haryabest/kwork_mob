/// Человекочитаемые ошибки WebSocket очереди (§3.4.1).
String formatWsError(Object error) {
  final s = error.toString().toLowerCase();
  if (s.contains('401') || s.contains('403') || s.contains('unauthorized')) {
    return 'Сессия истекла. Войдите снова.';
  }
  if (s.contains('connection refused') || s.contains('failed host lookup')) {
    return 'Сервер недоступен. Проверьте API_URL и сеть.';
  }
  if (s.contains('websocket') || s.contains('socket')) {
    return 'Не удалось подключиться к очереди. Повторите позже.';
  }
  return 'Ошибка соединения с очередью';
}
