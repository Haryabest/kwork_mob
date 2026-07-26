export const SUPPORT_STATUS_LABEL: Record<string, string> = {
  new: 'Новое',
  in_progress: 'В работе',
  answered: 'Отвечено',
  waiting_user: 'Ожидает вас',
  closed: 'Закрыто',
  resolved: 'Решено',
  escalated: 'Эскалация',
};

export const SUPPORT_STATUS_COLOR: Record<string, string> = {
  new: 'blue',
  in_progress: 'yellow',
  answered: 'teal',
  waiting_user: 'orange',
  closed: 'gray',
  resolved: 'gray',
  escalated: 'red',
};

export function supportStatusLabel(status: string) {
  return SUPPORT_STATUS_LABEL[status] ?? status;
}
