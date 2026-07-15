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
  String get guestSentToOwner => 'Фото иесіне жіберildi';

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
}
