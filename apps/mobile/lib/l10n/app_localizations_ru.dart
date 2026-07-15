// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Russian (`ru`).
class AppLocalizationsRu extends AppLocalizations {
  AppLocalizationsRu([String locale = 'ru']) : super(locale);

  @override
  String get appName => 'KWork Mob';

  @override
  String get authTitle => 'Вход';

  @override
  String get email => 'Email';

  @override
  String get password => 'Пароль';

  @override
  String get login => 'Войти';

  @override
  String get register => 'Регистрация';

  @override
  String get forgotPassword => 'Забыли пароль?';

  @override
  String get home => 'Главная';

  @override
  String get models => 'Модели';

  @override
  String get orders => 'Заказы';

  @override
  String get support => 'Поддержка';

  @override
  String get profile => 'Профиль';

  @override
  String get shoot => 'Снять товар';

  @override
  String get queue => 'Очередь';

  @override
  String get faq => 'FAQ';

  @override
  String get personalMode => 'Личный';

  @override
  String get corporateMode => 'Компания';

  @override
  String get onboarding1 => 'Снимите товар с 12 ракурсов';

  @override
  String get onboarding2 => 'Оплатите тариф и дождитесь генерации';

  @override
  String get onboarding3 => 'Скачайте .glb / .usdz для маркетплейса';

  @override
  String get onboarding4 => 'Опубликуйте модель на WB или Ozon';

  @override
  String get onboardingSub1 =>
      '12 ракурсов Guided Dome → 3D-модель для маркетплейса';

  @override
  String get onboardingSub2 =>
      'ARKit / ARCore или гироскоп подскажут угол ±15°. Для масштаба 1:1 — калибровка по карте или A4 в профиле.';

  @override
  String get onboardingSub3 =>
      'Скачайте GLB/USDZ и опубликуйте на Wildberries или Ozon';

  @override
  String get onboardingSub4 =>
      'При нагреве >40°C съёмка перейдёт в энергосбережение (FPS 15)';

  @override
  String get skip => 'Пропустить';

  @override
  String get alreadyHaveAccount => 'Уже есть аккаунт? Войти';

  @override
  String get continueBtn => 'Продолжить';

  @override
  String get errorNetwork => 'Нет интернета';

  @override
  String get comingSoon => 'Экран в разработке';

  @override
  String get save => 'Сохранить';

  @override
  String get cancel => 'Отмена';

  @override
  String get confirm => 'Подтвердить';

  @override
  String get done => 'Готово';

  @override
  String get account => 'Аккаунт';

  @override
  String get langRu => 'Русский';

  @override
  String get langEn => 'English';

  @override
  String get langKk => 'Қазақша';

  @override
  String get langZh => '中文';

  @override
  String get companyTopupTitle => 'Баланс компании';

  @override
  String get companyTopupSubtitle => 'Пополнение счёта · §19.14.2';

  @override
  String get companyPoliciesTitle => 'Политики компании';

  @override
  String get companyPoliciesSubtitle => 'Доступ и уведомления · §19.14.2';

  @override
  String companyBalanceLabel(String balance) {
    return 'Баланс компании: $balance ₽';
  }

  @override
  String get policiesMaxConcurrent =>
      'Лимит одновременных заказов (по умолчанию)';

  @override
  String get policiesNoMonthlyLimit => 'Без месячного лимита расходов';

  @override
  String get policiesMonthlyLimit => 'Месячный лимит расходов (₽)';

  @override
  String get policiesAllowedCategories => 'Разрешённые категории';

  @override
  String get policiesAllowDownload => 'Photographer может скачивать модели';

  @override
  String get policiesAllowLinks =>
      'Photographer может добавлять ссылки публикации';

  @override
  String get policiesRequire2fa => 'Требовать 2FA для всех сотрудников';

  @override
  String get policiesAutoBlock => 'Авто-блокировка при неактивности (дней)';

  @override
  String get policiesLowBalanceThreshold => 'Порог низкого баланса (₽)';

  @override
  String get policiesNotifySection => 'Уведомления Owner (§3.19)';

  @override
  String get policiesNotifyHint => 'Кому слать push/email по событиям компании';

  @override
  String get policiesSaved => 'Политики сохранены';

