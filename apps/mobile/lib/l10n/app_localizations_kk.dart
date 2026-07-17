// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Kazakh (`kk`).
class AppLocalizationsKk extends AppLocalizations {
  AppLocalizationsKk([String locale = 'kk']) : super(locale);

  @override
  String get appName => 'KWork Mob';

  @override
  String get authTitle => 'Кіру';

  @override
  String get email => 'Email';

  @override
  String get password => 'Құпия сөз';

  @override
  String get login => 'Кіру';

  @override
  String get register => 'Тіркелу';

  @override
  String get forgotPassword => 'Құпия сөзді ұмыттыңыз ба?';

  @override
  String get home => 'Басты';

  @override
  String get models => 'Модельдер';

  @override
  String get orders => 'Тапсырыстар';

  @override
  String get support => 'Қолдау';

  @override
  String get profile => 'Профиль';

  @override
  String get shoot => 'Тауарды түсіру';

  @override
  String get queue => 'Кезек';

  @override
  String get faq => 'FAQ';

  @override
  String get personalMode => 'Жеке';

  @override
  String get corporateMode => 'Компания';

  @override
  String get onboarding1 => 'Тауарды 12 бұрыштан түсіріңіз';

  @override
  String get onboarding2 => 'Тарифті төлеп, генерацияны күтіңіз';

  @override
  String get onboarding3 => 'Маркетплейс үшін .glb / .usdz жүктеп алыңыз';

  @override
  String get onboarding4 => 'Модельді WB немесе Ozon-ға жариялаңыз';

  @override
  String get onboardingSub1 =>
      '12 Guided Dome бұрышы → маркетплейс үшін 3D-модель';

  @override
  String get onboardingSub2 =>
      'ARKit / ARCore немесе гироскоп ±15° бұрышты көрсетеді. 1:1 масштаб үшін — профильде карта немесе A4 арқылы калибрлеу.';

  @override
  String get onboardingSub3 =>
      'GLB/USDZ жүктеп алып, Wildberries немесе Ozon-ға жариялаңыз';

  @override
  String get onboardingSub4 =>
      '40°C-ден жоғары қызу кезінде түсіру энергия үнемдеу режиміне өтеді (15 FPS)';

  @override
  String get skip => 'Өткізу';

  @override
  String get alreadyHaveAccount => 'Аккаунтыңыз бар ма? Кіру';

  @override
  String get continueBtn => 'Жалғастыру';

  @override
  String get errorNetwork => 'Интернет жоқ';

  @override
  String get comingSoon => 'Экран әзірленуде';

  @override
  String get save => 'Сақтау';

  @override
  String get cancel => 'Болдырмау';

  @override
  String get confirm => 'Растау';

  @override
  String get done => 'Дайын';

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
  String get companyTopupTitle => 'Компания балансы';

  @override
  String get companyTopupSubtitle => 'Шотты толтыру · §19.14.2';

  @override
  String get companyPoliciesTitle => 'Компания саясаты';

  @override
  String get companyPoliciesSubtitle =>
      'Қол жеткізу және хабарландыру · §19.14.2';

  @override
  String companyBalanceLabel(String balance) {
    return 'Компания балансы: $balance ₽';
  }

  @override
  String get policiesMaxConcurrent => 'Бір уақыттағы тапсырыс лимиті (әдепкі)';

  @override
  String get policiesNoMonthlyLimit => 'Айлық шығын лимиті жоқ';

  @override
  String get policiesMonthlyLimit => 'Айлық шығын лимиті (₽)';

  @override
  String get policiesAllowedCategories => 'Рұksat etılген категориялар';

  @override
  String get policiesAllowDownload => 'Photographer модельдерді жүктей алады';

  @override
  String get policiesAllowLinks =>
      'Photographer жариялау сілтемелерін қоса алады';

  @override
  String get policiesRequire2fa => 'Барлық қызметкерлерге 2FA міндетті';

  @override
  String get policiesAutoBlock => 'Белсенсіздік кезінде авто-блок (күн)';

  @override
  String get policiesLowBalanceThreshold => 'Төмен баланс порогы (₽)';

  @override
  String get policiesNotifySection => 'Owner хабарландырулары (§3.19)';

  @override
  String get policiesNotifyHint =>
      'Компания оқиғалары бойынша push/email кімге жіберіледі';

  @override
  String get policiesSaved => 'Саясат сақталды';

  @override
  String get policiesInvalidConcurrent =>
      '1–20 аралығында тапсырыс лимитін көрсетіңіз';

  @override
  String get policiesInvalidAutoBlock => 'Дұрыс авто-блок мерзімін көрсетіңіз';

  @override
  String get policiesInvalidThreshold => 'Дұрыс баланс порогын көрсетіңіз';

  @override
  String get policiesInvalidMonthly => 'Дұрыс айлық лимитті көрсетіңіз';

  @override
  String get notifyGenerationDone => 'Генерация аяқталды';

  @override
  String get notifyPhotographerUploaded => 'Фотограф фото жүктеді';

  @override
  String get notifySourceExpire => 'Бұлттық көшірме мерзімі аяқталуда';

  @override
  String get notifyLowBalance => 'Компания балансы төмен';

  @override
  String get audienceOwnerOnly => 'Тек Owner';

  @override
  String get audienceOwnerManager => 'Owner + Manager';

  @override
  String get audienceAll => 'Барлық қызметкерлер';

  @override
  String get balanceTitle => 'Баланс';

  @override
  String get balanceCompanyTitle => 'Компания балансы';

  @override
  String get balanceUnavailable => 'Сіздің рөліңіз үшін баланс қолжетімсіз';

  @override
  String lowBalanceBanner(String balance, String threshold) {
    return 'Компания балансы төмен: $balance ₽ (порог $threshold ₽). Шотты толтырыңыз §20.3.5';
  }

  @override
  String get topup => 'Толтыру';

  @override
  String get topupMinAmount => 'Минимум 100 ₽';

  @override
  String get balanceTopupSuccess => 'Баланс толтырылды';

  @override
  String get companyTopupSuccess => 'Компания балансы толтырылды';

  @override
  String get paymentCanceled => 'Төлем болдырылмады';

  @override
  String get lowBalanceThreshold => 'Төмен баланс порогы, ₽ §20.3.5';

  @override
  String get saveThreshold => 'Порогты сақтау';

  @override
  String get thresholdSaved => 'Төмен баланс порогы сақталды §20.3.5';

  @override
  String get topupCompanyBtn => 'Компания балансын толтыру §19.14.2';

  @override
  String get topupAmount => 'Толтыру сомасы';

