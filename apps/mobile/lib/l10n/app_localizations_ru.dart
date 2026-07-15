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

  @override
  String get queueGenerationTitle => 'Генерация модели';

  @override
  String get queueCancelTitle => 'Отмена генерации';

  @override
  String get queueCancelWarning =>
      'Внимание! Отмена во время генерации не приводит к возврату средств, так как вычислительные ресурсы уже затрачены. Отменить?';

  @override
  String get queueUnderstand => 'Я понимаю';

  @override
  String get queueReconnectWs => 'Переподключить WebSocket';

  @override
  String get queueNsfwBlocked =>
      'Заказ заблокирован: NSFW на текстурах импорта. Средства возвращены на баланс компании. Аккаунт на ручной проверке до 24 ч (§10.8).';

  @override
  String queueStatus(String status) {
    return 'Статус: $status';
  }

  @override
  String queuePosition(String pos, String ewt) {
    return 'Позиция в очереди: $pos. Примерное время ожидания: $ewt мин';
  }

  @override
  String get queueWsConnected => 'WebSocket: подключено';

  @override
  String get queueWsErrorShort => 'WebSocket: ошибка';

  @override
  String get queueWsConnecting => 'WebSocket: …';

  @override
  String get queueRefresh => 'Обновить';

  @override
  String get queueCancelOrder => 'Отменить';

  @override
  String get faqSupportTitle => 'FAQ / Поддержка';

  @override
  String get faqTab => 'FAQ';

  @override
  String get faqMyTickets => 'Мои обращения';

  @override
  String faqLoadError(String error) {
    return 'Ошибка загрузки: $error';
  }

  @override
  String get faqQuestionMin => 'Вопрос: минимум 10 символов';

  @override
  String get faqDefaultSubject => 'Вопрос из приложения';

  @override
  String get faqQuestionSent => 'Вопрос отправлен';

  @override
  String get faqEmpty => 'Пока нет вопросов в FAQ';

  @override
  String get faqAskPrompt => 'Не нашли ответ? Задайте вопрос';

  @override
  String get faqSubjectOptional => 'Тема (опционально)';

  @override
  String get faqYourQuestion => 'Ваш вопрос';

  @override
  String get faqSending => 'Отправка…';

  @override
  String get faqSend => 'Отправить';

  @override
  String get faqNoTickets => 'Нет обращений';

  @override
  String faqTicketDefault(String id) {
    return 'Обращение #$id';
  }

  @override
  String get faqSupportRole => 'Поддержка';

  @override
  String get faqYouRole => 'Вы';

  @override
  String get faqClarifyHint => 'Уточняющий вопрос…';

  @override
  String get faqReply => 'Ответить';

  @override
  String get faqClose => 'Закрыть';

  @override
  String get faqTicketClosed => 'Обращение закрыто';

  @override
  String get teamTitle => 'Команда';

  @override
  String get teamNoAccess => 'Нет доступа к команде';

  @override
  String get teamMembers => 'Участники';

  @override
  String get teamNoMembers => 'Нет сотрудников';

  @override
  String get teamInvite => 'Пригласить';

  @override
  String get teamAudit => 'Аудит';

  @override
  String get teamNoAudit => 'Нет записей аудита';

  @override
  String get teamExtendAllTitle => 'Продлить все исходники';

  @override
  String get teamExtendAllBody =>
      'Продлить хранение облачных исходников для всех моделей компании на 30 дней. Лимит — 3 продления на модель (§9.1.2).';

  @override
  String get teamExtend => 'Продлить';

  @override
  String get teamExtendAllBtn => 'Продлить все исходники §9.1.2';

  @override
  String get teamMemberFallback => 'Сотрудник';

  @override
  String get teamRole => 'Роль';

  @override
  String get teamActiveOrdersLimit => 'Лимит активных заказов';

  @override
  String get teamInviteSent => 'Приглашение отправлено';

  @override
  String get teamInviteSentWithLink =>
      'Приглашение отправлено · ссылка скопирована';

  @override
  String teamMemberSubtitle(String role, String limit) {
    return '$role · лимит $limit заказов';
  }

  @override
  String teamCompany(String id) {
    return 'Компания #$id';
  }

  @override
  String get teamSendInvite => 'Отправить приглашение';

  @override
  String get mvPublishValidating => 'Проверка импорта';

  @override
  String get mvPublishImported => 'Импортировано';

  @override
  String get mvPublishImportFailed => 'Ошибка импорта';

  @override
  String get mvPublishNotPublished => 'Не опубликовано';

  @override
  String get mvPublishVerified => 'Проверено';

  @override
  String get mvPublishPublished => 'Опубликовано';

  @override
  String get mvRenameTitle => 'Переименовать модель';

  @override
  String get mvNameLabel => 'Название';

  @override
  String get mvLinkCopied => 'Ссылка скопирована';

  @override
  String get mvMovedToTrash => 'Модель перемещена в корзину';

  @override
  String get mvRetry => 'Повторить';

  @override
  String get mvNoModels => 'Пока нет моделей';

  @override
  String get mvTitle => 'Модели';

  @override
  String get mvTrash => 'Корзина';

  @override
  String get mvFilterAll => 'Все';

  @override
  String get mvFilterFavorites => 'Избранное';

  @override
  String get mvSortNewest => 'Сначала новые';

  @override
  String get mvSortOldest => 'Сначала старые';

  @override
  String get mvNoModelsFilter => 'Нет моделей по фильтру';

  @override
  String get mvDownloadGlbOzon => 'Скачать .glb (Ozon)';

  @override
  String get mvDownloadUsdzWb => 'Скачать .usdz (Wildberries)';

  @override
  String get mvShare => 'Поделиться';

  @override
  String get mvRate => 'Оценить модель';

  @override
  String get mvVerifyLink => 'Ссылка для верификации';

  @override
  String get mvEdit => 'Редактировать';

  @override
  String get mvRename => 'Переименовать';

  @override
  String get mvDelete => 'Удалить';

  @override
  String mvLinkCopiedMarketplace(String mp) {
    return 'Ссылка $mp скопирована';
  }

  @override
  String mvGlbSaved(String path) {
    return 'GLB сохранён: $path';
  }

  @override
  String get mvPublicLinkTitle => 'Публичная ссылка §3.12';

  @override
  String mvUntil(String date) {
    return 'До: $date';
  }

  @override
  String get mvNoLocalPhotosTitle => 'Нет локальных фото';

  @override
  String get mvNoLocalPhotosBody =>
      'Для перегенерации нужны 12 исходников на устройстве. Восстановить из облака или снять заново?';

  @override
  String get mvRestore => 'Восстановить';

  @override
  String get mvCantDetectCategory => 'Не удалось определить категорию/тариф';

  @override
  String get mvStorageExtended => 'Хранение продлено';

  @override
  String get mvDeleteTitle => 'Удалить модель?';

  @override
  String get mvDeleteBody =>
      'Исходные фото и модель будут перемещены в корзину на 30 дней. Продолжить?';

  @override
  String get mvInTrash => 'В корзине';

  @override
  String get mvSourcesRestored => 'Исходники восстановлены';

  @override
  String get mvCardLinkTitle => 'Ссылка на карточку';

  @override
  String get mvCardLinkHint => 'https://www.wildberries.ru/... или ozon.ru/...';

  @override
  String get mvAdd => 'Добавить';

  @override
  String mvLinkStatus(String status) {
    return 'Ссылка: $status';
  }

  @override
  String get mvRateTitle => 'Оцените качество модели от 1 до 5';

  @override
  String get mvWhatsWrong => 'Что не так?';

  @override
  String get mvReasonBlurry => 'размытые текстуры';

  @override
  String get mvReasonHoles => 'дыры или артефакты';

  @override
  String get mvReasonScale => 'неправильный масштаб';

  @override
  String get mvReasonColor => 'не тот цвет / освещение';

  @override
  String get mvReasonOther => 'другое';

  @override
  String get mvComment => 'Комментарий';

  @override
  String get mvLater => 'Позже';

  @override
  String get mvModelTitle => '3D-модель';

  @override
  String get mvGlbNotReady => 'GLB ещё не готов';

  @override
  String mvCloud(String days, String used, String max) {
    return 'Облако: $days дн. · продлений $used/$max';
  }

  @override
  String get mvLocalGlbSaved => 'Локальный GLB сохранён';

  @override
  String get mvRegenerate => 'Перегенерировать';

  @override
  String get mvUpdateGlb => 'Обновить GLB';

  @override
  String get mvGlbLocal => 'GLB локально';

  @override
  String get mvDownloadWb => 'Скачать WB';

  @override
  String get mvDownloadOzon => 'Скачать Ozon';

  @override
  String get mvSources => 'Исходники';

  @override
  String get mvExtend30 => '+30 дн.';

  @override
  String get mvToTrash => 'В корзину';

  @override
  String get mvLink => 'Ссылка';

  @override
  String get mvImOnWb => 'Я на WB';

  @override
  String get mvImOnOzon => 'Я на Ozon';

  @override
  String mvApiResult(String status) {
    return 'API: $status';
  }

  @override
  String get orderLimitTitle => 'Лимит активных заказов';

  @override
  String get orderLimitBody =>
      'Достигнут лимит одновременных заказов для вашей роли. Дождитесь завершения текущих генераций или обратитесь к Owner.';

  @override
  String get orderLimitOk => 'Понятно';

  @override
  String get trashTitle => 'Корзина';

  @override
  String get trashEmpty => 'Корзина пуста\nУдалённые модели хранятся 30 дней';

  @override
  String get trashRestore => 'Восстановить';

  @override
  String get trashRestored => 'Восстановлено';

  @override
  String trashOrderLine(String id, String date) {
    return 'Заказ #$id · в корзине $date';
  }

  @override
  String trashPurgeLine(String date) {
    return 'Удаление: $date';
  }

  @override
  String get prefPushEnabled => 'Push-уведомления';

  @override
  String get prefEmailEnabled => 'Email-уведомления';

  @override
  String get prefGenerationDone => 'Генерация готова';

  @override
  String get prefRefund => 'Возврат средств';

  @override
  String get prefNsfwBlocked => 'NSFW-блокировка';

  @override
  String get prefSourceExpire => 'Истечение исходников';

  @override
  String get prefCleanup => 'Очистка хранилища';

  @override
  String get prefPublishReminder => 'Напоминание опубликовать';

  @override
  String get prefSupportReply => 'Ответ поддержки';

  @override
  String get profileInnLabel => 'ИНН (необязательно) §19.14.1';

  @override
  String get profilePhoneLabel => 'Телефон (необязательно) §19.14.1';

  @override
  String get profileFullNameLabel => 'ФИО (необязательно) §19.14.1';

  @override
  String get profileExportFormat => 'Формат экспорта §19.14.3';

  @override
  String get profileExportGlb => '.glb (Ozon / универсальный)';

  @override
  String get profileExportUsdz => '.usdz (Wildberries / AR)';

  @override
  String get profileTheme => 'Тема оформления §19.14.3';

  @override
  String get themeSystem => 'Системная';

  @override
  String get themeLight => 'Светлая';

  @override
  String get themeDark => 'Тёмная';

  @override
  String get profileLanguage => 'Язык';

  @override
  String get profileNotificationsSection => 'Уведомления §19.14.3';

  @override
  String get profileEventsSection => 'События §3.4.3';

  @override
  String get profileSecuritySection => 'Безопасность §19.14.4';

  @override
  String get profileChangePassword => 'Изменить пароль';

  @override
  String get profileChangePasswordTitle => 'Изменить пароль';

  @override
  String get profileCurrentPassword => 'Текущий пароль';

  @override
  String get profileNewPassword => 'Новый пароль';

  @override
  String get profilePasswordConfirm => 'Подтверждение';

  @override
  String get profilePasswordChanged => 'Пароль изменён';

  @override
  String get profileMinPassword => 'Минимум 8 символов';

  @override
  String get profilePasswordMismatch => 'Пароли не совпадают';

  @override
  String get profile2faSection => 'Двухфакторная аутентификация §19.14.4';

  @override
  String get profile2faEnabled => '2FA включена';

  @override
  String get profile2faDisabled => '2FA выключена';

  @override
  String get profile2faOwnerRequired => 'Для Owner 2FA обязательна (§10.7.5)';

  @override
  String get profile2faActiveHint =>
      'TOTP активен — Google Authenticator, 1Password или аналог.';

  @override
  String get profile2faStep1 =>
      '1. Отсканируйте QR в приложении-аутентификаторе';

  @override
  String get profile2faStep2 => '2. Или введите секрет вручную';

  @override
  String get profileSecretCopied => 'Секрет скопирован';

  @override
  String get profile2faCodeLabel => 'Код из Authenticator';

  @override
  String get profileConfirm2fa => 'Подтвердить 2FA';

  @override
  String get profileEnable2fa => 'Включить 2FA';

  @override
  String get profile2faEnabledSnackbar => '2FA включена';

  @override
  String get profileDeleteAccountTitle => 'Удалить аккаунт?';

  @override
  String get profileDeleteAccountBody =>
      'Все модели и персональные данные будут удалены в течение 30 дней (§2.8.3). Финансовые записи анонимизируются и хранятся 5 лет.';

  @override
  String get profileDeleteAccountBtn => 'Удалить';

  @override
  String get profileDeleteRequestAccepted => 'Запрос принят';

  @override
  String get notifGenDoneTitle => 'Генерация завершена';

  @override
  String notifGenDoneBody(String id) {
    return 'Заказ #$id готов к просмотру';
  }

  @override
  String get notifNsfwTitle => 'NSFW-блокировка';

  @override
  String notifNsfwBody(String id) {
    return 'Заказ #$id отклонён. Средства возвращены. Аккаунт на проверке до 24 ч.';
  }

  @override
  String get notifGenFailedTitle => 'Ошибка генерации';

  @override
  String notifGenFailedBody(String id) {
    return 'Заказ #$id не выполнен';
  }

  @override
  String get notifRefundTitle => 'Возврат средств';

  @override
  String notifRefundBody(String id) {
    return 'По заказу #$id средства возвращены';
  }

  @override
  String get notifCancelledTitle => 'Заказ отменён';

  @override
  String notifCancelledBody(String id) {
    return 'Заказ #$id отменён';
  }

  @override
  String get notifCompanyInviteTitle => 'Приглашение в компанию';

  @override
  String get publishGuideTitle => 'Как опубликовать';

  @override
  String get publishGuideIntro =>
      'Скачайте файлы модели и загрузите их в карточку товара на маркетплейсе.';

  @override
  String get publishGuideWbTitle => 'Wildberries';

  @override
  String get publishGuideWb1 =>
      '1. Скачайте .usdz (кнопка «Скачать WB» в модели).';

  @override
  String get publishGuideWb2 =>
      '2. Откройте карточку товара в кабинете WB → медиа → 3D.';

  @override
  String get publishGuideWb3 => '3. Загрузите .usdz для iOS-покупателей.';

  @override
  String get publishGuideOzonTitle => 'Ozon';

  @override
  String get publishGuideOzon1 => '1. Скачайте .glb (кнопка «Скачать Ozon»).';

  @override
  String get publishGuideOzon2 =>
      '2. В кабинете Ozon откройте карточку → 3D-модель.';

  @override
  String get publishGuideOzon3 => '3. Загрузите .glb для Android-покупателей.';

  @override
  String get publishGuideOpenModels => 'К моделям';

  @override
  String get apiKeysTitle => 'API-ключи';

  @override
  String get apiKeysSubtitle => 'Owner · scopes · rate limit';

  @override
  String get apiKeysCreate => 'Создать ключ';

  @override
  String get apiKeysRevoke => 'Отозвать';

  @override
  String get apiKeysCopyOnce => 'Скопируйте ключ — он больше не покажется';

  @override
  String get apiKeysName => 'Название';

  @override
  String get apiKeysEmpty => 'Нет ключей';

  @override
  String get apiKeysCreated => 'Ключ создан';

  @override
  String get profileCopySecretBtn => 'Скопировать секрет';

  @override
  String get profile2faCodeStep => '3. Введите 6-значный код';

  @override
  String get profile2faSetupHint =>
      'Защитите аккаунт одноразовыми кодами при входе.';

  @override
  String get profileDeleteAccount => 'Удалить аккаунт';

  @override
  String get profileLogout => 'Выйти';

  @override
  String get catClothing => 'Одежда';

  @override
  String get catShoes => 'Обувь';

  @override
  String get catElectronics => 'Электроника';

  @override
  String get catFurniture => 'Мебель';

  @override
  String get catDecor => 'Декор / Интерьер';

  @override
  String get catToys => 'Игрушки';

  @override
  String get catAdult => 'Интимные товары (18+)';

  @override
  String get catOther => 'Другое';

  @override
  String get tierSmall => 'Малый';

  @override
  String get tierLarge => 'Крупный';

  @override
  String get forbIntimate => 'Интим';

  @override
  String get forbWeapons => 'Оружие';

  @override
  String get forbDrugs => 'Наркотики';

  @override
  String get angle00 => 'Низ 0° (фронт)';

  @override
  String get angle01 => 'Низ 45°';

  @override
  String get angle02 => 'Низ 90° (лево)';

  @override
  String get angle03 => 'Низ 135°';

  @override
  String get angle04 => 'Низ 180° (тыл)';

  @override
  String get angle05 => 'Низ 225°';

  @override
  String get angle06 => 'Низ 270° (право)';

  @override
  String get angle07 => 'Низ 315°';

  @override
  String get angle08 => 'Верх вперёд 45°';

  @override
  String get angle09 => 'Верх вправо 45°';

  @override
  String get angle10 => 'Верх назад 45°';

  @override
  String get angle11 => 'Верх влево 45°';

  @override
  String get wsSessionExpired => 'Сессия истекла. Войдите снова.';

  @override
  String get wsServerUnavailable =>
      'Сервер недоступен. Проверьте API_URL и сеть.';

  @override
  String get wsQueueFailed =>
      'Не удалось подключиться к очереди. Повторите позже.';

  @override
  String get wsQueueError => 'Ошибка соединения с очередью';

  @override
  String get calSaved => 'Калибровка сохранена на 30 дней';

  @override
  String get calRefFractionError => 'Укажите долю эталона в кадре (0.1–0.9)';

  @override
  String get calEnterDimensions => 'Введите размеры в метрах';

  @override
  String calCurrentLine(String method, String date) {
    return 'Текущая: $method · до $date';
  }

  @override
  String get calReset => 'Сбросить калибровку';

  @override
  String get calIntro =>
      'Для опции «Масштаб 1:1» и мебели нужна калибровка (§3.7). Положите эталон рядом с товаром и укажите, какую долю кадра он занимает.';

  @override
  String get calMethod => 'Способ';

  @override
  String get calMethodCard => 'Банковская карта (85.6×54 мм)';

  @override
  String get calMethodA4 => 'Лист A4 (210×297 мм)';

  @override
  String get calMethodQr => 'QR-код с PDF (100 мм)';

  @override
  String get calMethodManual => 'Ручной ввод размеров (м)';

  @override
  String get calRefWidth => 'Ширина эталона в кадре (0.1–0.9)';

  @override
  String get calRefHeight => 'Высота эталона в кадре (0.1–0.9)';

  @override
  String get calSave => 'Сохранить калибровку';

  @override
  String get calQrIntro =>
      'Скачайте PDF с QR-кодом эталона (100×100 мм), распечатайте и положите рядом с товаром.';

  @override
  String get calDownloadPdf => 'Скачать PDF QR';

  @override
  String get calQrSide => 'Сторона QR (мм)';

  @override
  String get calQrWidth => 'QR в кадре — ширина (доля)';

  @override
  String get calQrHeight => 'QR в кадре — высота (доля)';

  @override
  String get calSaveQr => 'Сохранить по QR';

  @override
  String get calManualW => 'Ширина товара (м)';

  @override
  String get calManualH => 'Высота товара (м)';

  @override
  String get calManualD => 'Глубина товара (м)';

  @override
  String storUsedLine(String bytes, String models, String glbs) {
    return 'Занято: $bytes · папок: $models · GLB: $glbs';
  }

  @override
  String get storAutoDownload => 'Автозагрузка GLB при завершении';

  @override
  String get storAutoDownloadDesc => '§3.3.2 — сохранять модель на устройство';

  @override
  String get storAutoCleanup => 'Автоочистка GLB';

  @override
  String storAutoCleanupDesc(String days) {
    return 'Удалять не избранные старше $days дн.';
  }

  @override
  String get storCleanupDays => 'Срок автоочистки (дней)';

  @override
  String get storDays7 => '7 дней';

  @override
  String get storDays14 => '14 дней';

  @override
  String get storDays30 => '30 дней';

  @override
  String get storDays60 => '60 дней';

  @override
  String get storDays90 => '90 дней';

  @override
  String get storCleanupNow => 'Очистить сейчас';

  @override
  String get storExportZip => 'Экспорт всех GLB в ZIP';

  @override
  String storZipCopied(String path) {
    return 'ZIP: $path (путь скопирован)';
  }

  @override
  String storGlbDeleted(String count) {
    return 'Удалено локальных GLB: $count';
  }

  @override
  String get impIntro =>
      'Загрузите готовый GLB (до 50 МБ). Доступно только Owner компании §6.10.';

  @override
  String get impFileTooBig => 'Файл больше 50 МБ (§6.10)';

  @override
  String get impOwnerOnly => 'Импорт доступен только Owner компании (§6.10)';

  @override
  String get impUploadParamsError => 'Сервер не вернул параметры загрузки';

  @override
  String get impValidating => 'Модель на проверке (GLB 2.0 / PBR / Draco)…';

  @override
  String get impDone => 'Модель импортирована';

  @override
  String get impName => 'Название';

  @override
  String get impCategory => 'Категория';

  @override
  String get impPickGlb => 'Выбрать .glb';

  @override
  String impSize(String size) {
    return 'Размер: $size';
  }

  @override
  String get impImporting => 'Импорт…';

  @override
  String get impBtn => 'Импортировать';

  @override
  String get impFree => 'Импорт бесплатный';

  @override
  String impPriceLine(String price) {
    return 'Стоимость импорта: $price ₽ (списание с баланса компании)';
  }

  @override
  String get balStatusAuto => 'Статус обновится автоматически';

  @override
  String get balTransactions => 'Транзакции';

  @override
  String balTotalLine(String total) {
    return 'Всего: $total';
  }

  @override
  String get balEmpty => 'Нет операций';

  @override
  String get balSuccess => 'Успешно';

  @override
  String get balEmployee => 'Сотрудник §8';

  @override
  String get balAll => 'Все';

  @override
  String get balThresholdInvalid => 'Укажите корректный порог';

  @override
  String balDevMock(String balance) {
    return 'Баланс: $balance ₽';
  }

  @override
  String get consentUpdatedTitle => 'Обновлены условия';

  @override
  String get consentAcceptAllSnackbar => 'Примите все обновлённые документы';

  @override
  String get consentIntro =>
      'Для продолжения работы примите новые версии документов (§2.8).';

  @override
  String get consentRead => 'Читать';

  @override
  String get consentHide => 'Скрыть текст';

  @override
  String get consentAccept => 'Принимаю';

  @override
  String get consentContinue => 'Продолжить';

  @override
  String get consentSaving => 'Сохранение…';

  @override
  String get shootLinkTitle => 'Съёмка по ссылке';

  @override
  String get shootLinkCorpMode => 'Выберите корпоративный режим';

  @override
  String get shootLinkTier => 'Тариф';

  @override
  String get shootLinkCreate => 'Создать ссылку и QR';

  @override
  String get shootLinkCopied => 'Ссылка скопирована';

  @override
  String get shootLinkCopy => 'Копировать';

  @override
  String get gdCameraRequired => 'Нужен доступ к камере';

  @override
  String gdTurnToMarker(String azimuth, String elevation) {
    return 'Поверните к AR-метке $azimuth° / $elevation°';
  }

  @override
  String gdFpsWait(String fps) {
    return 'Подождите ($fps FPS, энергосбережение)';
  }

  @override
  String get gdAlignMarker => 'Совместите камеру с AR-меткой';

  @override
  String get ucDraftNotFound => 'Черновик съёмки не найден';

  @override
  String get ucForbiddenCategory =>
      'Вы выбрали запрещённую категорию. Заказ будет отклонён без возврата средств.';

  @override
  String ucNoViewFile(String index) {
    return 'Нет файла ракурса $index';
  }

  @override
  String get gyroTiltDown => 'наклоните телефон вниз';

  @override
  String get gyroTiltUp => 'поднимите телефон';

  @override
  String gyroTurnPitch(String dir, String pitch) {
    return 'Поверните телефон: $dir (~$pitch°)';
  }

  @override
  String gyroTurnDegrees(String deg, String dir) {
    return 'Поверните телефон примерно на $deg° $dir';
  }

  @override
  String get gyroLeft => 'влево';

  @override
  String get gyroRight => 'вправо';

  @override
  String get qaBlur => 'размытие';

  @override
  String get qaOffCenter => 'не по центру';

  @override
  String get qaOverexposed => 'пересвет';

  @override
  String get qaOk => 'ok';

  @override
  String get qaCenterPhone => 'Сместите телефон так, чтобы товар был в центре';

  @override
  String get qaCloser =>
      'Приблизьте телефон так, чтобы товар занимал ~70% экрана';

  @override
  String get qaFarther =>
      'Отдалите телефон так, чтобы товар занимал ~70% экрана';

  @override
  String get checkoutPromoApply => 'Применить';

  @override
  String checkoutPromoApplied(String amount) {
    return 'Скидка −$amount ₽';
  }

  @override
  String get checkoutPromoInvalid => 'Промокод недействителен';

  @override
  String get campaignBannerDismiss => 'Скрыть';

  @override
  String get companyDefaultName => 'Компания';

  @override
  String get paymentStatusPending => 'Ожидает оплаты';

  @override
  String get paymentStatusSucceeded => 'Оплачено';

  @override
  String get paymentStatusCanceled => 'Отменено';

  @override
  String get draftRestoreTitle => 'Восстановить черновики?';

  @override
  String draftRestoreBody(String count) {
    return 'Найдено $count облачных бэкапов (TTL 7 дней, §3.3.2). Восстановить незавершённые съёмки?';
  }

  @override
  String get draftRestoredSnackbar => 'Черновики восстановлены из облака';

  @override
  String get resumeDraftTitle => 'Незавершённая съёмка';

  @override
  String resumeDraftBody(String category, String count, String total) {
    return 'У вас есть черновик ($category, $count/$total кадров). Продолжить или начать заново?';
  }

  @override
  String get resumeDraftDiscard => 'Заново';

  @override
  String get resumeDraftContinue => 'Продолжить';
}