  @override
  String get policiesInvalidConcurrent => 'Укажите лимит заказов от 1 до 20';

  @override
  String get policiesInvalidAutoBlock =>
      'Укажите корректный срок авто-блокировки';

  @override
  String get policiesInvalidThreshold => 'Укажите корректный порог баланса';

  @override
  String get policiesInvalidMonthly => 'Укажите корректный месячный лимит';

  @override
  String get notifyGenerationDone => 'Генерация завершена';

  @override
  String get notifyPhotographerUploaded => 'Фотограф загрузил фото';

  @override
  String get notifySourceExpire => 'Истекает облачная копия';

  @override
  String get notifyLowBalance => 'Низкий баланс компании';

  @override
  String get audienceOwnerOnly => 'Только Owner';

  @override
  String get audienceOwnerManager => 'Owner + Manager';

  @override
  String get audienceAll => 'Всем сотрудникам';

  @override
  String get balanceTitle => 'Баланс';

  @override
  String get balanceCompanyTitle => 'Баланс компании';

  @override
  String get balanceUnavailable => 'Баланс недоступен для вашей роли';

  @override
  String lowBalanceBanner(String balance, String threshold) {
    return 'Низкий баланс компании: $balance ₽ (порог $threshold ₽). Пополните счёт §20.3.5';
  }

  @override
  String get topup => 'Пополнить';

  @override
  String get topupMinAmount => 'Минимум 100 ₽';

  @override
  String get balanceTopupSuccess => 'Баланс пополнен';

  @override
  String get companyTopupSuccess => 'Баланс компании пополнен';

  @override
  String get paymentCanceled => 'Платёж отменён';

  @override
  String get lowBalanceThreshold => 'Порог низкого баланса, ₽ §20.3.5';

  @override
  String get saveThreshold => 'Сохранить порог';

  @override
  String get thresholdSaved => 'Порог низкого баланса сохранён §20.3.5';

  @override
  String get topupCompanyBtn => 'Пополнить баланс компании §19.14.2';

  @override
  String get topupAmount => 'Сумма пополнения';

  @override
  String get topupCompanyAmount => 'Пополнение компании §19.14.2';

  @override
  String get topupCard => 'Пополнить картой';

  @override
  String get topupSbpQr => 'СБП QR';

  @override
  String get sbpQrTitle => 'СБП — отсканируйте QR';

  @override
  String get sbpAutoStatus => 'Статус обновится автоматически';

  @override
  String get copyPayload => 'Скопировать payload';

  @override
  String get dateFrom => 'Дата от';

  @override
  String get dateTo => 'Дата до';

  @override
  String get txTypeLabel => 'Тип операции';

  @override
  String get txTypeAll => 'Все';

  @override
  String get txTypeTopup => 'Пополнения';

  @override
  String get txTypeCharge => 'Списания';

  @override
  String get txTypeRefund => 'Возвраты';

  @override
  String get perPage => 'На странице §20.3.4';

  @override
  String get applyFilters => 'Применить фильтры';

  @override
  String get exportCsv => 'Экспорт CSV §20.3.4';

  @override
  String get exporting => 'Экспорт…';

  @override
  String get companyTopupScreenTitle => 'Пополнение компании';

  @override
  String get companyTopupScreenHint =>
      'Owner: пополнение корпоративного счёта через ЮKassa §19.14.2';

  @override
  String get languageInterface => 'Язык интерфейса';

  @override
  String get team => 'Команда';

  @override
  String get switchMode => 'Режим Личный / Компания';

  @override
  String get localStorage => 'Локальное хранилище';

  @override
  String get localStorageSub => 'GLB, автоочистка, экспорт ZIP';

  @override
  String get calibration => 'Калибровка масштаба';

  @override
  String get calibrationSub => 'Карта / A4 / QR · §3.7';

  @override
  String get importModel => 'Импорт модели';

  @override
  String get importModelSub => 'Готовый GLB · §6.10';

  @override
  String get saveProfile => 'Сохранить профиль';

  @override
  String get profileSaved => 'Профиль сохранён';

  @override
  String balanceLabel(String amount) {
    return 'Баланс: $amount ₽';
  }
}
