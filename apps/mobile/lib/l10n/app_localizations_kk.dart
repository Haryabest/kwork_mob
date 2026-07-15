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
}
