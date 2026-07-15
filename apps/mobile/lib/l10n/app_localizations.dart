import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_kk.dart';
import 'app_localizations_ru.dart';
import 'app_localizations_zh.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'l10n/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations? of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations);
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('ru'),
    Locale('en'),
    Locale('kk'),
    Locale('zh'),
  ];

  /// No description provided for @appName.
  ///
  /// In ru, this message translates to:
  /// **'KWork Mob'**
  String get appName;

  /// No description provided for @authTitle.
  ///
  /// In ru, this message translates to:
  /// **'Вход'**
  String get authTitle;

  /// No description provided for @email.
  ///
  /// In ru, this message translates to:
  /// **'Email'**
  String get email;

  /// No description provided for @password.
  ///
  /// In ru, this message translates to:
  /// **'Пароль'**
  String get password;

  /// No description provided for @login.
  ///
  /// In ru, this message translates to:
  /// **'Войти'**
  String get login;

  /// No description provided for @register.
  ///
  /// In ru, this message translates to:
  /// **'Регистрация'**
  String get register;

  /// No description provided for @forgotPassword.
  ///
  /// In ru, this message translates to:
  /// **'Забыли пароль?'**
  String get forgotPassword;

  /// No description provided for @home.
  ///
  /// In ru, this message translates to:
  /// **'Главная'**
  String get home;

  /// No description provided for @models.
  ///
  /// In ru, this message translates to:
  /// **'Модели'**
  String get models;

  /// No description provided for @orders.
  ///
  /// In ru, this message translates to:
  /// **'Заказы'**
  String get orders;

  /// No description provided for @support.
  ///
  /// In ru, this message translates to:
  /// **'Поддержка'**
  String get support;

  /// No description provided for @profile.
  ///
  /// In ru, this message translates to:
  /// **'Профиль'**
  String get profile;

  /// No description provided for @shoot.
  ///
  /// In ru, this message translates to:
  /// **'Снять товар'**
  String get shoot;

  /// No description provided for @queue.
  ///
  /// In ru, this message translates to:
  /// **'Очередь'**
  String get queue;

  /// No description provided for @faq.
  ///
  /// In ru, this message translates to:
  /// **'FAQ'**
  String get faq;

  /// No description provided for @personalMode.
  ///
  /// In ru, this message translates to:
  /// **'Личный'**
  String get personalMode;

  /// No description provided for @corporateMode.
  ///
  /// In ru, this message translates to:
  /// **'Компания'**
  String get corporateMode;

  /// No description provided for @onboarding1.
  ///
  /// In ru, this message translates to:
  /// **'Снимите товар с 12 ракурсов'**
  String get onboarding1;

  /// No description provided for @onboarding2.
  ///
  /// In ru, this message translates to:
  /// **'Оплатите тариф и дождитесь генерации'**
  String get onboarding2;

  /// No description provided for @onboarding3.
  ///
  /// In ru, this message translates to:
  /// **'Скачайте .glb / .usdz для маркетплейса'**
  String get onboarding3;

  /// No description provided for @onboarding4.
  ///
  /// In ru, this message translates to:
  /// **'Опубликуйте модель на WB или Ozon'**
  String get onboarding4;

  /// No description provided for @onboardingSub1.
  ///
  /// In ru, this message translates to:
  /// **'12 ракурсов Guided Dome → 3D-модель для маркетплейса'**
  String get onboardingSub1;

  /// No description provided for @onboardingSub2.
  ///
  /// In ru, this message translates to:
  /// **'ARKit / ARCore или гироскоп подскажут угол ±15°. Для масштаба 1:1 — калибровка по карте или A4 в профиле.'**
  String get onboardingSub2;

  /// No description provided for @onboardingSub3.
  ///
  /// In ru, this message translates to:
  /// **'Скачайте GLB/USDZ и опубликуйте на Wildberries или Ozon'**
  String get onboardingSub3;

  /// No description provided for @onboardingSub4.
  ///
  /// In ru, this message translates to:
  /// **'При нагреве >40°C съёмка перейдёт в энергосбережение (FPS 15)'**
  String get onboardingSub4;

  /// No description provided for @skip.
  ///
  /// In ru, this message translates to:
  /// **'Пропустить'**
  String get skip;

  /// No description provided for @alreadyHaveAccount.
  ///
  /// In ru, this message translates to:
  /// **'Уже есть аккаунт? Войти'**
  String get alreadyHaveAccount;

  /// No description provided for @continueBtn.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить'**
  String get continueBtn;

  /// No description provided for @errorNetwork.
  ///
  /// In ru, this message translates to:
  /// **'Нет интернета'**
  String get errorNetwork;

  /// No description provided for @comingSoon.
  ///
  /// In ru, this message translates to:
  /// **'Экран в разработке'**
  String get comingSoon;

  /// No description provided for @save.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить'**
  String get save;

  /// No description provided for @cancel.
  ///
  /// In ru, this message translates to:
  /// **'Отмена'**
  String get cancel;

  /// No description provided for @confirm.
  ///
  /// In ru, this message translates to:
  /// **'Подтвердить'**
  String get confirm;

  /// No description provided for @done.
  ///
  /// In ru, this message translates to:
  /// **'Готово'**
  String get done;

  /// No description provided for @account.
  ///
  /// In ru, this message translates to:
  /// **'Аккаунт'**
  String get account;

  /// No description provided for @langRu.
  ///
  /// In ru, this message translates to:
  /// **'Русский'**
  String get langRu;

  /// No description provided for @langEn.
  ///
  /// In ru, this message translates to:
  /// **'English'**
  String get langEn;

  /// No description provided for @langKk.
  ///
  /// In ru, this message translates to:
  /// **'Қазақша'**
  String get langKk;

  /// No description provided for @langZh.
  ///
  /// In ru, this message translates to:
  /// **'中文'**
  String get langZh;

  /// No description provided for @companyTopupTitle.
  ///
  /// In ru, this message translates to:
  /// **'Баланс компании'**
  String get companyTopupTitle;

  /// No description provided for @companyTopupSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Пополнение счёта · §19.14.2'**
  String get companyTopupSubtitle;

  /// No description provided for @companyPoliciesTitle.
  ///
  /// In ru, this message translates to:
  /// **'Политики компании'**
  String get companyPoliciesTitle;

  /// No description provided for @companyPoliciesSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Доступ и уведомления · §19.14.2'**
  String get companyPoliciesSubtitle;

  /// No description provided for @companyBalanceLabel.
  ///
  /// In ru, this message translates to:
  /// **'Баланс компании: {balance} ₽'**
  String companyBalanceLabel(String balance);

  /// No description provided for @policiesMaxConcurrent.
  ///
  /// In ru, this message translates to:
  /// **'Лимит одновременных заказов (по умолчанию)'**
  String get policiesMaxConcurrent;

  /// No description provided for @policiesNoMonthlyLimit.
  ///
  /// In ru, this message translates to:
  /// **'Без месячного лимита расходов'**
  String get policiesNoMonthlyLimit;

  /// No description provided for @policiesMonthlyLimit.
  ///
  /// In ru, this message translates to:
  /// **'Месячный лимит расходов (₽)'**
  String get policiesMonthlyLimit;

  /// No description provided for @policiesAllowedCategories.
  ///
  /// In ru, this message translates to:
  /// **'Разрешённые категории'**
  String get policiesAllowedCategories;

  /// No description provided for @policiesAllowDownload.
  ///
  /// In ru, this message translates to:
  /// **'Photographer может скачивать модели'**
  String get policiesAllowDownload;

  /// No description provided for @policiesAllowLinks.
  ///
  /// In ru, this message translates to:
  /// **'Photographer может добавлять ссылки публикации'**
  String get policiesAllowLinks;

  /// No description provided for @policiesRequire2fa.
  ///
  /// In ru, this message translates to:
  /// **'Требовать 2FA для всех сотрудников'**
  String get policiesRequire2fa;

  /// No description provided for @policiesAutoBlock.
  ///
  /// In ru, this message translates to:
  /// **'Авто-блокировка при неактивности (дней)'**
  String get policiesAutoBlock;

  /// No description provided for @policiesLowBalanceThreshold.
  ///
  /// In ru, this message translates to:
  /// **'Порог низкого баланса (₽)'**
  String get policiesLowBalanceThreshold;

  /// No description provided for @policiesNotifySection.
  ///
  /// In ru, this message translates to:
  /// **'Уведомления Owner (§3.19)'**
  String get policiesNotifySection;

  /// No description provided for @policiesNotifyHint.
  ///
  /// In ru, this message translates to:
  /// **'Кому слать push/email по событиям компании'**
  String get policiesNotifyHint;

  /// No description provided for @policiesSaved.
  ///
  /// In ru, this message translates to:
  /// **'Политики сохранены'**
  String get policiesSaved;

  /// No description provided for @policiesInvalidConcurrent.
  ///
  /// In ru, this message translates to:
  /// **'Укажите лимит заказов от 1 до 20'**
  String get policiesInvalidConcurrent;

  /// No description provided for @policiesInvalidAutoBlock.
  ///
  /// In ru, this message translates to:
  /// **'Укажите корректный срок авто-блокировки'**
  String get policiesInvalidAutoBlock;

  /// No description provided for @policiesInvalidThreshold.
  ///
  /// In ru, this message translates to:
  /// **'Укажите корректный порог баланса'**
  String get policiesInvalidThreshold;

  /// No description provided for @policiesInvalidMonthly.
  ///
  /// In ru, this message translates to:
  /// **'Укажите корректный месячный лимит'**
  String get policiesInvalidMonthly;

  /// No description provided for @notifyGenerationDone.
  ///
  /// In ru, this message translates to:
  /// **'Генерация завершена'**
  String get notifyGenerationDone;

  /// No description provided for @notifyPhotographerUploaded.
  ///
  /// In ru, this message translates to:
  /// **'Фотограф загрузил фото'**
  String get notifyPhotographerUploaded;

  /// No description provided for @notifySourceExpire.
  ///
  /// In ru, this message translates to:
  /// **'Истекает облачная копия'**
  String get notifySourceExpire;

  /// No description provided for @notifyLowBalance.
  ///
  /// In ru, this message translates to:
  /// **'Низкий баланс компании'**
  String get notifyLowBalance;

  /// No description provided for @audienceOwnerOnly.
  ///
  /// In ru, this message translates to:
  /// **'Только Owner'**
  String get audienceOwnerOnly;

  /// No description provided for @audienceOwnerManager.
  ///
  /// In ru, this message translates to:
  /// **'Owner + Manager'**
  String get audienceOwnerManager;

  /// No description provided for @audienceAll.
  ///
  /// In ru, this message translates to:
  /// **'Всем сотрудникам'**
  String get audienceAll;

  /// No description provided for @balanceTitle.
  ///
  /// In ru, this message translates to:
  /// **'Баланс'**
  String get balanceTitle;

  /// No description provided for @balanceCompanyTitle.
  ///
  /// In ru, this message translates to:
  /// **'Баланс компании'**
  String get balanceCompanyTitle;

  /// No description provided for @balanceUnavailable.
  ///
  /// In ru, this message translates to:
  /// **'Баланс недоступен для вашей роли'**
  String get balanceUnavailable;

  /// No description provided for @lowBalanceBanner.
  ///
  /// In ru, this message translates to:
  /// **'Низкий баланс компании: {balance} ₽ (порог {threshold} ₽). Пополните счёт §20.3.5'**
  String lowBalanceBanner(String balance, String threshold);

  /// No description provided for @topup.
  ///
  /// In ru, this message translates to:
  /// **'Пополнить'**
  String get topup;

  /// No description provided for @topupMinAmount.
  ///
  /// In ru, this message translates to:
  /// **'Минимум 100 ₽'**
  String get topupMinAmount;

  /// No description provided for @balanceTopupSuccess.
  ///
  /// In ru, this message translates to:
  /// **'Баланс пополнен'**
  String get balanceTopupSuccess;

  /// No description provided for @companyTopupSuccess.
  ///
  /// In ru, this message translates to:
  /// **'Баланс компании пополнен'**
  String get companyTopupSuccess;

  /// No description provided for @paymentCanceled.
  ///
  /// In ru, this message translates to:
  /// **'Платёж отменён'**
  String get paymentCanceled;

  /// No description provided for @lowBalanceThreshold.
  ///
  /// In ru, this message translates to:
  /// **'Порог низкого баланса, ₽ §20.3.5'**
  String get lowBalanceThreshold;

  /// No description provided for @saveThreshold.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить порог'**
  String get saveThreshold;

  /// No description provided for @thresholdSaved.
  ///
  /// In ru, this message translates to:
  /// **'Порог низкого баланса сохранён §20.3.5'**
  String get thresholdSaved;

  /// No description provided for @topupCompanyBtn.
  ///
  /// In ru, this message translates to:
  /// **'Пополнить баланс компании §19.14.2'**
  String get topupCompanyBtn;

  /// No description provided for @topupAmount.
  ///
  /// In ru, this message translates to:
  /// **'Сумма пополнения'**
  String get topupAmount;

  /// No description provided for @topupCompanyAmount.
  ///
  /// In ru, this message translates to:
  /// **'Пополнение компании §19.14.2'**
  String get topupCompanyAmount;

  /// No description provided for @topupCard.
  ///
  /// In ru, this message translates to:
  /// **'Пополнить картой'**
  String get topupCard;

  /// No description provided for @topupSbpQr.
  ///
  /// In ru, this message translates to:
  /// **'СБП QR'**
  String get topupSbpQr;

  /// No description provided for @sbpQrTitle.
  ///
  /// In ru, this message translates to:
  /// **'СБП — отсканируйте QR'**
  String get sbpQrTitle;

  /// No description provided for @sbpAutoStatus.
  ///
  /// In ru, this message translates to:
  /// **'Статус обновится автоматически'**
  String get sbpAutoStatus;

  /// No description provided for @copyPayload.
  ///
  /// In ru, this message translates to:
  /// **'Скопировать payload'**
  String get copyPayload;

  /// No description provided for @dateFrom.
  ///
  /// In ru, this message translates to:
  /// **'Дата от'**
  String get dateFrom;

  /// No description provided for @dateTo.
  ///
  /// In ru, this message translates to:
  /// **'Дата до'**
  String get dateTo;

  /// No description provided for @txTypeLabel.
  ///
  /// In ru, this message translates to:
  /// **'Тип операции'**
  String get txTypeLabel;

  /// No description provided for @txTypeAll.
  ///
  /// In ru, this message translates to:
  /// **'Все'**
  String get txTypeAll;

  /// No description provided for @txTypeTopup.
  ///
  /// In ru, this message translates to:
  /// **'Пополнения'**
  String get txTypeTopup;

  /// No description provided for @txTypeCharge.
  ///
  /// In ru, this message translates to:
  /// **'Списания'**
  String get txTypeCharge;

  /// No description provided for @txTypeRefund.
  ///
  /// In ru, this message translates to:
  /// **'Возвраты'**
  String get txTypeRefund;

  /// No description provided for @perPage.
  ///
  /// In ru, this message translates to:
  /// **'На странице §20.3.4'**
  String get perPage;

  /// No description provided for @applyFilters.
  ///
  /// In ru, this message translates to:
  /// **'Применить фильтры'**
  String get applyFilters;

  /// No description provided for @exportCsv.
  ///
  /// In ru, this message translates to:
  /// **'Экспорт CSV §20.3.4'**
  String get exportCsv;

  /// No description provided for @exporting.
  ///
  /// In ru, this message translates to:
  /// **'Экспорт…'**
  String get exporting;

  /// No description provided for @companyTopupScreenTitle.
  ///
  /// In ru, this message translates to:
  /// **'Пополнение компании'**
  String get companyTopupScreenTitle;

  /// No description provided for @companyTopupScreenHint.
  ///
  /// In ru, this message translates to:
  /// **'Owner: пополнение корпоративного счёта через ЮKassa §19.14.2'**
  String get companyTopupScreenHint;

  /// No description provided for @languageInterface.
  ///
  /// In ru, this message translates to:
  /// **'Язык интерфейса'**
  String get languageInterface;

  /// No description provided for @team.
  ///
  /// In ru, this message translates to:
  /// **'Команда'**
  String get team;

  /// No description provided for @switchMode.
  ///
  /// In ru, this message translates to:
  /// **'Режим Личный / Компания'**
  String get switchMode;

  /// No description provided for @localStorage.
  ///
  /// In ru, this message translates to:
  /// **'Локальное хранилище'**
  String get localStorage;

  /// No description provided for @localStorageSub.
  ///
  /// In ru, this message translates to:
  /// **'GLB, автоочистка, экспорт ZIP'**
  String get localStorageSub;

  /// No description provided for @calibration.
  ///
  /// In ru, this message translates to:
  /// **'Калибровка масштаба'**
  String get calibration;

  /// No description provided for @calibrationSub.
  ///
  /// In ru, this message translates to:
  /// **'Карта / A4 / QR · §3.7'**
  String get calibrationSub;

  /// No description provided for @importModel.
  ///
  /// In ru, this message translates to:
  /// **'Импорт модели'**
  String get importModel;

  /// No description provided for @importModelSub.
  ///
  /// In ru, this message translates to:
  /// **'Готовый GLB · §6.10'**
  String get importModelSub;

  /// No description provided for @saveProfile.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить профиль'**
  String get saveProfile;

  /// No description provided for @profileSaved.
  ///
  /// In ru, this message translates to:
  /// **'Профиль сохранён'**
  String get profileSaved;

  /// No description provided for @balanceLabel.
  ///
  /// In ru, this message translates to:
  /// **'Баланс: {amount} ₽'**
  String balanceLabel(String amount);

  /// No description provided for @exportShareText.
  ///
  /// In ru, this message translates to:
  /// **'Транзакции §20.3.4'**
  String get exportShareText;

  /// No description provided for @exportSuccess.
  ///
  /// In ru, this message translates to:
  /// **'CSV экспортирован'**
  String get exportSuccess;

  /// No description provided for @open.
  ///
  /// In ru, this message translates to:
  /// **'Открыть'**
  String get open;

  /// No description provided for @notificationDefault.
  ///
  /// In ru, this message translates to:
  /// **'Уведомление'**
  String get notificationDefault;

  /// No description provided for @authCreateAccount.
  ///
  /// In ru, this message translates to:
  /// **'Создайте аккаунт'**
  String get authCreateAccount;

  /// No description provided for @authVerifyEmail.
  ///
  /// In ru, this message translates to:
  /// **'Подтверждение email'**
  String get authVerifyEmail;

  /// No description provided for @authAccountType.
  ///
  /// In ru, this message translates to:
  /// **'Тип аккаунта'**
  String get authAccountType;

  /// No description provided for @authForgotPasswordTitle.
  ///
  /// In ru, this message translates to:
  /// **'Восстановление пароля'**
  String get authForgotPasswordTitle;

  /// No description provided for @authNewPasswordTitle.
  ///
  /// In ru, this message translates to:
  /// **'Новый пароль'**
  String get authNewPasswordTitle;

  /// No description provided for @authTwoFaTitle.
  ///
  /// In ru, this message translates to:
  /// **'Введите код 2FA'**
  String get authTwoFaTitle;

  /// No description provided for @authSendLink.
  ///
  /// In ru, this message translates to:
  /// **'Отправить ссылку'**
  String get authSendLink;

  /// No description provided for @authSavePassword.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить пароль'**
  String get authSavePassword;

  /// No description provided for @authRememberMe.
  ///
  /// In ru, this message translates to:
  /// **'Запомнить меня'**
  String get authRememberMe;

  /// No description provided for @authPasswordConfirm.
  ///
  /// In ru, this message translates to:
  /// **'Подтверждение пароля'**
  String get authPasswordConfirm;

  /// No description provided for @authConsents.
  ///
  /// In ru, this message translates to:
  /// **'Принимаю соглашение, политику ПДн, оферту, подтверждение прав и правила запрещённого контента'**
  String get authConsents;

  /// No description provided for @authEmailCode.
  ///
  /// In ru, this message translates to:
  /// **'Код из письма (6 цифр)'**
  String get authEmailCode;

  /// No description provided for @authIndividual.
  ///
  /// In ru, this message translates to:
  /// **'Физ. лицо'**
  String get authIndividual;

  /// No description provided for @authLegal.
  ///
  /// In ru, this message translates to:
  /// **'Юр. лицо / ИП'**
  String get authLegal;

  /// No description provided for @authFullNameOptional.
  ///
  /// In ru, this message translates to:
  /// **'ФИО (необязательно)'**
  String get authFullNameOptional;

  /// No description provided for @authOrgName.
  ///
  /// In ru, this message translates to:
  /// **'Наименование организации'**
  String get authOrgName;

  /// No description provided for @authInn.
  ///
  /// In ru, this message translates to:
  /// **'ИНН'**
  String get authInn;

  /// No description provided for @authOgrn.
  ///
  /// In ru, this message translates to:
  /// **'ОГРН / ОГРНИП'**
  String get authOgrn;

  /// No description provided for @authLegalAddress.
  ///
  /// In ru, this message translates to:
  /// **'Юридический адрес'**
  String get authLegalAddress;

  /// No description provided for @authDirectorName.
  ///
  /// In ru, this message translates to:
  /// **'ФИО руководителя'**
  String get authDirectorName;

  /// No description provided for @authBankName.
  ///
  /// In ru, this message translates to:
  /// **'Банк'**
  String get authBankName;

  /// No description provided for @authBik.
  ///
  /// In ru, this message translates to:
  /// **'БИК'**
  String get authBik;

  /// No description provided for @authCheckingAccount.
  ///
  /// In ru, this message translates to:
  /// **'Расчётный счёт'**
  String get authCheckingAccount;

  /// No description provided for @authResetToken.
  ///
  /// In ru, this message translates to:
  /// **'Токен из письма'**
  String get authResetToken;

  /// No description provided for @authNewPasswordField.
  ///
  /// In ru, this message translates to:
  /// **'Новый пароль'**
  String get authNewPasswordField;

  /// No description provided for @authAuthenticatorCode.
  ///
  /// In ru, this message translates to:
  /// **'Код из Authenticator'**
  String get authAuthenticatorCode;

  /// No description provided for @authBack.
  ///
  /// In ru, this message translates to:
  /// **'Назад'**
  String get authBack;

  /// No description provided for @authBackToLogin.
  ///
  /// In ru, this message translates to:
  /// **'Назад ко входу'**
  String get authBackToLogin;

  /// No description provided for @authAcceptTerms.
  ///
  /// In ru, this message translates to:
  /// **'Примите условия сервиса'**
  String get authAcceptTerms;

  /// No description provided for @authPasswordUpdated.
  ///
  /// In ru, this message translates to:
  /// **'Пароль обновлён. Войдите с новым паролем'**
  String get authPasswordUpdated;

  /// No description provided for @authDevCode.
  ///
  /// In ru, this message translates to:
  /// **'Dev-код: {code}'**
  String authDevCode(String code);

  /// No description provided for @authDevToken.
  ///
  /// In ru, this message translates to:
  /// **'Dev-токен: {token}'**
  String authDevToken(String token);

  /// No description provided for @shootCategoryTitle.
  ///
  /// In ru, this message translates to:
  /// **'Категория товара'**
  String get shootCategoryTitle;

  /// No description provided for @shootCategoryLabel.
  ///
  /// In ru, this message translates to:
  /// **'Категория'**
  String get shootCategoryLabel;

  /// No description provided for @shootForbiddenCategories.
  ///
  /// In ru, this message translates to:
  /// **'Запрещённые категории'**
  String get shootForbiddenCategories;

  /// No description provided for @shootForbiddenHint.
  ///
  /// In ru, this message translates to:
  /// **'Если отметите — заказ не создаётся, средства не списываются'**
  String get shootForbiddenHint;

  /// No description provided for @shootAgeConfirmed.
  ///
  /// In ru, this message translates to:
  /// **'Возраст подтверждён'**
  String get shootAgeConfirmed;

  /// No description provided for @shootAgeConfirmedSub.
  ///
  /// In ru, this message translates to:
  /// **'Повторный ввод даты не требуется'**
  String get shootAgeConfirmedSub;

  /// No description provided for @shootBirthDate.
  ///
  /// In ru, this message translates to:
  /// **'Дата рождения (YYYY-MM-DD)'**
  String get shootBirthDate;

  /// No description provided for @shootBirthDateHint.
  ///
  /// In ru, this message translates to:
  /// **'Сохраняется в профиле после успешной проверки'**
  String get shootBirthDateHint;

  /// No description provided for @shootScaleRequired.
  ///
  /// In ru, this message translates to:
  /// **'Масштаб (м) — обязательно для мебели'**
  String get shootScaleRequired;

  /// No description provided for @shootCalibrationBtn.
  ///
  /// In ru, this message translates to:
  /// **'Калибровка: карта / A4 / QR (§3.7)'**
  String get shootCalibrationBtn;

  /// No description provided for @shootLength.
  ///
  /// In ru, this message translates to:
  /// **'Длина'**
  String get shootLength;

  /// No description provided for @shootWidth.
  ///
  /// In ru, this message translates to:
  /// **'Ширина'**
  String get shootWidth;

  /// No description provided for @shootHeight.
  ///
  /// In ru, this message translates to:
  /// **'Высота'**
  String get shootHeight;

  /// No description provided for @shootModelName.
  ///
  /// In ru, this message translates to:
  /// **'Название модели (необязательно)'**
  String get shootModelName;

  /// No description provided for @shootModelNameHint.
  ///
  /// In ru, this message translates to:
  /// **'Например: Кроссовки Nike Air'**
  String get shootModelNameHint;

  /// No description provided for @shootTier.
  ///
  /// In ru, this message translates to:
  /// **'Тариф'**
  String get shootTier;

  /// No description provided for @shootGhostMeshHint.
  ///
  /// In ru, this message translates to:
  /// **'Ghost Mesh — масштаб двумя пальцами'**
  String get shootGhostMeshHint;

  /// No description provided for @shootNext.
  ///
  /// In ru, this message translates to:
  /// **'Далее к съёмке'**
  String get shootNext;

  /// No description provided for @shootAgeConfirmTitle.
  ///
  /// In ru, this message translates to:
  /// **'Подтвердите, что вам 18 лет'**
  String get shootAgeConfirmTitle;

  /// No description provided for @shootAgeConfirmBody.
  ///
  /// In ru, this message translates to:
  /// **'Введите дату рождения (YYYY-MM-DD).'**
  String get shootAgeConfirmBody;

  /// No description provided for @shootInvalidDate.
  ///
  /// In ru, this message translates to:
  /// **'Некорректная дата (YYYY-MM-DD)'**
  String get shootInvalidDate;

  /// No description provided for @shootAgeOnly18.
  ///
  /// In ru, this message translates to:
  /// **'Создание модели доступно только с 18 лет'**
  String get shootAgeOnly18;

  /// No description provided for @shootBirthRequired.
  ///
  /// In ru, this message translates to:
  /// **'Укажите дату рождения для 18+'**
  String get shootBirthRequired;

  /// No description provided for @shootForbiddenTitle.
  ///
  /// In ru, this message translates to:
  /// **'Запрещённая категория'**
  String get shootForbiddenTitle;

  /// No description provided for @shootForbiddenBody.
  ///
  /// In ru, this message translates to:
  /// **'Вы выбрали запрещённую категорию. Заказ будет отклонён без возврата средств. Продолжить?'**
  String get shootForbiddenBody;

  /// No description provided for @shootOrderBlocked.
  ///
  /// In ru, this message translates to:
  /// **'Заказ не будет создан — смените категорию'**
  String get shootOrderBlocked;

  /// No description provided for @shootStorageFree.
  ///
  /// In ru, this message translates to:
  /// **'Освободите место на телефоне (нужно {need} МБ, доступно ~{free} МБ)'**
  String shootStorageFree(String need, String free);

  /// No description provided for @shootStorageFreeUnknown.
  ///
  /// In ru, this message translates to:
  /// **'Освободите место на телефоне (нужно {need} МБ)'**
  String shootStorageFreeUnknown(String need);

  /// No description provided for @shootQualityTitle.
  ///
  /// In ru, this message translates to:
  /// **'Проверка качества'**
  String get shootQualityTitle;

  /// No description provided for @shootQualityLow.
  ///
  /// In ru, this message translates to:
  /// **'Низкое качество фото. Постарайтесь улучшить условия съемки'**
  String get shootQualityLow;

  /// No description provided for @shootQualityLowTitle.
  ///
  /// In ru, this message translates to:
  /// **'Низкое качество'**
  String get shootQualityLowTitle;

  /// No description provided for @shootQualityLowDialog.
  ///
  /// In ru, this message translates to:
  /// **'Некоторые кадры имеют низкое качество, это может привести к браку модели. Продолжить?'**
  String get shootQualityLowDialog;

  /// No description provided for @yes.
  ///
  /// In ru, this message translates to:
  /// **'Да'**
  String get yes;

  /// No description provided for @no.
  ///
  /// In ru, this message translates to:
  /// **'Нет'**
  String get no;

  /// No description provided for @shootQualityContinue.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить к загрузке'**
  String get shootQualityContinue;

  /// No description provided for @shootQualityContinueForce.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить, несмотря на ошибки'**
  String get shootQualityContinueForce;

  /// No description provided for @shootQualityRestart.
  ///
  /// In ru, this message translates to:
  /// **'Начать съёмку с начала'**
  String get shootQualityRestart;

  /// No description provided for @shootArHint.
  ///
  /// In ru, this message translates to:
  /// **'AR: тариф «{tier}», габариты {scale}'**
  String shootArHint(String tier, String scale);

  /// No description provided for @shootTitle.
  ///
  /// In ru, this message translates to:
  /// **'Съёмка'**
  String get shootTitle;

  /// No description provided for @shootOverheatTitle.
  ///
  /// In ru, this message translates to:
  /// **'Перегрев телефона'**
  String get shootOverheatTitle;

  /// No description provided for @shootOverheatBody.
  ///
  /// In ru, this message translates to:
  /// **'Температура батареи ≈ {temp}°C (>45°C). Рекомендуем прервать съёмку до охлаждения. При продолжении включится энергосбережение (FPS 15).'**
  String shootOverheatBody(String temp);

  /// No description provided for @shootAbort.
  ///
  /// In ru, this message translates to:
  /// **'Прервать'**
  String get shootAbort;

  /// No description provided for @shootExit.
  ///
  /// In ru, this message translates to:
  /// **'Выход'**
  String get shootExit;

  /// No description provided for @shootCalibrateShort.
  ///
  /// In ru, this message translates to:
  /// **'Калибр.'**
  String get shootCalibrateShort;

  /// No description provided for @shootArCameraActive.
  ///
  /// In ru, this message translates to:
  /// **'AR-камера активна'**
  String get shootArCameraActive;

  /// No description provided for @shootAngleLine.
  ///
  /// In ru, this message translates to:
  /// **'Ракурс {current}/{total} · {label} · {backend}'**
  String shootAngleLine(
    String current,
    String total,
    String label,
    String backend,
  );

  /// No description provided for @uploadPhotoTitle.
  ///
  /// In ru, this message translates to:
  /// **'Загрузка фото'**
  String get uploadPhotoTitle;

  /// No description provided for @uploadPreparing.
  ///
  /// In ru, this message translates to:
  /// **'Подготовка…'**
  String get uploadPreparing;

  /// No description provided for @uploadResumeFound.
  ///
  /// In ru, this message translates to:
  /// **'Найдена незавершённая загрузка ({done}/12)'**
  String uploadResumeFound(String done);

  /// No description provided for @uploadResumeHint.
  ///
  /// In ru, this message translates to:
  /// **'§3.4.1: прогресс сохранён локально. При обрыве связи загрузка продолжится с последнего фото.'**
  String get uploadResumeHint;

  /// No description provided for @uploadBuildingZip.
  ///
  /// In ru, this message translates to:
  /// **'Сборка ZIP + SHA-256…'**
  String get uploadBuildingZip;

  /// No description provided for @uploadSha256.
  ///
  /// In ru, this message translates to:
  /// **'SHA-256: {hash}…'**
  String uploadSha256(String hash);

  /// No description provided for @uploadPresigned.
  ///
  /// In ru, this message translates to:
  /// **'Получение presigned URL…'**
  String get uploadPresigned;

  /// No description provided for @uploadEncrypting.
  ///
  /// In ru, this message translates to:
  /// **'E2E шифрование фото…'**
  String get uploadEncrypting;

  /// No description provided for @uploadProgress.
  ///
  /// In ru, this message translates to:
  /// **'Загрузка {current}/{total}…'**
  String uploadProgress(String current, String total);

  /// No description provided for @uploadUploaded.
  ///
  /// In ru, this message translates to:
  /// **'Загружено {done}/12'**
  String uploadUploaded(String done);

  /// No description provided for @uploadInterrupted.
  ///
  /// In ru, this message translates to:
  /// **'Загрузка прервана — можно продолжить'**
  String get uploadInterrupted;

  /// No description provided for @uploadUploading.
  ///
  /// In ru, this message translates to:
  /// **'Загрузка…'**
  String get uploadUploading;

  /// No description provided for @uploadContinue.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить загрузку'**
  String get uploadContinue;

  /// No description provided for @upload12Photos.
  ///
  /// In ru, this message translates to:
  /// **'Загрузить 12 фото'**
  String get upload12Photos;

  /// No description provided for @checkoutTitle.
  ///
  /// In ru, this message translates to:
  /// **'Оплата'**
  String get checkoutTitle;

  /// No description provided for @checkoutPayTitle.
  ///
  /// In ru, this message translates to:
  /// **'Оплата заказа'**
  String get checkoutPayTitle;

  /// No description provided for @checkoutSubmitGeneration.
  ///
  /// In ru, this message translates to:
  /// **'Отправка на генерацию'**
  String get checkoutSubmitGeneration;

  /// No description provided for @checkoutNeedCalibration.
  ///
  /// In ru, this message translates to:
  /// **'Нужна калибровка'**
  String get checkoutNeedCalibration;

  /// No description provided for @checkoutCalibrationBody.
  ///
  /// In ru, this message translates to:
  /// **'Для «Масштаб 1:1» выполните калибровку по карте, A4 или QR (§3.7).'**
  String get checkoutCalibrationBody;

  /// No description provided for @checkoutCalibrate.
  ///
  /// In ru, this message translates to:
  /// **'Калибровать'**
  String get checkoutCalibrate;

  /// No description provided for @checkoutCategory.
  ///
  /// In ru, this message translates to:
  /// **'Категория: {label}'**
  String checkoutCategory(String label);

  /// No description provided for @checkoutTier.
  ///
  /// In ru, this message translates to:
  /// **'Тариф: {label}'**
  String checkoutTier(String label);

  /// No description provided for @checkoutBasePrice.
  ///
  /// In ru, this message translates to:
  /// **'Базовая цена: {amount} ₽'**
  String checkoutBasePrice(String amount);

  /// No description provided for @checkoutUpsells.
  ///
  /// In ru, this message translates to:
  /// **'Дополнительные услуги'**
  String get checkoutUpsells;

  /// No description provided for @checkoutTotal.
  ///
  /// In ru, this message translates to:
  /// **'Итого: {amount} ₽'**
  String checkoutTotal(String amount);

  /// No description provided for @checkoutPromo.
  ///
  /// In ru, this message translates to:
  /// **'Промокод'**
  String get checkoutPromo;

  /// No description provided for @checkoutFioOptional.
  ///
  /// In ru, this message translates to:
  /// **'ФИО (необязательно)'**
  String get checkoutFioOptional;

  /// No description provided for @checkoutFioHint.
  ///
  /// In ru, this message translates to:
  /// **'Можно пропустить'**
  String get checkoutFioHint;

  /// No description provided for @checkoutFioTaxHint.
  ///
  /// In ru, this message translates to:
  /// **'ФИО используется для чека «Мой налог» (§19.8.1)'**
  String get checkoutFioTaxHint;

  /// No description provided for @checkoutPayCard.
  ///
  /// In ru, this message translates to:
  /// **'Оплатить картой'**
  String get checkoutPayCard;

  /// No description provided for @checkoutPaySbp.
  ///
  /// In ru, this message translates to:
  /// **'Оплатить СБП (QR)'**
  String get checkoutPaySbp;

  /// No description provided for @checkoutSbpOrderTitle.
  ///
  /// In ru, this message translates to:
  /// **'СБП — оплата заказа'**
  String get checkoutSbpOrderTitle;

  /// No description provided for @guestShootTitle.
  ///
  /// In ru, this message translates to:
  /// **'Съёмка по ссылке'**
  String get guestShootTitle;

  /// No description provided for @guestTask.
  ///
  /// In ru, this message translates to:
  /// **'Задача {id}…'**
  String guestTask(String id);

  /// No description provided for @guestMeta.
  ///
  /// In ru, this message translates to:
  /// **'Категория: {category} · тариф: {tier}'**
  String guestMeta(String category, String tier);

  /// No description provided for @guestHint.
  ///
  /// In ru, this message translates to:
  /// **'Гостевой режим: 12 ракурсов через AR или галерею (§3.15).'**
  String get guestHint;

  /// No description provided for @guestStartAr.
  ///
  /// In ru, this message translates to:
  /// **'Начать AR-съёмку'**
  String get guestStartAr;

  /// No description provided for @guestGallery12.
  ///
  /// In ru, this message translates to:
  /// **'12 фото из галереи'**
  String get guestGallery12;

  /// No description provided for @guestPhotosRequired.
  ///
  /// In ru, this message translates to:
  /// **'Нужно ровно {need} фото (выбрано {selected})'**
  String guestPhotosRequired(String need, String selected);

  /// No description provided for @guestUploadTitle.
  ///
  /// In ru, this message translates to:
  /// **'Отправка по ссылке'**
  String get guestUploadTitle;

  /// No description provided for @guestReadyToSend.
  ///
  /// In ru, this message translates to:
  /// **'Готово к отправке'**
  String get guestReadyToSend;

  /// No description provided for @guestGettingUrls.
  ///
  /// In ru, this message translates to:
  /// **'Получение upload URL…'**
  String get guestGettingUrls;

  /// No description provided for @guestUploading.
  ///
  /// In ru, this message translates to:
  /// **'Загрузка {current}/12…'**
  String guestUploading(String current);

  /// No description provided for @guestConfirming.
  ///
  /// In ru, this message translates to:
  /// **'Подтверждение…'**
  String get guestConfirming;

  /// No description provided for @guestSentToOwner.
  ///
  /// In ru, this message translates to:
  /// **'Фото отправлены владельцу'**
  String get guestSentToOwner;

  /// No description provided for @guestSend12Photos.
  ///
  /// In ru, this message translates to:
  /// **'Отправить 12 фото'**
  String get guestSend12Photos;

  /// No description provided for @guestLinkUsed.
  ///
  /// In ru, this message translates to:
  /// **'Ссылка использована. Владелец компании получит уведомление.'**
  String get guestLinkUsed;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'kk', 'ru', 'zh'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'kk':
      return AppLocalizationsKk();
    case 'ru':
      return AppLocalizationsRu();
    case 'zh':
      return AppLocalizationsZh();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