  @override
  String get topupCompanyAmount => 'Компания толтыруы §19.14.2';

  @override
  String get topupCard => 'Картамен толтыру';

  @override
  String get topupSbpQr => 'СБП QR';

  @override
  String get sbpQrTitle => 'СБП — QR сканерлеңіз';

  @override
  String get sbpAutoStatus => 'Күй автоматты жаңартылады';

  @override
  String get copyPayload => 'Payload көшіру';

  @override
  String get dateFrom => 'Күннен';

  @override
  String get dateTo => 'Күнге дейін';

  @override
  String get txTypeLabel => 'Операция түрі';

  @override
  String get txTypeAll => 'Барлығы';

  @override
  String get txTypeTopup => 'Толтырулар';

  @override
  String get txTypeCharge => 'Есептен шығару';

  @override
  String get txTypeRefund => 'Қайтарулар';

  @override
  String get perPage => 'Бетте §20.3.4';

  @override
  String get applyFilters => 'Сүзгілерді қолдану';

  @override
  String get exportCsv => 'CSV экспорт §20.3.4';

  @override
  String get exporting => 'Экспорт…';

  @override
  String get companyTopupScreenTitle => 'Компания толтыруы';

  @override
  String get companyTopupScreenHint =>
      'Owner: корпоративтік шотты ЮKassa арқылы толтыру §19.14.2';

  @override
  String get languageInterface => 'Интерфейс тілі';

  @override
  String get team => 'Команда';

  @override
  String get switchMode => 'Жеке / Компания режимі';

  @override
  String get localStorage => 'Жергілікті сақтау';

  @override
  String get localStorageSub => 'GLB, авто-тазалау, ZIP экспорт';

  @override
  String get calibration => 'Масштаб калибрлеу';

  @override
  String get calibrationSub => 'Карта / A4 / QR · §3.7';

  @override
  String get importModel => 'Модель импорты';

  @override
  String get importModelSub => 'Дайын GLB · §6.10';

  @override
  String get saveProfile => 'Профильді сақтау';

  @override
  String get profileSaved => 'Профиль сақталды';

  @override
  String balanceLabel(String amount) {
    return 'Баланс: $amount ₽';
  }

  @override
  String get exportShareText => 'Транзакциялар §20.3.4';

  @override
  String get exportSuccess => 'CSV экспортталды';

  @override
  String get open => 'Ашу';

  @override
  String get notificationDefault => 'Хабарландыру';

  @override
  String get authCreateAccount => 'Аккаунт жасау';

  @override
  String get authVerifyEmail => 'Email растау';

  @override
  String get authAccountType => 'Аккаунт түрі';

  @override
  String get authForgotPasswordTitle => 'Құпия сөзді қалпына келтіру';

  @override
  String get authNewPasswordTitle => 'Жаңа құпия сөз';

  @override
  String get authTwoFaTitle => '2FA кодын енгізіңіз';

  @override
  String get authSendLink => 'Сілтеме жіберу';

  @override
  String get authSavePassword => 'Құпия сөзді сақтау';

  @override
  String get authRememberMe => 'Мені есте сақта';

  @override
  String get authPasswordConfirm => 'Құпия сөзді растау';

  @override
  String get authConsents =>
      'Келісім, ДҚ саясаты, оферта, құқықтар растауы және тыйым салынған контент ережелерін қабылдаймын';

  @override
  String get authEmailCode => 'Хаттағы код (6 цифр)';

  @override
  String get authIndividual => 'Жеке тұлға';

  @override
  String get authLegal => 'ЗТ / ЖК';

  @override
  String get authFullNameOptional => 'ТАӘ (міндетті емес)';

  @override
  String get authOrgName => 'Ұйым атауы';

  @override
  String get authInn => 'ЖСН';

  @override
  String get authOgrn => 'БСН / ЖКБСН';

  @override
  String get authLegalAddress => 'Заңды мекенжай';

  @override
  String get authDirectorName => 'Басшының ТАӘ';

  @override
  String get authBankName => 'Банк';

  @override
  String get authBik => 'БСК';

  @override
  String get authCheckingAccount => 'Есеп шоты';

  @override
  String get authResetToken => 'Хаттағы токен';

  @override
  String get authNewPasswordField => 'Жаңа құпия сөз';

  @override
  String get authAuthenticatorCode => 'Authenticator коды';

  @override
  String get authBack => 'Артқа';

  @override
  String get authBackToLogin => 'Кіруге оралу';

  @override
  String get authAcceptTerms => 'Қызмет шарттарын қабылдаңыз';

  @override
  String get authPasswordUpdated =>
      'Құпия сөз жаңартылды. Жаңа құпия сөзбен кіріңіз';

  @override
  String authDevCode(String code) {
    return 'Dev-код: $code';
  }

  @override
  String authDevToken(String token) {
    return 'Dev-токен: $token';
  }

  @override
  String get shootCategoryTitle => 'Тауар категориясы';

  @override
  String get shootCategoryLabel => 'Категория';

  @override
  String get shootForbiddenCategories => 'Тыйым салынған категориялар';

  @override
  String get shootForbiddenHint =>
      'Белgilenseniz — тапсырыс жасалмайды, қаражат алынбайды';

  @override
  String get shootAgeConfirmed => 'Жас расталды';

  @override
  String get shootAgeConfirmedSub => 'Күнді қайта енгізу қажет емес';

  @override
  String get shootBirthDate => 'Туған күні (YYYY-MM-DD)';

  @override
  String get shootBirthDateHint => 'Сәтті тексеруден кейін профильде сақталады';

  @override
  String get shootScaleRequired => 'Масштаб (м) — жиһаз үшін міндетті';

  @override
  String get shootCalibrationBtn => 'Калибрлеу: карта / A4 / QR (§3.7)';

  @override
  String get shootLength => 'Ұзындығы';

  @override
  String get shootWidth => 'Ені';

  @override
  String get shootHeight => 'Биіктігі';

  @override
  String get shootModelName => 'Модель атауы (міндетті емес)';

  @override
  String get shootModelNameHint => 'Мысалы: Nike Air кроссовкалары';

  @override
  String get shootTier => 'Тариф';

  @override
  String get shootGhostMeshHint => 'Ghost Mesh — екі саусақпен масштаб';

  @override
  String get shootNext => 'Түсіруге өту';

  @override
  String get shootAgeConfirmTitle => '18 жасқа толғаныңызды растаңыз';

  @override
  String get shootAgeConfirmBody => 'Туған күнді енгізіңіз (YYYY-MM-DD).';

  @override
  String get shootInvalidDate => 'Дұрыс емес күн (YYYY-MM-DD)';

