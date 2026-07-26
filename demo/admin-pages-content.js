/** Общий контент вкладок web-admin §11 — подключается во все demo-варианты */
window.ADMIN_PAGES = {
  dashboard: `
    <div class="pg-head"><div><h1>Главный дашборд</h1><p class="muted">§11.2 · ClickHouse агрегаты · WebSocket live</p></div>
    <select class="demo-select"><option>Сегодня</option><option>7 дней</option><option>30 дней</option></select></div>
    <div class="demo-kpi-grid">
      <div class="demo-kpi"><span class="muted">Заказы в работе</span><strong>142</strong><span class="tag tag-ok">+12%</span></div>
      <div class="demo-kpi"><span class="muted">EWT normal / high</span><strong>4.2 / 1.1 мин</strong></div>
      <div class="demo-kpi"><span class="muted">Воркеры онлайн</span><strong>18 / 22</strong><span class="tag tag-warn">1 overheated</span></div>
      <div class="demo-kpi"><span class="muted">Quality ≥0.7</span><strong>87%</strong><span class="tag tag-ok">цель 80%</span></div>
    </div>
    <div class="demo-grid-2">
      <div class="demo-card"><h3>Поступление задач · §11.2.1</h3><div class="chart-wrap"><canvas id="ch-tasks"></canvas></div></div>
      <div>
        <div class="demo-card mb"><h3>Выручка · §11.2.2</h3><p class="big">284 500 ₽</p><p class="muted">Возвраты NSFW: 12 400 ₽ · ЮKassa: 8 535 ₽</p></div>
        <div class="demo-card"><h3>Очередь</h3><p>queue:normal <strong>89</strong> · queue:high <strong class="danger">12</strong></p>
        <p class="muted mt">Удержано NSFW: 3 200 ₽</p></div>
      </div>
    </div>
    <div class="demo-grid-2 mt">
      <div class="demo-card"><h3>B2B топ · §11.2.3</h3>
        <table class="demo-table"><thead><tr><th>Компания</th><th>Заказы</th><th>₽</th></tr></thead>
        <tbody><tr><td>ООО «МебельПро»</td><td>312</td><td>1 240 000</td></tr>
        <tr><td>ИП Сидоров</td><td>89</td><td>340 000</td></tr></tbody></table>
      </div>
      <div class="demo-card"><h3>Сегментация · §11.2.5</h3>
        <p>DeepLab <strong>94.2%</strong> · SAM fallback <strong>5.8%</strong></p>
        <div class="demo-bar"><span style="width:94%"></span></div>
        <p class="muted">NSFW: ложные 12 / подтверждённые 3 за 7д</p>
      </div>
    </div>`,

  workers: `
    <div class="pg-head"><h1>Управление воркерами · §11.3</h1>
    <div><button class="demo-btn primary">☁️ Облачный инстанс</button> <button class="demo-btn">Deploy JSON</button></div></div>
    <div class="demo-card mb"><h3>Загрузка GPU · §11.2.6</h3><div class="chart-wrap"><canvas id="ch-gpu"></canvas></div></div>
    <table class="demo-table">
      <thead><tr><th>ID</th><th>GPU</th><th>TRELLIS</th><th>Статус</th><th>GPU%</th><th>VRAM</th><th>T°</th><th>Вес</th><th>Grace</th><th></th></tr></thead>
      <tbody>
        <tr><td><code>client-gpu-01</code></td><td>RTX 5060 Ti</td><td>2</td><td><span class="tag tag-ok">busy</span></td><td>92%</td><td>11.2/16</td><td>72°C</td><td>0.8</td><td>25s</td><td><button class="demo-btn sm">Логи</button></td></tr>
        <tr><td><code>cloud-rtx4090-03</code></td><td>RTX 4090</td><td>2</td><td><span class="tag">idle</span></td><td>8%</td><td>2.1/24</td><td>45°C</td><td>1.0</td><td>25s</td><td><button class="demo-btn sm">Логи</button></td></tr>
        <tr><td><code>cloud-rtx4090-07</code></td><td>RTX 4090</td><td>2</td><td><span class="tag tag-warn">overheated</span></td><td>—</td><td>—</td><td>91°C</td><td>0</td><td>—</td><td><button class="demo-btn sm danger">Maintenance</button></td></tr>
      </tbody>
    </table>
    <div class="demo-card mt"><h3>Облачные инстансы</h3>
    <table class="demo-table"><thead><tr><th>Провайдер</th><th>GPU</th><th>₽/ч</th><th>Статус</th><th></th></tr></thead>
    <tbody><tr><td>Intelion</td><td>RTX 4090</td><td>89</td><td><span class="tag tag-ok">running</span></td><td><button class="demo-btn sm danger">Стоп</button></td></tr></tbody></table></div>`,

  storage: `
    <h1>Кластер хранения · §11.16</h1>
    <div class="demo-kpi-grid">
      <div class="demo-card border-ok"><h3>🟢 Primary · Дом ПК-1</h3>
        <p>Tailscale <code>100.64.0.12</code> · ping 12ms</p>
        <p>PostgreSQL · Redis · MinIO · ClickHouse — <strong>running</strong></p>
        <p>CPU 34% · RAM 28/64 GB · NVMe 62% · Temp 48°C</p>
        <p class="muted">MinIO replication: синхронно · SMART OK</p>
        <button class="demo-btn sm">Ping</button> <button class="demo-btn sm">Docker logs</button>
      </div>
      <div class="demo-card border-warn"><h3>🟡 Replica · Дом ПК-2</h3>
        <p>Tailscale <code>100.64.0.13</code> · ping 18ms</p>
        <p>ClickHouse replication lag: <strong>45 сек</strong></p>
        <p>SMART: предупреждение <code>/dev/nvme1</code></p>
        <button class="demo-btn sm primary">Диагностика</button>
      </div>
    </div>
    <div class="demo-card mt"><h3>История доступности узлов · §11.16.3</h3><div class="chart-wrap chart-wrap--sm"><canvas id="ch-uptime"></canvas></div></div>`,

  users: `
    <div class="pg-head"><h1>Пользователи · §11.6</h1>
    <input class="demo-input" placeholder="Поиск email…" /></div>
    <table class="demo-table">
      <thead><tr><th>Email</th><th>Тип</th><th>Статус</th><th>Заказы</th><th>Сумма</th><th>Последняя активность</th><th></th></tr></thead>
      <tbody>
        <tr><td>seller@shop.ru</td><td>юрлицо</td><td><span class="tag tag-ok">активен</span></td><td>47</td><td>128 400 ₽</td><td>26.07 00:45</td><td><button class="demo-btn sm">Карточка</button></td></tr>
        <tr><td>user@mail.ru</td><td>физлицо</td><td><span class="tag tag-warn">blocked_pending_review</span></td><td>3</td><td>8 700 ₽</td><td>25.07 22:10</td><td><button class="demo-btn sm">NSFW</button></td></tr>
        <tr><td>photo@corp.ru</td><td>Photographer</td><td><span class="tag tag-ok">активен</span></td><td>156</td><td>—</td><td>26.07 01:12</td><td><button class="demo-btn sm danger">Удалить §11.12</button></td></tr>
      </tbody>
    </table>`,

  b2b: `
    <div class="pg-head"><h1>B2B-клиенты · §11.6</h1><button class="demo-btn primary">Импорт CSV §11.14</button></div>
    <table class="demo-table">
      <thead><tr><th>Компания</th><th>ИНН</th><th>Сотрудники</th><th>Баланс</th><th>API ключи</th><th>Статус</th><th></th></tr></thead>
      <tbody>
        <tr><td>ООО «МебельПро»</td><td>7701234567</td><td>12</td><td>84 200 ₽</td><td>3 активных</td><td><span class="tag tag-ok">активна</span></td><td><button class="demo-btn sm">Карточка</button></td></tr>
        <tr><td>ИП Сидоров</td><td>500123456789</td><td>2</td><td>12 000 ₽</td><td>1 активный</td><td><span class="tag tag-ok">активна</span></td><td><button class="demo-btn sm">Лимиты</button></td></tr>
      </tbody>
    </table>
    <div class="demo-card mt"><h3>Карточка компании (пример)</h3>
    <div class="demo-grid-2">
      <div><p><strong>monthly_spending_limit:</strong> 500 000 ₽</p><p><strong>max_concurrent_orders:</strong> 5 / Photographer</p></div>
      <div><p><strong>Индивидуальные цены:</strong> малый −15%, крупный −10%</p><p><strong>Последний API вызов:</strong> 26.07 00:30</p></div>
    </div></div>`,

  promo: `
    <div class="pg-head"><h1>Промокоды · §11.7</h1>
    <div><button class="demo-btn">Импорт CSV</button> <button class="demo-btn primary">+ Создать</button></div></div>
    <table class="demo-table">
      <thead><tr><th>Код</th><th>Название</th><th>Скидка</th><th>Использовано</th><th>Тариф</th><th>Статус</th><th></th></tr></thead>
      <tbody>
        <tr><td><code>KAJ5X7M2N9PQ</code> <button class="demo-btn sm" data-copy="KAJ5X7M2N9PQ">📋</button></td><td>Летняя акция</td><td>10%</td><td>24 / 100</td><td>любой</td><td><span class="tag tag-ok">Активен</span></td><td><button class="demo-btn sm danger">Отключить</button></td></tr>
        <tr><td><code>SCC7FREE100X</code> <button class="demo-btn sm" data-copy="SCC7FREE100X">📋</button></td><td>мимими</td><td>100%</td><td>0 / 10</td><td>малый</td><td><span class="tag tag-ok">Активен</span></td><td><button class="demo-btn sm danger">Отключить</button></td></tr>
      </tbody>
    </table>`,

  campaigns: `
    <div class="pg-head"><h1>Маркетинговые кампании · §11.7</h1><button class="demo-btn primary">+ Новая кампания</button></div>
    <table class="demo-table mb">
      <thead><tr><th>Название</th><th>Шаблон</th><th>Статус</th><th>Охват</th><th>Конверсия</th><th>ROI</th><th></th></tr></thead>
      <tbody>
        <tr><td>Лето 2026</td><td>скидка по промокоду</td><td><span class="tag tag-ok">запущена</span></td><td>4 200</td><td>3.2%</td><td>1.8x</td><td><button class="demo-btn sm">Статистика</button></td></tr>
        <tr><td>Реферал Q3</td><td>реферальная акция</td><td><span class="tag">черновик</span></td><td>—</td><td>—</td><td>—</td><td><button class="demo-btn sm primary">Запустить</button></td></tr>
      </tbody>
    </table>
    <div class="demo-card"><h3>Конструктор кампании</h3>
    <div class="demo-form">
      <label>Шаблон<select class="demo-select full"><option>скидка по промокоду</option><option>каждая N-я бесплатно</option><option>таймерная скидка</option></select></label>
      <label>Сегмент<select class="demo-select full"><option>активность 30д</option><option>регион Москва</option><option>B2B компании</option></select></label>
      <label>Канал<select class="demo-select full"><option>push</option><option>email (с согласием)</option></select></label>
      <label>Текст<textarea class="demo-input" rows="3">Привет, {name}! Промокод {code} — скидка 10%</textarea></label>
    </div></div>`,

  support: `
    <h1>Поддержка · §11.9</h1>
    <div class="demo-grid-2">
      <div class="demo-card nopad">
        <a class="demo-list-item active">#1042 · GLB не скачивается <span class="tag tag-danger">новое</span></a>
        <a class="demo-list-item">#1041 · Возврат по NSFW <span class="tag">в работе</span></a>
        <a class="demo-list-item">#1040 · ЮKassa оплата</a>
      </div>
      <div class="demo-card">
        <p class="muted">seller@shop.ru · 47 заказов · 128 400 ₽ · NSFW: 0</p>
        <div class="demo-bubble">Здравствуйте, после генерации кнопка «Скачать» неактивна…</div>
        <button class="demo-btn sm">🤖 Ollama черновик</button>
        <textarea class="demo-input mt" rows="3" placeholder="Ответ…"></textarea>
        <button class="demo-btn primary mt">Отправить</button>
        <button class="demo-btn sm mt">Эскалировать владельцу</button>
      </div>
    </div>
    <div class="demo-card mt"><h3>FAQ · редактирование</h3>
    <table class="demo-table"><thead><tr><th>Вопрос</th><th>Категория</th><th>Версия</th><th></th></tr></thead>
    <tbody><tr><td>Как загрузить на WB?</td><td>Публикация</td><td>v12</td><td><button class="demo-btn sm">Редактировать</button></td></tr></tbody></table></div>`,

  moderation: `
    <h1>NSFW-модерация · §11.10</h1>
    <table class="demo-table mb">
      <thead><tr><th>Дата</th><th>Пользователь</th><th>Компания</th><th>Refunded</th><th>Статус</th><th></th></tr></thead>
      <tbody>
        <tr><td>26.07 00:12</td><td>user@mail.ru</td><td>—</td><td>да</td><td>ожидает 24ч</td><td><button class="demo-btn sm primary">Проверить</button></td></tr>
      </tbody>
    </table>
    <div class="demo-card"><h3>Проверка заказа #8821</h3>
    <div class="demo-thumbs">${Array(12).fill(0).map((_, i) => `<div class="demo-thumb">кадр ${i + 1}</div>`).join('')}</div>
    <div class="mt"><button class="demo-btn primary">✓ Легально (разблокировать)</button> <button class="demo-btn danger">✗ Нарушение (permanent)</button></div></div>
    <div class="demo-card mt"><h3>Чёрный список слов</h3>
    <textarea class="demo-input" rows="4">counterfeit-brand\nоружие\nнаркотики</textarea>
    <button class="demo-btn sm primary mt">Сохранить</button></div>`,

  tax: `
    <h1>Налоговый модуль · §11.13</h1>
    <div class="demo-card">
      <p><label><input type="radio" name="tax" checked /> Самозанятый</label>
      <label class="ml"><input type="radio" name="tax" /> ИП</label>
      <label class="ml"><input type="radio" name="tax" /> ООО</label></p>
      <div class="demo-form mt">
        <label>ИНН<input class="demo-input" value="500123456789" /></label>
        <label>ФИО<input class="demo-input" value="Иванов И.И." /></label>
        <label>Телефон<input class="demo-input" value="+7 900 000-00-00" /></label>
      </div>
      <button class="demo-btn primary mt">Сохранить реквизиты</button>
    </div>
    <div class="demo-card mt"><h3>Выгрузка доходов · §8.6</h3>
    <p>Период: <input type="month" class="demo-input" value="2026-07" /></p>
    <button class="demo-btn">CSV</button> <button class="demo-btn">Отчёт для налоговой</button></div>`,

  legal: `
    <h1>Юридические документы · §11.11</h1>
    <div class="demo-grid-2">
      <div class="demo-card"><h3>Редактор</h3>
        <select class="demo-select full"><option>Пользовательское соглашение</option><option>Политика ПД</option><option>Оферта</option></select>
        <textarea class="demo-input mt" rows="10"># Пользовательское соглашение v13\n\n1. Предмет договора…</textarea>
        <button class="demo-btn primary mt">Опубликовать новую версию</button>
      </div>
      <div class="demo-card"><h3>История версий</h3>
        <table class="demo-table"><thead><tr><th>Версия</th><th>Дата</th><th>Автор</th></tr></thead>
        <tbody><tr><td>v13</td><td>20.07.2026</td><td>admin</td></tr><tr><td>v12</td><td>01.06.2026</td><td>admin</td></tr></tbody></table>
        <h3 class="mt">Согласия пользователей</h3>
        <p class="muted">Фильтр по user_id, версии · IP · user-agent</p>
      </div>
    </div>`,

  settings: `
    <h1>Настройки · §11.4 / §11.1</h1>
    <div class="demo-tabs">
      <button class="demo-tab active" data-tab="tariffs">Тарифы</button>
      <button class="demo-tab" data-tab="session">Сессия JWT</button>
      <button class="demo-tab" data-tab="alerts">Алерты</button>
    </div>
    <div class="demo-card" id="tab-tariffs">
      <h3>Цены и тарифы · §11.4</h3>
      <div class="demo-form"><label>Малый тариф, ₽<input class="demo-input" type="number" value="990" /></label>
      <label>Крупный тариф, ₽<input class="demo-input" type="number" value="2490" /></label>
      <label>Апсейл 1:1, ₽<input class="demo-input" type="number" value="500" /></label></div>
      <button class="demo-btn primary">Применить к новым заказам</button>
    </div>
    <div class="demo-card mt hidden" id="tab-session">
      <h3>Staff сессия</h3>
      <label>JWT access, мин<input class="demo-input" value="480" /></label>
      <label>Refresh, дней<input class="demo-input" value="30" /></label>
      <label>Idle timeout, мин<input class="demo-input" value="43200" /></label>
    </div>
    <div class="demo-card mt hidden" id="tab-alerts">
      <h3>Алерты · §11.5</h3>
      <p>GPU temp &gt; 85°C → Telegram</p>
      <p>Очередь &gt; 50 → email + Telegram</p>
      <p>Сегментация устройства &gt; 15% fail → срочно</p>
    </div>
    <div class="demo-card mt"><h3>Grace period воркеров · §11.3</h3>
    <label>Глобально, сек (25–30)<input class="demo-input" type="range" min="25" max="30" value="25" /></label></div>`,

  logs: `
    <div class="pg-head"><h1>Логи · §11.5</h1><button class="demo-btn">Выгрузить CSV §11.14</button></div>
    <div class="demo-filters">
      <select class="demo-select"><option>user_events</option><option>worker_agent</option><option>segmentation</option><option>ERROR</option></select>
      <input class="demo-input" placeholder="user_id / company_id" />
      <input class="demo-input" type="date" value="2026-07-25" />
    </div>
    <table class="demo-table">
      <thead><tr><th>Время</th><th>Источник</th><th>Уровень</th><th>Сообщение</th></tr></thead>
      <tbody>
        <tr><td>26.07 01:02:11</td><td>worker_agent</td><td>INFO</td><td>client-gpu-01 trellis_generate done 357s</td></tr>
        <tr><td>26.07 01:01:44</td><td>segmentation</td><td>INFO</td><td>DeepLab mean_confidence=0.91 area_ratio=0.74</td></tr>
        <tr><td>26.07 00:58:02</td><td>orchestrator</td><td>ERROR</td><td>webhook delivery failed order_id=8820 attempt 3/5</td></tr>
        <tr><td>26.07 00:45:18</td><td>user_events</td><td>INFO</td><td>order.created user_id=104 tier=small</td></tr>
      </tbody>
    </table>`
};

