import type { Locale, Messages } from './types';

const ru: Messages = {
  nav: {
    dashboard: 'Главная',
    models: 'Мои модели',
    orders: 'Заказы',
    balance: 'Баланс',
    team: 'Команда',
    support: 'Поддержка',
    settings: 'Настройки',
  },
  shell: {
    sellerCabinet: 'Кабинет селлера',
    notifications: 'Уведомления',
    personalAccount: 'Личный кабинет',
    settings: 'Настройки',
    logout: 'Выйти',
  },
  settings: {
    title: 'Профиль и настройки',
    description: 'Личные данные, 2FA и уведомления',
    profile: 'Профиль',
    security: 'Безопасность',
    notifications: 'Уведомления',
    danger: 'Опасная зона',
    language: 'Язык интерфейса',
    languageHint: 'Сохраняется в профиле и синхронизируется между устройствами',
    saveProfile: 'Сохранить профиль',
    profileSaved: 'Профиль сохранён',
    email: 'Email',
    fullName: 'ФИО',
    phone: 'Телефон',
  },
  common: {
    langRu: 'Русский',
    langEn: 'English',
    langKk: 'Қазақша',
    langZh: '中文',
  },
};

const en: Messages = {
  nav: {
    dashboard: 'Dashboard',
    models: 'My models',
    orders: 'Orders',
    balance: 'Balance',
    team: 'Team',
    support: 'Support',
    settings: 'Settings',
  },
  shell: {
    sellerCabinet: 'Seller portal',
    notifications: 'Notifications',
    personalAccount: 'Account',
    settings: 'Settings',
    logout: 'Log out',
  },
  settings: {
    title: 'Profile & settings',
    description: 'Personal data, 2FA and notifications',
    profile: 'Profile',
    security: 'Security',
    notifications: 'Notifications',
    danger: 'Danger zone',
    language: 'Interface language',
    languageHint: 'Saved to your profile and synced across devices',
    saveProfile: 'Save profile',
    profileSaved: 'Profile saved',
    email: 'Email',
    fullName: 'Full name',
    phone: 'Phone',
  },
  common: {
    langRu: 'Русский',
    langEn: 'English',
    langKk: 'Қазақша',
    langZh: '中文',
  },
};

const kk: Messages = {
  nav: {
    dashboard: 'Басты',
    models: 'Модельдерім',
    orders: 'Тапсырыстар',
    balance: 'Баланс',
    team: 'Команда',
    support: 'Қолдау',
    settings: 'Баптаулар',
  },
  shell: {
    sellerCabinet: 'Сатушы кабинеті',
    notifications: 'Хабарламалар',
    personalAccount: 'Жеке кабинет',
    settings: 'Баптаулар',
    logout: 'Шығу',
  },
  settings: {
    title: 'Профиль және баптаулар',
    description: 'Жеке деректер, 2FA және хабарламалар',
    profile: 'Профиль',
    security: 'Қауіпсіздік',
    notifications: 'Хабарламалар',
    danger: 'Қауіпті аймақ',
    language: 'Интерфейс тілі',
    languageHint: 'Профильде сақталады және құрылғылар арасында синхрондалады',
    saveProfile: 'Профильді сақтау',
    profileSaved: 'Профиль сақталды',
    email: 'Email',
    fullName: 'Аты-жөні',
    phone: 'Телефон',
  },
  common: {
    langRu: 'Русский',
    langEn: 'English',
    langKk: 'Қазақша',
    langZh: '中文',
  },
};

const zhCN: Messages = {
  nav: {
    dashboard: '首页',
    models: '我的模型',
    orders: '订单',
    balance: '余额',
    team: '团队',
    support: '支持',
    settings: '设置',
  },
  shell: {
    sellerCabinet: '卖家中心',
    notifications: '通知',
    personalAccount: '个人账户',
    settings: '设置',
    logout: '退出',
  },
  settings: {
    title: '个人资料与设置',
    description: '个人资料、双重验证与通知',
    profile: '个人资料',
    security: '安全',
    notifications: '通知',
    danger: '危险操作',
    language: '界面语言',
    languageHint: '保存到个人资料并在设备间同步',
    saveProfile: '保存资料',
    profileSaved: '资料已保存',
    email: '邮箱',
    fullName: '姓名',
    phone: '电话',
  },
  common: {
    langRu: 'Русский',
    langEn: 'English',
    langKk: 'Қазақша',
    langZh: '中文',
  },
};

export const MESSAGES: Record<Locale, Messages> = {
  ru,
  en,
  kk,
  'zh-CN': zhCN,
};

export function getMessages(locale: Locale): Messages {
  return MESSAGES[locale] ?? MESSAGES.ru;
}