  @override
  String get shootAgeOnly18 => 'Модель жасау тек 18 жастан бастап';

  @override
  String get shootBirthRequired => '18+ үшін туған күнді көрсетіңіз';

  @override
  String get shootForbiddenTitle => 'Тыйым салынған категория';

  @override
  String get shootForbiddenBody =>
      'Тыйым салынған категория таңдалды. Тапсырыс қайтарусыз қабылданбайды. Жалғастыру?';

  @override
  String get shootOrderBlocked =>
      'Тапсырыс жасалмайды — категорияны өзгертіңіз';

  @override
  String shootStorageFree(String need, String free) {
    return 'Телефонда орын босатыңыз (керек $need МБ, ~$free МБ бар)';
  }

  @override
  String shootStorageFreeUnknown(String need) {
    return 'Телефонда орын босатыңыз (керек $need МБ)';
  }

  @override
  String get shootQualityTitle => 'Сапаны тексеру';

  @override
  String get shootQualityLow =>
      'Фото сапасы төмен. Түсіру жағдайларын жақсартып көріңіз';

  @override
  String get shootQualityLowTitle => 'Төмен сапа';

  @override
  String get shootQualityLowDialog =>
      'Кейбір кадрлардың сапасы төмен, бұл модель брагіне әкелуі мүмкін. Жалғастыру?';

  @override
  String get yes => 'Иә';

  @override
  String get no => 'Жоқ';

  @override
  String get shootQualityContinue => 'Жүктеуге өту';

  @override
  String get shootQualityContinueForce => 'Қателерге қарамастан жалғастыру';

  @override
  String get shootQualityRestart => 'Түсіруді басынан бастау';

  @override
  String shootArHint(String tier, String scale) {
    return 'AR: тариф «$tier», өлшемдер $scale';
  }

  @override
  String get shootTitle => 'Түсіру';

  @override
  String get shootOverheatTitle => 'Телефон қызу';

  @override
  String shootOverheatBody(String temp) {
    return 'Батарея температуры ≈ $temp°C (>45°C). Суытуға дейін тоқтату ұсынылады. Жалғастырсаңыз — энергия үнемдеу (15 FPS).';
  }

  @override
  String get shootAbort => 'Тоқтату';

  @override
  String get shootExit => 'Шығу';

  @override
  String get shootCalibrateShort => 'Кalib.';

  @override
  String get shootArCameraActive => 'AR-кamera белсенді';

  @override
  String shootAngleLine(
    String current,
    String total,
    String label,
    String backend,
  ) {
    return 'Бұрыш $current/$total · $label · $backend';
  }

  @override
  String get uploadPhotoTitle => 'Фото жүктеу';

  @override
  String get uploadPreparing => 'Дайындалуда…';

  @override
  String uploadResumeFound(String done) {
    return 'Аяқталмаған жүктеу ($done/12)';
  }

  @override
  String get uploadResumeHint =>
      '§3.4.1: прогресс жергілікті сақталды. Байланыс үзілсе, соңғы фотодан жалғасады.';

  @override
  String get uploadBuildingZip => 'ZIP + SHA-256 жинау…';

  @override
  String uploadSha256(String hash) {
    return 'SHA-256: $hash…';
  }

  @override
  String get uploadPresigned => 'Presigned URL алу…';

  @override
  String get uploadEncrypting => 'E2E фото шифрлеу…';

  @override
  String uploadProgress(String current, String total) {
    return 'Жүктеу $current/$total…';
  }

  @override
  String uploadUploaded(String done) {
    return 'Жүктелді $done/12';
  }

  @override
  String get uploadInterrupted => 'Жүктеу үзildi — жалғастыруға болады';

  @override
  String get uploadUploading => 'Жүктелуде…';

  @override
  String get uploadContinue => 'Жүктеуді жалғастыру';

  @override
  String get upload12Photos => '12 фото жүктеу';

  @override
  String get checkoutTitle => 'Төлем';

  @override
  String get checkoutPayTitle => 'Тапсырыс төлемі';

  @override
  String get checkoutSubmitGeneration => 'Генерацияға жіберу';

  @override
  String get checkoutNeedCalibration => 'Калибрлеу қажет';

  @override
  String get checkoutCalibrationBody =>
      '«1:1 масштаб» үшін карта, A4 немесе QR арқылы калибрлеңіз (§3.7).';