window.ADMIN_NAV = [
  { id: 'dashboard', label: 'Дашборд', icon: '📊' },
  { id: 'workers', label: 'Воркеры', icon: '🖥️' },
  { id: 'storage', label: 'Кластер', icon: '💾' },
  { id: 'users', label: 'Пользователи', icon: '👤' },
  { id: 'b2b', label: 'B2B', icon: '🏢' },
  { id: 'promo', label: 'Промокоды', icon: '🏷️' },
  { id: 'campaigns', label: 'Кампании', icon: '📣' },
  { id: 'support', label: 'Поддержка', icon: '💬' },
  { id: 'moderation', label: 'NSFW', icon: '🛡️' },
  { id: 'tax', label: 'Налоги', icon: '🧾' },
  { id: 'legal', label: 'Юр. документы', icon: '📄' },
  { id: 'settings', label: 'Настройки', icon: '⚙️' },
  { id: 'logs', label: 'Логи', icon: '📋' }
];

window._chartInstances = {};

window.initAdminCharts = function (pageId, colors) {
  const c = colors || { primary: '#0057b8', secondary: '#198754' };
  Object.values(window._chartInstances).forEach((ch) => ch.destroy());
  window._chartInstances = {};
  if (typeof Chart === 'undefined') return;
  const mk = (id, cfg) => {
    const el = document.getElementById(id);
    if (!el) return;
    window._chartInstances[id] = new Chart(el, cfg);
  };
  if (pageId === 'dashboard') {
    mk('ch-tasks', { type: 'line', data: { labels: ['00','04','08','12','16','20','24'], datasets: [{ data: [12,8,45,62,58,71,38], borderColor: c.primary, tension: 0.35, fill: true, backgroundColor: c.primary + '22' }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } } } });
  }
  if (pageId === 'workers') {
    mk('ch-gpu', { type: 'line', data: { labels: Array(8).fill(''), datasets: [{ label: 'client-gpu-01', data: [20,45,80,92,88,92,90,92], borderColor: c.primary, tension: 0.35 }, { label: 'cloud-03', data: [5,8,12,10,8,8,7,8], borderColor: c.secondary, tension: 0.35 }] }, options: { responsive: true, maintainAspectRatio: false, scales: { y: { min: 0, max: 100 } } } });
  }
  if (pageId === 'storage') {
    mk('ch-uptime', { type: 'bar', data: { labels: ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'], datasets: [{ data: [100,100,99.9,100,100,100,99.8], backgroundColor: c.primary + 'aa' }] }, options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { min: 99, max: 100 } } } });
  }
};

window.bindAdminPage = function (hostId, navSelector, colors) {
  const host = document.getElementById(hostId);
  const show = (id) => {
    host.innerHTML = window.ADMIN_PAGES[id] || '<p>Страница не найдена</p>';
    document.querySelectorAll(navSelector).forEach((n) => n.classList.toggle('active', n.dataset.page === id));
    requestAnimationFrame(() => window.initAdminCharts(id, colors));
    host.querySelectorAll('[data-copy]').forEach((btn) => {
      btn.onclick = () => navigator.clipboard.writeText(btn.dataset.copy);
    });
    host.querySelectorAll('.demo-tab').forEach((tab) => {
      tab.onclick = () => {
        host.querySelectorAll('.demo-tab').forEach((t) => t.classList.remove('active'));
        tab.classList.add('active');
        ['tariffs','session','alerts'].forEach((k) => {
          const el = host.querySelector('#tab-' + k);
          if (el) el.classList.toggle('hidden', tab.dataset.tab !== k);
        });
      };
    });
  };
  document.querySelectorAll(navSelector).forEach((a) => {
    a.addEventListener('click', (e) => { e.preventDefault(); show(a.dataset.page); });
  });
  show('dashboard');
};
