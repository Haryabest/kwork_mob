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

  @override
  String get exportShareText => 'Транзакции §20.3.4';

  @override
  String get exportSuccess => 'CSV экспортирован';

  @override
  String get open => 'Открыть';

  @override
  String get notificationDefault => 'Уведомление';

  @override
  String get authCreateAccount => 'Создайте аккаунт';

  @override
  String get authVerifyEmail => 'Подтверждение email';

  @override
  String get authAccountType => 'Тип аккаунта';

  @override
  String get authForgotPasswordTitle => 'Восстановление пароля';

  @override
  String get authNewPasswordTitle => 'Новый пароль';

  @override
  String get authTwoFaTitle => 'Введите код 2FA';

  @override
  String get authSendLink => 'Отправить ссылку';

  @override
  String get authSavePassword => 'Сохранить пароль';

  @override
  String get authRememberMe => 'Запомнить меня';

  @override
  String get authPasswordConfirm => 'Подтверждение пароля';

  @override
  String get authConsents =>
      'Принимаю соглашение, политику ПДн, оферту, подтверждение прав и правила запрещённого контента';

  @override
  String get authEmailCode => 'Код из письма (6 цифр)';

  @override
  String get authIndividual => 'Физ. лицо';

  @override
  String get authLegal => 'Юр. лицо / ИП';

  @override
  String get authFullNameOptional => 'ФИО (необязательно)';

  @override
  String get authOrgName => 'Наименование организации';

  @override
  String get authInn => 'ИНН';

  @override
  String get authOgrn => 'ОГРН / ОГРНИП';

  @override
  String get authLegalAddress => 'Юридический адрес';

  @override
  String get authDirectorName => 'ФИО руководителя';

  @override
  String get authBankName => 'Банк';

  @override
  String get authBik => 'БИК';

  @override
  String get authCheckingAccount => 'Расчётный счёт';

  @override
  String get authResetToken => 'Токен из письма';

  @override
  String get authNewPasswordField => 'Новый пароль';

  @override
  String get authAuthenticatorCode => 'Код из Authenticator';

  @override
  String get authBack => 'Назад';

  @override
  String get authBackToLogin => 'Назад ко входу';

  @override
  String get authAcceptTerms => 'Примите условия сервиса';

  @override
  String get authPasswordUpdated => 'Пароль обновлён. Войдите с новым паролем';

  @override
  String authDevCode(String code) {
    return 'Dev-код: $code';
  }

  @override
  String authDevToken(String token) {
    return 'Dev-токен: $token';
  }

  @override
  String get shootCategoryTitle => 'Категория товара';

  @override
  String get shootCategoryLabel => 'Категория';

  @override
  String get shootForbiddenCategories => 'Запрещённые категории';

  @override
  String get shootForbiddenHint =>
      'Если отметите — заказ не создаётся, средства не списываются';

  @override
  String get shootAgeConfirmed => 'Возраст подтверждён';

  @override
  String get shootAgeConfirmedSub => 'Повторный ввод даты не требуется';

  @override
  String get shootBirthDate => 'Дата рождения (YYYY-MM-DD)';

  @override
  String get shootBirthDateHint =>
      'Сохраняется в профиле после успешной проверки';

  @override
  String get shootScaleRequired => 'Масштаб (м) — обязательно для мебели';

  @override
  String get shootCalibrationBtn => 'Калибровка: карта / A4 / QR (§3.7)';

  @override
  String get shootLength => 'Длина';

  @override
  String get shootWidth => 'Ширина';

  @override
  String get shootHeight => 'Высота';

  @override
  String get shootModelName => 'Название модели (необязательно)';

  @override
  String get shootModelNameHint => 'Например: Кроссовки Nike Air';

  @override
  String get shootTier => 'Тариф';

  @override
  String get shootGhostMeshHint => 'Ghost Mesh — масштаб двумя пальцами';

  @override
  String get shootNext => 'Далее к съёмке';

  @override
  String get shootAgeConfirmTitle => 'Подтвердите, что вам 18 лет';

  @override
  String get shootAgeConfirmBody => 'Введите дату рождения (YYYY-MM-DD).';

  @override
  String get shootInvalidDate => 'Некорректная дата (YYYY-MM-DD)';

  @override
  String get shootAgeOnly18 => 'Создание модели доступно только с 18 лет';

  @override
  String get shootBirthRequired => 'Укажите дату рождения для 18+';

  @override
  String get shootForbiddenTitle => 'Запрещённая категория';

  @override
  String get shootForbiddenBody =>
      'Вы выбрали запрещённую категорию. Заказ будет отклонён без возврата средств. Продолжить?';

  @override
  String get shootOrderBlocked => 'Заказ не будет создан — смените категорию';

  @override
  String shootStorageFree(String need, String free) {
    return 'Освободите место на телефоне (нужно $need МБ, доступно ~$free МБ)';
  }

  @override
  String shootStorageFreeUnknown(String need) {
    return 'Освободите место на телефоне (нужно $need МБ)';
  }

  @override
  String get shootQualityTitle => 'Проверка качества';

  @override
  String get shootQualityLow =>
      'Низкое качество фото. Постарайтесь улучшить условия съемки';

  @override
  String get shootQualityLowTitle => 'Низкое качество';

  @override
  String get shootQualityLowDialog =>
      'Некоторые кадры имеют низкое качество, это может привести к браку модели. Продолжить?';

  @override
  String get yes => 'Да';

  @override
  String get no => 'Нет';

  @override
  String get shootQualityContinue => 'Продолжить к загрузке';

  @override
  String get shootQualityContinueForce => 'Продолжить, несмотря на ошибки';

  @override
  String get shootQualityRestart => 'Начать съёмку с начала';

  @override
  String shootArHint(String tier, String scale) {
    return 'AR: тариф «$tier», габариты $scale';
  }

  @override
  String get shootTitle => 'Съёмка';

  @override
  String get shootOverheatTitle => 'Перегрев телефона';

  @override
  String shootOverheatBody(String temp) {
    return 'Температура батареи ≈ $temp°C (>45°C). Рекомендуем прервать съёмку до охлаждения. При продолжении включится энергосбережение (FPS 15).';
  }

  @override
  String get shootAbort => 'Прервать';

  @override
  String get shootExit => 'Выход';

  @override
  String get shootCalibrateShort => 'Калибр.';

  @override
  String get shootArCameraActive => 'AR-камера активна';

  @override
  String shootAngleLine(
    String current,
    String total,
    String label,
    String backend,
  ) {
    return 'Ракурс $current/$total · $label · $backend';
  }

  @override
  String get uploadPhotoTitle => 'Загрузка фото';

  @override
  String get uploadPreparing => 'Подготовка…';

  @override
  String uploadResumeFound(String done) {
    return 'Найдена незавершённая загрузка ($done/12)';
  }

  @override
  String get uploadResumeHint =>
      '§3.4.1: прогресс сохранён локально. При обрыве связи загрузка продолжится с последнего фото.';

  @override
  String get uploadBuildingZip => 'Сборка ZIP + SHA-256…';

  @override
  String uploadSha256(String hash) {
    return 'SHA-256: $hash…';
  }

  @override
  String get uploadPresigned => 'Получение presigned URL…';

  @override
  String get uploadEncrypting => 'E2E шифрование фото…';

  @override
  String uploadProgress(String current, String total) {
    return 'Загрузка $current/$total…';
  }

  @override
  String uploadUploaded(String done) {
    return 'Загружено $done/12';
  }

  @override
  String get uploadInterrupted => 'Загрузка прервана — можно продолжить';

  @override
  String get uploadUploading => 'Загрузка…';

  @override
  String get uploadContinue => 'Продолжить загрузку';

  @override
  String get upload12Photos => 'Загрузить 12 фото';

  @override
  String get checkoutTitle => 'Оплата';

  @override
  String get checkoutPayTitle => 'Оплата заказа';

  @override
  String get checkoutSubmitGeneration => 'Отправка на генерацию';

  @override
  String get checkoutNeedCalibration => 'Нужна калибровка';

  @override
  String get checkoutCalibrationBody =>
      'Для «Масштаб 1:1» выполните калибровку по карте, A4 или QR (§3.7).';

  @override
  String get checkoutCalibrate => 'Калибровать';

  @override
  String checkoutCategory(String label) {
    return 'Категория: $label';
  }

  @override
  String checkoutTier(String label) {
    return 'Тариф: $label';
  }

  @override
  String checkoutBasePrice(String amount) {
    return 'Базовая цена: $amount ₽';
  }

  @override
  String get checkoutUpsells => 'Дополнительные услуги';

  @override
  String checkoutTotal(String amount) {
    return 'Итого: $amount ₽';
  }

  @override
  String get checkoutPromo => 'Промокод';

  @override
  String get checkoutFioOptional => 'ФИО (необязательно)';

  @override
  String get checkoutFioHint => 'Можно пропустить';

  @override
  String get checkoutFioTaxHint =>
      'ФИО используется для чека «Мой налог» (§19.8.1)';

  @override
  String get checkoutPayCard => 'Оплатить картой';

  @override
  String get checkoutPaySbp => 'Оплатить СБП (QR)';

  @override
  String get checkoutSbpOrderTitle => 'СБП — оплата заказа';

  @override
  String get guestShootTitle => 'Съёмка по ссылке';

  @override
  String guestTask(String id) {
    return 'Задача $id…';
  }

  @override
  String guestMeta(String category, String tier) {
    return 'Категория: $category · тариф: $tier';
  }

  @override
  String get guestHint =>
      'Гостевой режим: 12 ракурсов через AR или галерею (§3.15).';

  @override
  String get guestStartAr => 'Начать AR-съёмку';

  @override
  String get guestGallery12 => '12 фото из галереи';

  @override
  String guestPhotosRequired(String need, String selected) {
    return 'Нужно ровно $need фото (выбрано $selected)';
  }

  @override
  String get guestUploadTitle => 'Отправка по ссылке';

  @override
  String get guestReadyToSend => 'Готово к отправке';

  @override
  String get guestGettingUrls => 'Получение upload URL…';

  @override
  String guestUploading(String current) {
    return 'Загрузка $current/12…';
  }

  @override
  String get guestConfirming => 'Подтверждение…';

  @override
  String get guestSentToOwner => 'Фото отправлены владельцу';

  @override
  String get guestSend12Photos => 'Отправить 12 фото';

  @override
  String get guestLinkUsed =>
      'Ссылка использована. Владелец компании получит уведомление.';

  @override
  String get prefTopupFailed => 'Ошибка пополнения';

  @override
  String homePendingUploadTitle(String uploaded, String total) {
    return 'Незавершённая загрузка фото ($uploaded/$total)';
  }

  @override
  String get homePendingUploadHint =>
      'Загрузка прервалась. Можно продолжить с последнего кадра.';

  @override
  String homeModePrefix(String mode) {
    return 'Режим: $mode';
  }

  @override
  String get homeNoCompanies => 'Нет привязанных компаний';

  @override
  String get homeSwitchModeTitle => 'Сменить режим?';

  @override
  String get homeSwitchModeBody => 'Подтвердите переключение Личный / Компания';

  @override
  String get homeShootLinkQr => 'Съёмка по ссылке (QR)';

  @override
  String get ordersExecutorFilter => 'Исполнитель §3.16.2';

  @override
  String get ordersAllMembers => 'Все сотрудники';

  @override
  String get ordersEmpty => 'Нет заказов';

  @override
  String get orderStatusPending => 'Новый';

  @override
  String get orderStatusAwaitingPayment => 'Ожидает оплаты';

  @override
  String get orderStatusQueued => 'В очереди';

  @override
  String get orderStatusProcessing => 'В обработке';

  @override
  String get orderStatusCompleted => 'Готов';

  @override
  String get orderStatusFailed => 'Ошибка';

  @override
  String get orderStatusCancelled => 'Отменён';

  @override
  String get orderStatusPaid => 'Оплачен';

  @override
  String get orderStatusBlockedNsfw => 'NSFW блок';

  @override
  String get notificationsTitle => 'Уведомления';

  @override
  String get notificationsEmpty => 'Нет уведомлений';
}