  @override
  String get checkoutCalibrate => 'Калибрлеу';

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
    return 'Негізгі баға: $amount ₽';
  }

  @override
  String get checkoutUpsells => 'Қосымша қызметтер';

  @override
  String checkoutTotal(String amount) {
    return 'Барлығы: $amount ₽';
  }

  @override
  String get checkoutPromo => 'Промокод';

  @override
  String get checkoutFioOptional => 'ТАӘ (міндетті емес)';

  @override
  String get checkoutFioHint => 'Өткізуге болады';

  @override
  String get checkoutFioTaxHint => 'ТАӘ «Мой налог» чекі үшін (§19.8.1)';

  @override
  String get checkoutPayCard => 'Картамен төлеу';

  @override
  String get checkoutPaySbp => 'СБП (QR) арқылы төлеу';

  @override
  String get checkoutSbpOrderTitle => 'СБП — тапсырыс төлемі';

  @override
  String get guestShootTitle => 'Сілтеме арқылы түсіру';

  @override
  String guestTask(String id) {
    return 'Тапсырма $id…';
  }

  @override
  String guestMeta(String category, String tier) {
    return 'Категория: $category · тариф: $tier';
  }

  @override
  String get guestHint =>
      'Қонақ режимі: AR немесе галерея арқылы 12 бұрыш (§3.15).';

  @override
  String get guestStartAr => 'AR түсіруді бастау';

  @override
  String get guestGallery12 => 'Галереядан 12 фото';

  @override
  String guestPhotosRequired(String need, String selected) {
    return 'Дәл $need фото керек (таңдалды $selected)';
  }

  @override
  String get guestUploadTitle => 'Сілтеме арқылы жіберу';

  @override
  String get guestReadyToSend => 'Жіберуге дайын';

  @override
  String get guestGettingUrls => 'Upload URL алу…';

  @override
  String guestUploading(String current) {
    return 'Жүктеу $current/12…';
  }

  @override
  String get guestConfirming => 'Растау…';

  @override
  String get guestSentToOwner => 'Фото иесіне жіберілді';

  @override
  String guestMissingFrame(String index) {
    return 'Кадр файлы жоқ $index';
  }

  @override
  String get guestSend12Photos => '12 фото жіберу';

  @override
  String get guestLinkUsed =>
      'Сілтеме пайдаланылды. Компания иесіне хабарланады.';

  @override
  String get prefTopupFailed => 'Толықтыру қатесі';

  @override
  String homePendingUploadTitle(String uploaded, String total) {
    return 'Аяқталмаған фото жүктеу ($uploaded/$total)';
  }

  @override
  String get homePendingUploadHint =>
      'Жүктеу үзілді. Соңғы кадрдан жалғастыруға болады.';

  @override
  String homeModePrefix(String mode) {
    return 'Режим: $mode';
  }

  @override
  String get homeNoCompanies => 'Байланған компаниялар жоқ';

  @override
  String get homeSwitchModeTitle => 'Режимді ауыстыру?';

  @override
  String get homeSwitchModeBody => 'Жеке / Компания ауыстыруды растаңыз';

  @override
  String get homeShootLinkQr => 'Ссылка бойынша түсіру (QR)';

  @override
  String get ordersExecutorFilter => 'Орындаушы §3.16.2';

  @override
  String get ordersAllMembers => 'Барлық қызметкерлер';

  @override
  String get ordersEmpty => 'Тапсырыстар жоқ';

  @override
  String get orderStatusPending => 'Жаңа';

  @override
  String get orderStatusAwaitingPayment => 'Төлем күтілуде';

  @override
  String get orderStatusQueued => 'Кезекте';

  @override
  String get orderStatusProcessing => 'Өңделуде';

  @override
  String get orderStatusCompleted => 'Дайын';

  @override
  String get orderStatusFailed => 'Қате';

  @override
  String get orderStatusCancelled => 'Бас тартылды';

  @override
  String get orderStatusPaid => 'Төленді';

  @override
  String get orderStatusBlockedNsfw => 'NSFW блок';

  @override
  String get notificationsTitle => 'Хабарландырулар';

  @override
  String get notificationsEmpty => 'Хабарландырулар жоқ';

  @override
  String get queueGenerationTitle => 'Модель генерациясы';

  @override
  String get queueCancelTitle => 'Генерацияны болдырмау';

  @override
  String get queueCancelWarning =>
      'Назар аударыңыз! Генерация кезінде болдырмау қаражатты қайтаруға әкелмейді, себебі есептеу ресурстары жұмсалған. Болдырмайсыз ба?';

  @override
  String get queueUnderstand => 'Түсінемін';

  @override
  String get queueReconnectWs => 'WebSocket-ті қайта қосу';

  @override
  String get queueNsfwBlocked =>
      'Тапсырыс бұғатталды: импорт текстураларында NSFW. Қаражат компания балансына қайтарылды. Аккаунт 24 сағатқа дейін қолмен тексеруде (§10.8).';

  @override
  String queueStatus(String status) {
    return 'Күйі: $status';
  }

  @override
  String queuePosition(String pos, String ewt) {
    return 'Кезектегі орын: $pos. Болжамды күту уақыты: $ewt мин';
  }

  @override
  String get queueWsConnected => 'WebSocket: қосылды';

  @override
  String get queueWsErrorShort => 'WebSocket: қате';

  @override
  String get queueWsConnecting => 'WebSocket: …';

  @override
  String get queueRefresh => 'Жаңарту';

  @override
  String get queueCancelOrder => 'Болдырмау';

  @override
  String get faqSupportTitle => 'FAQ / Қолдау';

  @override
  String get faqTab => 'FAQ';

  @override
  String get faqMyTickets => 'Менің өтініштерім';

  @override
  String faqLoadError(String error) {
    return 'Жүктеу қатесі: $error';
  }

  @override
  String get faqQuestionMin => 'Сұрақ: кемінде 10 таңба';

  @override
  String get faqDefaultSubject => 'Қосымшадан сұрақ';

  @override
  String get faqQuestionSent => 'Сұрақ жіберілді';

  @override
  String get faqEmpty => 'FAQ-та әзірге сұрақтар жоқ';

  @override
  String get faqAskPrompt => 'Жауап таппадыңыз ба? Сұрақ қойыңыз';

  @override
  String get faqSubjectOptional => 'Тақырып (міндетті емес)';

  @override
  String get faqYourQuestion => 'Сіздің сұрағыңыз';

  @override
  String get faqSending => 'Жіберілуде…';

  @override
  String get faqSend => 'Жіберу';

  @override
  String get faqNoTickets => 'Өтініштер жоқ';

  @override
  String faqTicketDefault(String id) {
    return 'Өтініш #$id';
  }

  @override
  String get faqSupportRole => 'Қолдау';

  @override
  String get faqYouRole => 'Сіз';

  @override
  String get faqClarifyHint => 'Нақтылаушы сұрақ…';

  @override
  String get faqReply => 'Жауап беру';

  @override
  String get faqClose => 'Жабу';

  @override
  String get faqTicketClosed => 'Өтініш жабылды';

  @override
  String get teamTitle => 'Команда';

  @override
  String get teamNoAccess => 'Командаға қолжетімділік жоқ';

  @override
  String get teamMembers => 'Қатысушылар';

  @override
  String get teamNoMembers => 'Қызметкерлер жоқ';

  @override
  String get teamInvite => 'Шақыру';

  @override
  String get teamAudit => 'Аудит';

  @override
  String get teamNoAudit => 'Аудит жазбалары жоқ';

  @override
  String get teamExtendAllTitle => 'Барлық бастапқы файлдарды ұзарту';

  @override
  String get teamExtendAllBody =>
      'Компанияның барлық модельдері үшін бұлттық бастапқы файлдарды сақтауды 30 күнге ұзарту. Шектеу — модельге 3 ұзарту (§9.1.2).';

  @override
  String get teamExtend => 'Ұзарту';

  @override
  String get teamExtendAllBtn => 'Барлық бастапқы файлдарды ұзарту §9.1.2';

  @override
  String get teamMemberFallback => 'Қызметкер';

  @override
  String get teamRole => 'Рөл';

  @override
  String get teamActiveOrdersLimit => 'Белсенді тапсырыстар шегі';

  @override
  String get teamInviteSent => 'Шақыру жіберілді';

  @override
  String get teamInviteSentWithLink => 'Шақыру жіберілді · сілтеме көшірілді';

  @override
  String teamMemberSubtitle(String role, String limit) {
    return '$role · шегі $limit тапсырыс';
  }

  @override
  String teamCompany(String id) {
    return 'Компания #$id';
  }

  @override
  String get teamSendInvite => 'Шақыру жіберу';

  @override
  String get teamSearchHint => 'Аты немесе email';

  @override
  String get teamRoleAll => 'Барлық рөлдер';

  @override
  String get teamLoadMore => 'Тағы жүктеу';

  @override
  String get mvPublishValidating => 'Импортты тексеру';

  @override
  String get mvPublishImported => 'Импортталды';

  @override
  String get mvPublishImportFailed => 'Импорт қатесі';

  @override
  String get mvPublishNotPublished => 'Жарияланбаған';

  @override
  String get mvPublishVerified => 'Тексерілді';

  @override
  String get mvPublishPublished => 'Жарияланды';

  @override
  String get mvRenameTitle => 'Модельді қайта атау';

  @override
  String get mvNameLabel => 'Атауы';

  @override
  String get mvLinkCopied => 'Сілтеме көшірілді';

  @override
  String get mvMovedToTrash => 'Модель себетке жылжытылды';

  @override
  String get mvRetry => 'Қайталау';

  @override
  String get mvNoModels => 'Әзірге модельдер жоқ';

  @override
  String get mvTitle => 'Модельдер';

  @override
  String get mvTrash => 'Себет';

  @override
  String get mvFilterAll => 'Барлығы';

  @override
  String get mvFilterFavorites => 'Таңдаулылар';

  @override
  String get mvSortNewest => 'Алдымен жаңалары';

  @override
  String get mvSortOldest => 'Алдымен ескілері';

  @override
  String get mvNoModelsFilter => 'Бұл сүзгі бойынша модельдер жоқ';

  @override
  String get mvDownloadGlbOzon => '.glb жүктеу (Ozon)';

  @override
  String get mvDownloadUsdzWb => '.usdz жүктеу (Wildberries)';

  @override
  String get mvShare => 'Бөлісу';

  @override
  String get mvRate => 'Модельді бағалау';

  @override
  String get mvVerifyLink => 'Растау сілтемесі';

  @override
  String get mvEdit => 'Өңдеу';

  @override
  String get mvRename => 'Қайта атау';

  @override
  String get mvDelete => 'Жою';

  @override
  String mvLinkCopiedMarketplace(String mp) {
    return '$mp сілтемесі көшірілді';
  }

  @override
  String mvGlbSaved(String path) {
    return 'GLB сақталды: $path';
  }

  @override
  String get mvPublicLinkTitle => 'Жария сілтеме §3.12';

  @override
  String mvUntil(String date) {
    return 'Дейін: $date';
  }

  @override
  String get mvNoLocalPhotosTitle => 'Жергілікті фото жоқ';

  @override
  String get mvNoLocalPhotosBody =>
      'Қайта генерациялау үшін құрылғыда 12 бастапқы фото қажет. Бұлттан қалпына келтіру немесе қайта түсіру керек пе?';

  @override
  String get mvRestore => 'Қалпына келтіру';

  @override
  String get mvCantDetectCategory => 'Санат/тарифті анықтау мүмкін болмады';

  @override
  String get mvStorageExtended => 'Сақтау ұзартылды';

  @override
  String get mvDeleteTitle => 'Модельді жою керек пе?';

  @override
  String get mvDeleteBody =>
      'Бастапқы фото мен модель 30 күнге себетке жылжытылады. Жалғастырасыз ба?';

  @override
  String get mvInTrash => 'Себетте';

  @override
  String get mvSourcesRestored => 'Бастапқы файлдар қалпына келтірілді';

  @override
  String get mvCardLinkTitle => 'Карточка сілтемесі';

  @override
  String get mvCardLinkHint =>
      'https://www.wildberries.ru/... немесе ozon.ru/...';

  @override
  String get mvAdd => 'Қосу';

  @override
  String mvLinkStatus(String status) {
    return 'Сілтеме: $status';
  }

  @override
  String get mvRateTitle => 'Модель сапасын 1-ден 5-ке дейін бағалаңыз';

  @override
  String get mvWhatsWrong => 'Не дұрыс емес?';

  @override
  String get mvReasonBlurry => 'бұлыңғыр текстуралар';

  @override
  String get mvReasonHoles => 'тесіктер немесе артефактілер';

  @override
  String get mvReasonScale => 'қате масштаб';

  @override
  String get mvReasonColor => 'қате түс / жарық';

  @override
  String get mvReasonOther => 'басқа';

  @override
  String get mvComment => 'Пікір';

  @override
  String get mvLater => 'Кейінірек';

  @override
  String get mvModelTitle => '3D-модель';

  @override
  String get mvGlbNotReady => 'GLB әзірге дайын емес';

  @override
  String mvCloud(String days, String used, String max) {
    return 'Бұлт: $days күн · ұзартулар $used/$max';
  }

  @override
  String get mvLocalGlbSaved => 'Жергілікті GLB сақталды';

  @override
  String get mvRegenerate => 'Қайта генерациялау';

  @override
  String get mvUpdateGlb => 'GLB жаңарту';

  @override
  String get mvGlbLocal => 'GLB жергілікті';

  @override
  String get mvDownloadWb => 'WB жүктеу';

  @override
  String get mvDownloadOzon => 'Ozon жүктеу';

  @override
  String get mvSources => 'Бастапқы файлдар';

  @override
  String get mvExtend30 => '+30 күн';

  @override
  String get mvToTrash => 'Себетке';

  @override
  String get mvLink => 'Сілтеме';

  @override
  String get mvImOnWb => 'Мен WB-дамын';

  @override
  String get mvImOnOzon => 'Мен Ozon-дамын';

  @override
  String mvApiResult(String status) {
    return 'API: $status';
  }

  @override
  String get orderLimitTitle => 'Белсенді тапсырыс лимиті';

  @override
  String get orderLimitBody =>
      'Рөліңіз үшін бір уақыттағы тапсырыс лимитіне жеттіңіз. Ағымдағы генерациялар аяқталуын күтіңіз немесе Owner-ге хабарласыңыз.';

  @override
  String get orderLimitOk => 'Түсінікті';

  @override
  String get trashTitle => 'Себет';

  @override
  String get trashEmpty => 'Себет бос\nЖойылған модельдер 30 күн сақталады';

  @override
  String get trashRestore => 'Қалпына келтіру';

  @override
  String get trashRestored => 'Қалпына келтірілді';

  @override
  String trashOrderLine(String id, String date) {
    return 'Тапсырыс #$id · себетте $date';
  }

  @override
  String trashPurgeLine(String date) {
    return 'Жою: $date';
  }

  @override
  String get prefPushEnabled => 'Push-хабарландырулар';

  @override
  String get prefEmailEnabled => 'Email-хабарландырулар';

  @override
  String get prefGenerationDone => 'Генерация дайын';

  @override
  String get prefRefund => 'Қайтару';

  @override
  String get prefNsfwBlocked => 'NSFW-блок';

  @override
  String get prefSourceExpire => 'Дереккөз мерзімі';

  @override
  String get prefCleanup => 'Сақтау тазарту';

  @override
  String get prefPublishReminder => 'Жариялау еске салу';

  @override
  String get prefSupportReply => 'Қолдау жауабы';

  @override
  String get profileInnLabel => 'ЖСН (міндетті емес) §19.14.1';

  @override
  String get profilePhoneLabel => 'Телефон (міндетті емес) §19.14.1';

  @override
  String get profileFullNameLabel => 'Аты-жөні (міндетті емес) §19.14.1';

  @override
  String get profileExportFormat => 'Экспорт форматы §19.14.3';

  @override
  String get profileExportGlb => '.glb (Ozon / әмбебап)';

  @override
  String get profileExportUsdz => '.usdz (Wildberries / AR)';

  @override
  String get profileTheme => 'Тема §19.14.3';

  @override
  String get themeSystem => 'Жүйелік';

  @override
  String get themeLight => 'Ашық';

  @override
  String get themeDark => 'Қараңғы';

  @override
  String get profileLanguage => 'Тіл';

  @override
  String get profileNotificationsSection => 'Хабарландырулар §19.14.3';

  @override
  String get profileEventsSection => 'Оқиғалар §3.4.3';

  @override
  String get profileSecuritySection => 'Қауіпсіздік §19.14.4';

  @override
  String get profileChangePassword => 'Құпиясөзді өзгерту';

  @override
  String get profileChangePasswordTitle => 'Құпиясөзді өзгерту';

  @override
  String get profileCurrentPassword => 'Ағымдағы құпиясөз';

  @override
  String get profileNewPassword => 'Жаңа құпиясөз';

  @override
  String get profilePasswordConfirm => 'Растау';

  @override
  String get profilePasswordChanged => 'Құпиясөз өзгертілді';

  @override
  String get profileMinPassword => 'Кемінде 8 таңба';

  @override
  String get profilePasswordMismatch => 'Құпиясөздер сәйкес емес';

  @override
  String get profile2faSection => 'Екі факторлы аутентификация §19.14.4';

  @override
  String get profile2faEnabled => '2FA қосулы';

  @override
  String get profile2faDisabled => '2FA сөндірулі';

  @override
  String get profile2faOwnerRequired => 'Owner үшін 2FA міндетті (§10.7.5)';

  @override
  String get profile2faActiveHint =>
      'TOTP белсенді — Google Authenticator, 1Password және т.б.';

  @override
  String get profile2faStep1 => '1. Authenticator-да QR сканерлеңіз';

  @override
  String get profile2faStep2 => '2. Немесе құпиясөзді қолмен енгізіңіз';

  @override
  String get profileSecretCopied => 'Секрет көшірілді';

  @override
  String get profile2faCodeLabel => 'Authenticator коды';

  @override
  String get profileConfirm2fa => '2FA растау';

  @override
  String get profileEnable2fa => '2FA қосу';

  @override
  String get profile2faEnabledSnackbar => '2FA қосылды';

  @override
  String get profileDeleteAccountTitle => 'Аккаунтты жою?';

  @override
  String get profileDeleteAccountBody =>
      'Барлық модельдер мен жеке деректер 30 күн ішінде жойылады (§2.8.3). Қаржылық жазбалар анонимделіп 5 жыл сақталады.';

  @override
  String get profileDeleteAccountBtn => 'Жою';

  @override
  String get profileDeleteRequestAccepted => 'Сұрау қабылданды';

  @override
  String get notifGenDoneTitle => 'Генерация аяқталды';

  @override
  String notifGenDoneBody(String id) {
    return 'Тапсырыс #$id дайын';
  }

  @override
  String get notifNsfwTitle => 'NSFW-блок';

  @override
  String notifNsfwBody(String id) {
    return 'Тапсырыс #$id қабылданбады. Қаражат қайтарылды.';
  }

  @override
  String get notifGenFailedTitle => 'Генерация қатесі';

  @override
  String notifGenFailedBody(String id) {
    return 'Тапсырыс #$id орындалмады';
  }

  @override
  String get notifRefundTitle => 'Қайтару';

  @override
  String notifRefundBody(String id) {
    return 'Тапсырыс #$id бойынша қайтару';
  }

  @override
  String get notifCancelledTitle => 'Тапсырыс бас тартылды';

  @override
  String notifCancelledBody(String id) {
    return 'Тапсырыс #$id бас тартылды';
  }

  @override
  String get notifCompanyInviteTitle => 'Компанияға шақыру';

  @override
  String get publishGuideTitle => 'Жариялау нұсқаулығы';

  @override
  String get publishGuideIntro =>
      'Модель файлдарын жүктеп, маркетплейс карточкасына жүктеңіз.';

  @override
  String get publishGuideWbTitle => 'Wildberries';

  @override
  String get publishGuideWb1 => '1. .usdz жүктеңіз (модельдегі «WB жүктеу»).';

  @override
  String get publishGuideWb2 => '2. WB кабинетінде карточка → медиа → 3D.';

  @override
  String get publishGuideWb3 => '3. iOS сатып алушыларға .usdz жүктеңіз.';

  @override
  String get publishGuideOzonTitle => 'Ozon';

  @override
  String get publishGuideOzon1 => '1. .glb жүктеңіз (Ozon жүктеу).';

  @override
  String get publishGuideOzon2 => '2. Ozon кабинетінде карточка → 3D-модель.';

  @override
  String get publishGuideOzon3 => '3. Android сатып алушыларға .glb жүктеңіз.';

  @override
  String get publishGuideOpenModels => 'Модельдерге';

  @override
  String get apiKeysTitle => 'API-ключтер';

  @override
  String get apiKeysSubtitle => 'Owner · scopes · rate limit';

  @override
  String get apiKeysCreate => 'Ключ жасау';

  @override
  String get apiKeysRevoke => 'Күшін жою';

  @override
  String get apiKeysCopyOnce => 'Ключті көшіріңіз — қайта көрсетілмейді';

  @override
  String get apiKeysName => 'Атауы';

  @override
  String get apiKeysEmpty => 'Ключтер жоқ';

  @override
  String get apiKeysCreated => 'Ключ жасалды';

  @override
  String get profileCopySecretBtn => 'Құпиясөзді көшіру';

  @override
  String get profile2faCodeStep => '3. 6 таңбалы кодты енгізіңіз';

  @override
  String get profile2faSetupHint =>
      'Кіргенде бір реттік кодтармен аккаунтты қорғаңыз.';

  @override
  String get profileDeleteAccount => 'Аккаунтты жою';

  @override
  String get profileLogout => 'Шығу';

  @override
  String get catClothing => 'Киім';

  @override
  String get catShoes => 'Аяқ киім';

  @override
  String get catElectronics => 'Электроника';

  @override
  String get catFurniture => 'Жиһаз';

  @override
  String get catDecor => 'Декор / Инterior';

  @override
  String get catToys => 'Ойыншықтар';

  @override
  String get catAdult => '18+ тауарлар';

  @override
  String get catOther => 'Басқа';

  @override
  String get tierSmall => 'Кіші';

  @override
  String get tierLarge => 'Үлкен';

  @override
  String get forbIntimate => 'Интим';

  @override
  String get forbWeapons => 'Қару';

  @override
  String get forbDrugs => 'Есірткі';

  @override
  String get angle00 => 'Төмен 0° (алдыңғы)';

  @override
  String get angle01 => 'Төмен 45°';

  @override
  String get angle02 => 'Төмен 90° (сол)';

  @override
  String get angle03 => 'Төмен 135°';

  @override
  String get angle04 => 'Төмен 180° (артқы)';

  @override
  String get angle05 => 'Төмен 225°';

  @override
  String get angle06 => 'Төмен 270° (оң)';

  @override
  String get angle07 => 'Төмен 315°';

  @override
  String get angle08 => 'Жоғары алға 45°';

  @override
  String get angle09 => 'Жоғары оңға 45°';

  @override
  String get angle10 => 'Жоғары артқа 45°';

  @override
  String get angle11 => 'Жоғары солға 45°';

  @override
  String get wsSessionExpired => 'Сессия аяқталды. Қайта кіріңіз.';

  @override
  String get wsServerUnavailable =>
      'Сервер қолжетімсіз. API_URL және желіні тексеріңіз.';

  @override
  String get wsQueueFailed => 'Кезекке қосылу сәтсіз. Кейінірек қайталаңыз.';

  @override
  String get wsQueueError => 'Кезек қосылу қатесі';

  @override
  String get calSaved => 'Калибровка 30 күнге сақталды';

  @override
  String get calRefFractionError =>
      'Кадрдағы эталон бөлінісін көрсетіңіз (0.1–0.9)';

  @override
  String get calEnterDimensions => 'Өлшемдерді метрмен енгізіңіз';

  @override
  String calCurrentLine(String method, String date) {
    return 'Ағымдағы: $method · $date дейін';
  }

  @override
  String get calReset => 'Калибровканы қалпына келтіру';

  @override
  String get calIntro =>
      '«Масштаб 1:1» және жиһаз үшін калибровка қажет (§3.7).';

  @override
  String get calMethod => 'Әдіс';

  @override
  String get calMethodCard => 'Банк картасы (85.6×54 мм)';

  @override
  String get calMethodA4 => 'A4 парақ (210×297 мм)';

  @override
  String get calMethodQr => 'PDF QR (100 мм)';

  @override
  String get calMethodManual => 'Қолмен енгізу (м)';

  @override
  String get calRefWidth => 'Эталон ені (0.1–0.9)';

  @override
  String get calRefHeight => 'Эталон биіктігі (0.1–0.9)';

  @override
  String get calSave => 'Калибровканы сақтау';

  @override
  String get calQrIntro => 'QR PDF жүктеп, басып, тауар жanıна қойыңыз.';

  @override
  String get calDownloadPdf => 'QR PDF жүктеу';

  @override
  String get calQrSide => 'QR жағы (мм)';

  @override
  String get calQrWidth => 'QR кадрда — ені';

  @override
  String get calQrHeight => 'QR кадрда — биіктігі';

  @override
  String get calSaveQr => 'QR бойынша сақтау';

  @override
  String get calManualW => 'Тауар ені (м)';

  @override
  String get calManualH => 'Тауар биіктігі (м)';

  @override
  String get calManualD => 'Тауар тереңдігі (м)';

  @override
  String storUsedLine(String bytes, String models, String glbs) {
    return 'Бос емес: $bytes · папка: $models · GLB: $glbs';
  }

  @override
  String get storAutoDownload => 'GLB автожүктеу';

  @override
  String get storAutoDownloadDesc => '§3.3.2 — модельді құрылғыға сақтау';

  @override
  String get storAutoCleanup => 'GLB авто тазарту';

  @override
  String storAutoCleanupDesc(String days) {
    return 'Таңдаулы емес $days күннен ескілерін жою';
  }

  @override
  String get storCleanupDays => 'Авто тазарту мерзімі (күн)';

  @override
  String get storDays7 => '7 күн';

  @override
  String get storDays14 => '14 күн';

  @override
  String get storDays30 => '30 күн';

  @override
  String get storDays60 => '60 күн';

  @override
  String get storDays90 => '90 күн';

  @override
  String get storCleanupNow => 'Қазір тазарту';

  @override
  String get storExportZip => 'Барлық GLB ZIP-ке экспорт';

  @override
  String storZipCopied(String path) {
    return 'ZIP: $path (жол көшірілді)';
  }

  @override
  String storGlbDeleted(String count) {
    return 'Жергілікті GLB жойылды: $count';
  }

  @override
  String get impIntro =>
      'GLB жүктеңіз (50 МБ дейін). Тек компания Owner §6.10.';

  @override
  String get impFileTooBig => 'Файл 50 МБ-тан үлкен (§6.10)';

  @override
  String get impOwnerOnly => 'Импорт тек компания Owner үшін (§6.10)';

  @override
  String get impUploadParamsError => 'Сервер жүктеу параметрлерін қайтармады';

  @override
  String get impValidating => 'Модель тексеруде (GLB 2.0 / PBR / Draco)…';

  @override
  String get impDone => 'Модель импортталды';

  @override
  String get impName => 'Атауы';

  @override
  String get impCategory => 'Санат';

  @override
  String get impPickGlb => '.glb таңдау';

  @override
  String impSize(String size) {
    return 'Өлшем: $size';
  }

  @override
  String get impImporting => 'Импорт…';

  @override
  String get impBtn => 'Импорттау';

  @override
  String get impFree => 'Импорт тегін';

  @override
  String impPriceLine(String price) {
    return 'Импорт құны: $price ₽';
  }

  @override
  String get balStatusAuto => 'Күй автоматты жаңартылады';

  @override
  String get balTransactions => 'Транзакциялар';

  @override
  String balTotalLine(String total) {
    return 'Барлығы: $total';
  }

  @override
  String get balEmpty => 'Операциялар жоқ';

  @override
  String get balSuccess => 'Сәтті';

  @override
  String get balEmployee => 'Қызметкер §8';

  @override
  String get balAll => 'Барлығы';

  @override
  String get balThresholdInvalid => 'Дұрыс порог көрсетіңіз';

  @override
  String balDevMock(String balance) {
    return 'Баланс: $balance ₽';
  }

  @override
  String get consentUpdatedTitle => 'Шарттар жаңартылды';

  @override
  String get consentAcceptAllSnackbar =>
      'Барлық жаңартылған құжаттарды қабылдаңыз';

  @override
  String get consentIntro =>
      'Жалғастыру үшін жаңа құжат нұсқаларын қабылдаңыз (§2.8).';

  @override
  String get consentRead => 'Оқу';

  @override
  String get consentHide => 'Мәтінді жасыру';

  @override
  String get consentAccept => 'Қабылдаймын';

  @override
  String get consentContinue => 'Жалғастыру';

  @override
  String consentDocVersion(String title, String version) {
    return '$title · v$version';
  }

  @override
  String get consentSaving => 'Сақталуда…';

  @override
  String get shootLinkTitle => 'Сілтеме бойынша түсіру';

  @override
  String get shootLinkCorpMode => 'Кorporativ режимді таңдаңыз';

  @override
  String get shootLinkTier => 'Тариф';

  @override
  String get shootLinkCreate => 'Сілтеме және QR жасау';

  @override
  String get shootLinkCopied => 'Сілтеме көшірілді';

  @override
  String get shootLinkCopy => 'Көшіру';

  @override
  String get gdCameraRequired => 'Кamera рұқсаты қажет';

  @override
  String gdTurnToMarker(String azimuth, String elevation) {
    return 'AR белгісіне бұрыңыз $azimuth° / $elevation°';
  }

  @override
  String gdFpsWait(String fps) {
    return 'Күтіңіз ($fps FPS, энергия үнемдеу)';
  }

  @override
  String get gdAlignMarker => 'Кamerаны AR белгісімен сәйkestendirіңіз';

  @override
  String get ucDraftNotFound => 'Түсіру черновигі табылмады';

  @override
  String get ucForbiddenCategory =>
      'Тыйым салынған санат. Тапсырыс қайтарусыз қабылданбайды.';

  @override
  String ucNoViewFile(String index) {
    return 'Ракурс файлы жоқ $index';
  }

  @override
  String get gyroTiltDown => 'телефонды төмен бүгіңіз';

  @override
  String get gyroTiltUp => 'телефонды көтеріңіз';

  @override
  String gyroTurnPitch(String dir, String pitch) {
    return 'Телефонды бұрыңыз: $dir (~$pitch°)';
  }

  @override
  String gyroTurnDegrees(String deg, String dir) {
    return 'Телефонды шамамен $deg° $dir бұрыңыз';
  }

  @override
  String get gyroLeft => 'солға';

  @override
  String get gyroRight => 'оңға';

  @override
  String get qaBlur => 'бұлыңғыр';

  @override
  String get qaOffCenter => 'ортadan тыс';

  @override
  String get qaOverexposed => 'ашық экспозиция';

  @override
  String get qaOk => 'ok';

  @override
  String get qaCenterPhone => 'Тауар ортада болуы үшін телефонды жылжытыңыз';

  @override
  String get qaCloser => 'Тауар экранның ~70%-ын алуы үшін жақындатыңыз';

  @override
  String get qaFarther => 'Тауар экранның ~70%-ын алуы үшін алыстатыңыз';

  @override
  String get checkoutPromoApply => 'Қолдану';

  @override
  String checkoutPromoApplied(String amount) {
    return 'Жеңілдік −$amount ₽';
  }

  @override
  String get checkoutPromoInvalid => 'Промокод жарамсыз';

  @override
  String get campaignBannerDismiss => 'Жасыру';

  @override
  String get companyDefaultName => 'Компания';

  @override
  String get paymentStatusPending => 'Төлем күтілуде';

  @override
  String get paymentStatusSucceeded => 'Төленді';

  @override
  String get paymentStatusCanceled => 'Бас тартылды';

  @override
  String get draftRestoreTitle => 'Черновиктерді қалпына келтіру?';

  @override
  String draftRestoreBody(String count) {
    return '$count бұлттық бэкап табылды (TTL 7 күн). Аяқталмаған түсірулерді қалпына келтіру?';
  }

  @override
  String get draftRestoredSnackbar => 'Черновиктер бұлттан қалпына келтірілді';

  @override
  String get resumeDraftTitle => 'Аяқталмаған түсіру';

  @override
  String resumeDraftBody(String category, String count, String total) {
    return 'Черновик бар ($category, $count/$total кадр). Жалғастыру немесе қайта?';
  }

  @override
  String get resumeDraftDiscard => 'Қайта';

  @override
  String get resumeDraftContinue => 'Жалғастыру';

  @override
  String get mvSearchHint => 'Атау бойынша іздеу';

  @override
  String get mvFilterTierAll => 'Барлық тарифтер';

  @override
  String get mvFilterAuthorAll => 'Барлық авторлар';

  @override
  String get mvFilterAuthor => 'Автор';

  @override
  String get mvClearDates => 'Күндерді тазалау';

  @override
  String get balancePresetsLabel => 'Сақталған көріністер';

  @override
  String get balanceSavePreset => 'Сақтау…';

  @override
  String get balancePresetNameHint => 'Көрініс атауы';

  @override
  String get balancePresetSaved => 'Көрініс сақталды';

  @override
  String get balancePresetDeleted => 'Көрініс жойылды';

  @override
  String get balanceApplyPreset => 'Қолдану';

  @override
  String get profileSessionsSection => 'Белсенді сессиялар §19.14.4';

  @override
  String get profileSessionRevoke => 'Аяқтау';

  @override
  String get profileSessionsRevokeOthers => 'Басқа сессияларды аяқтау';

  @override
  String get profileSessionsRevokeOthersDone => 'Басқа сессиялар аяқталды';

  @override
  String get profileSessionsEmpty => 'Басқа белсенді сессиялар жоқ';

  @override
  String get profileDisable2fa => '2FA сөндіру';

  @override
  String get profileDisable2faTitle => '2FA сөндіру керек пе?';

  @override
  String get profileDisable2faBody =>
      'Растау үшін authenticator кодын енгізіңіз.';

  @override
  String get profile2faDisabledSnackbar => '2FA сөндірілді';

  @override
  String get mvApiUploadTitle => 'API арқылы жүктеу';

  @override
  String get mvApiSkuLabel => 'SKU';

  @override
  String get mvApiUploadBtn => 'API жүктеу';

  @override
  String get mvLoadMore => 'Тағы жүктеу';
}
