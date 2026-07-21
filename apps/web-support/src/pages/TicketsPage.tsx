/** DEPRECATED — используйте apps/web-admin (/support/*) */
export default function TicketsPage() {
  const adminUrl = import.meta.env.VITE_ADMIN_URL || 'http://localhost:3001/support/tickets';
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', maxWidth: 560, margin: '4rem auto', padding: '0 1.5rem' }}>
      <h1>Панель поддержки перенесена</h1>
      <p>
        Пакет <code>web-support</code> deprecated. Используйте единую Staff Panel в{' '}
        <code>web-admin</code> (роль <code>support_agent</code>).
      </p>
      <p>
        <a href={adminUrl}>Открыть тикеты в admin →</a>
      </p>
    </div>
  );
}

