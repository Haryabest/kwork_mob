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

  /// No description provided for @shootCategoryRestricted.
  ///
  /// In ru, this message translates to:
  /// **'Эта категория недоступна для вашей роли в компании'**
  String get shootCategoryRestricted;

  /// No description provided for @corpPolicyDenied.
  ///
  /// In ru, this message translates to:
  /// **'Действие недоступно по политике компании'**
  String get corpPolicyDenied;

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

  /// No description provided for @guestMissingFrame.
  ///
  /// In ru, this message translates to:
  /// **'Нет файла ракурса {index}'**
  String guestMissingFrame(String index);

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

  /// No description provided for @prefTopupFailed.
  ///
  /// In ru, this message translates to:
  /// **'Ошибка пополнения'**
  String get prefTopupFailed;

  /// No description provided for @homePendingUploadTitle.
  ///
  /// In ru, this message translates to:
  /// **'Незавершённая загрузка фото ({uploaded}/{total})'**
  String homePendingUploadTitle(String uploaded, String total);

  /// No description provided for @homePendingUploadHint.
  ///
  /// In ru, this message translates to:
  /// **'Загрузка прервалась. Можно продолжить с последнего кадра.'**
  String get homePendingUploadHint;

  /// No description provided for @homeModePrefix.
  ///
  /// In ru, this message translates to:
  /// **'Режим: {mode}'**
  String homeModePrefix(String mode);

  /// No description provided for @homeNoCompanies.
  ///
  /// In ru, this message translates to:
  /// **'Нет привязанных компаний'**
  String get homeNoCompanies;

  /// No description provided for @homeSwitchModeTitle.
  ///
  /// In ru, this message translates to:
  /// **'Сменить режим?'**
  String get homeSwitchModeTitle;

  /// No description provided for @homeSwitchModeBody.
  ///
  /// In ru, this message translates to:
  /// **'Подтвердите переключение Личный / Компания'**
  String get homeSwitchModeBody;

  /// No description provided for @homeShootLinkQr.
  ///
  /// In ru, this message translates to:
  /// **'Съёмка по ссылке (QR)'**
  String get homeShootLinkQr;

  /// No description provided for @ordersExecutorFilter.
  ///
  /// In ru, this message translates to:
  /// **'Исполнитель §3.16.2'**
  String get ordersExecutorFilter;

  /// No description provided for @ordersAllMembers.
  ///
  /// In ru, this message translates to:
  /// **'Все сотрудники'**
  String get ordersAllMembers;

  /// No description provided for @ordersEmpty.
  ///
  /// In ru, this message translates to:
  /// **'Нет заказов'**
  String get ordersEmpty;

  /// No description provided for @orderStatusPending.
  ///
  /// In ru, this message translates to:
  /// **'Новый'**
  String get orderStatusPending;

  /// No description provided for @orderStatusAwaitingPayment.
  ///
  /// In ru, this message translates to:
  /// **'Ожидает оплаты'**
  String get orderStatusAwaitingPayment;

  /// No description provided for @orderStatusQueued.
  ///
  /// In ru, this message translates to:
  /// **'В очереди'**
  String get orderStatusQueued;

  /// No description provided for @orderStatusProcessing.
  ///
  /// In ru, this message translates to:
  /// **'В обработке'**
  String get orderStatusProcessing;

  /// No description provided for @orderStatusCompleted.
  ///
  /// In ru, this message translates to:
  /// **'Готов'**
  String get orderStatusCompleted;

  /// No description provided for @orderStatusFailed.
  ///
  /// In ru, this message translates to:
  /// **'Ошибка'**
  String get orderStatusFailed;

  /// No description provided for @orderStatusCancelled.
  ///
  /// In ru, this message translates to:
  /// **'Отменён'**
  String get orderStatusCancelled;

  /// No description provided for @orderStatusPaid.
  ///
  /// In ru, this message translates to:
  /// **'Оплачен'**
  String get orderStatusPaid;

  /// No description provided for @orderStatusBlockedNsfw.
  ///
  /// In ru, this message translates to:
  /// **'NSFW блок'**
  String get orderStatusBlockedNsfw;

  /// No description provided for @notificationsTitle.
  ///
  /// In ru, this message translates to:
  /// **'Уведомления'**
  String get notificationsTitle;

  /// No description provided for @notificationsEmpty.
  ///
  /// In ru, this message translates to:
  /// **'Нет уведомлений'**
  String get notificationsEmpty;

  /// No description provided for @queueGenerationTitle.
  ///
  /// In ru, this message translates to:
  /// **'Генерация модели'**
  String get queueGenerationTitle;

  /// No description provided for @queueCancelTitle.
  ///
  /// In ru, this message translates to:
  /// **'Отмена генерации'**
  String get queueCancelTitle;

  /// No description provided for @queueCancelWarning.
  ///
  /// In ru, this message translates to:
  /// **'Внимание! Отмена во время генерации не приводит к возврату средств, так как вычислительные ресурсы уже затрачены. Отменить?'**
  String get queueCancelWarning;

  /// No description provided for @queueUnderstand.
  ///
  /// In ru, this message translates to:
  /// **'Я понимаю'**
  String get queueUnderstand;

  /// No description provided for @queueReconnectWs.
  ///
  /// In ru, this message translates to:
  /// **'Переподключить WebSocket'**
  String get queueReconnectWs;

  /// No description provided for @queueNsfwBlocked.
  ///
  /// In ru, this message translates to:
  /// **'Заказ заблокирован: NSFW на текстурах импорта. Средства возвращены на баланс компании. Аккаунт на ручной проверке до 24 ч (§10.8).'**
  String get queueNsfwBlocked;

  /// No description provided for @queueStatus.
  ///
  /// In ru, this message translates to:
  /// **'Статус: {status}'**
  String queueStatus(String status);

  /// No description provided for @queuePosition.
  ///
  /// In ru, this message translates to:
  /// **'Позиция в очереди: {pos}. Примерное время ожидания: {ewt} мин'**
  String queuePosition(String pos, String ewt);

  /// No description provided for @queueWsConnected.
  ///
  /// In ru, this message translates to:
  /// **'WebSocket: подключено'**
  String get queueWsConnected;

  /// No description provided for @queueWsErrorShort.
  ///
  /// In ru, this message translates to:
  /// **'WebSocket: ошибка'**
  String get queueWsErrorShort;

  /// No description provided for @queueWsConnecting.
  ///
  /// In ru, this message translates to:
  /// **'WebSocket: …'**
  String get queueWsConnecting;

  /// No description provided for @queueRefresh.
  ///
  /// In ru, this message translates to:
  /// **'Обновить'**
  String get queueRefresh;

  /// No description provided for @queueCancelOrder.
  ///
  /// In ru, this message translates to:
  /// **'Отменить'**
  String get queueCancelOrder;

  /// No description provided for @faqSupportTitle.
  ///
  /// In ru, this message translates to:
  /// **'FAQ / Поддержка'**
  String get faqSupportTitle;

  /// No description provided for @faqTab.
  ///
  /// In ru, this message translates to:
  /// **'FAQ'**
  String get faqTab;

  /// No description provided for @faqMyTickets.
  ///
  /// In ru, this message translates to:
  /// **'Мои обращения'**
  String get faqMyTickets;

  /// No description provided for @faqLoadError.
  ///
  /// In ru, this message translates to:
  /// **'Ошибка загрузки: {error}'**
  String faqLoadError(String error);

  /// No description provided for @faqQuestionMin.
  ///
  /// In ru, this message translates to:
  /// **'Вопрос: минимум 10 символов'**
  String get faqQuestionMin;

  /// No description provided for @faqDefaultSubject.
  ///
  /// In ru, this message translates to:
  /// **'Вопрос из приложения'**
  String get faqDefaultSubject;

  /// No description provided for @faqQuestionSent.
  ///
  /// In ru, this message translates to:
  /// **'Вопрос отправлен'**
  String get faqQuestionSent;

  /// No description provided for @faqEmpty.
  ///
  /// In ru, this message translates to:
  /// **'Пока нет вопросов в FAQ'**
  String get faqEmpty;

  /// No description provided for @faqAskPrompt.
  ///
  /// In ru, this message translates to:
  /// **'Не нашли ответ? Задайте вопрос'**
  String get faqAskPrompt;

  /// No description provided for @faqSubjectOptional.
  ///
  /// In ru, this message translates to:
  /// **'Тема (опционально)'**
  String get faqSubjectOptional;

  /// No description provided for @faqYourQuestion.
  ///
  /// In ru, this message translates to:
  /// **'Ваш вопрос'**
  String get faqYourQuestion;

  /// No description provided for @faqSending.
  ///
  /// In ru, this message translates to:
  /// **'Отправка…'**
  String get faqSending;

  /// No description provided for @faqSend.
  ///
  /// In ru, this message translates to:
  /// **'Отправить'**
  String get faqSend;

  /// No description provided for @faqNoTickets.
  ///
  /// In ru, this message translates to:
  /// **'Нет обращений'**
  String get faqNoTickets;

  /// No description provided for @faqTicketDefault.
  ///
  /// In ru, this message translates to:
  /// **'Обращение #{id}'**
  String faqTicketDefault(String id);

  /// No description provided for @faqSupportRole.
  ///
  /// In ru, this message translates to:
  /// **'Поддержка'**
  String get faqSupportRole;

  /// No description provided for @faqYouRole.
  ///
  /// In ru, this message translates to:
  /// **'Вы'**
  String get faqYouRole;

  /// No description provided for @faqClarifyHint.
  ///
  /// In ru, this message translates to:
  /// **'Уточняющий вопрос…'**
  String get faqClarifyHint;

  /// No description provided for @faqReply.
  ///
  /// In ru, this message translates to:
  /// **'Ответить'**
  String get faqReply;

  /// No description provided for @faqClose.
  ///
  /// In ru, this message translates to:
  /// **'Закрыть'**
  String get faqClose;

  /// No description provided for @faqTicketClosed.
  ///
  /// In ru, this message translates to:
  /// **'Обращение закрыто'**
  String get faqTicketClosed;

  /// No description provided for @teamTitle.
  ///
  /// In ru, this message translates to:
  /// **'Команда'**
  String get teamTitle;

  /// No description provided for @teamNoAccess.
  ///
  /// In ru, this message translates to:
  /// **'Нет доступа к команде'**
  String get teamNoAccess;

  /// No description provided for @teamMembers.
  ///
  /// In ru, this message translates to:
  /// **'Участники'**
  String get teamMembers;

  /// No description provided for @teamNoMembers.
  ///
  /// In ru, this message translates to:
  /// **'Нет сотрудников'**
  String get teamNoMembers;

  /// No description provided for @teamInvite.
  ///
  /// In ru, this message translates to:
  /// **'Пригласить'**
  String get teamInvite;

  /// No description provided for @teamAudit.
  ///
  /// In ru, this message translates to:
  /// **'Аудит'**
  String get teamAudit;

  /// No description provided for @teamNoAudit.
  ///
  /// In ru, this message translates to:
  /// **'Нет записей аудита'**
  String get teamNoAudit;

  /// No description provided for @teamExtendAllTitle.
  ///
  /// In ru, this message translates to:
  /// **'Продлить все исходники'**
  String get teamExtendAllTitle;

  /// No description provided for @teamExtendAllBody.
  ///
  /// In ru, this message translates to:
  /// **'Продлить хранение облачных исходников для всех моделей компании на 30 дней. Лимит — 3 продления на модель (§9.1.2).'**
  String get teamExtendAllBody;

  /// No description provided for @teamExtend.
  ///
  /// In ru, this message translates to:
  /// **'Продлить'**
  String get teamExtend;

  /// No description provided for @teamExtendAllBtn.
  ///
  /// In ru, this message translates to:
  /// **'Продлить все исходники §9.1.2'**
  String get teamExtendAllBtn;

  /// No description provided for @teamMemberFallback.
  ///
  /// In ru, this message translates to:
  /// **'Сотрудник'**
  String get teamMemberFallback;

  /// No description provided for @teamRole.
  ///
  /// In ru, this message translates to:
  /// **'Роль'**
  String get teamRole;

  /// No description provided for @teamActiveOrdersLimit.
  ///
  /// In ru, this message translates to:
  /// **'Лимит активных заказов'**
  String get teamActiveOrdersLimit;

  /// No description provided for @teamInviteSent.
  ///
  /// In ru, this message translates to:
  /// **'Приглашение отправлено'**
  String get teamInviteSent;

  /// No description provided for @teamInviteSentWithLink.
  ///
  /// In ru, this message translates to:
  /// **'Приглашение отправлено · ссылка скопирована'**
  String get teamInviteSentWithLink;

  /// No description provided for @teamMemberSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'{role} · лимит {limit} заказов'**
  String teamMemberSubtitle(String role, String limit);

  /// No description provided for @teamCompany.
  ///
  /// In ru, this message translates to:
  /// **'Компания #{id}'**
  String teamCompany(String id);

  /// No description provided for @teamSendInvite.
  ///
  /// In ru, this message translates to:
  /// **'Отправить приглашение'**
  String get teamSendInvite;

  /// No description provided for @teamSearchHint.
  ///
  /// In ru, this message translates to:
  /// **'Имя или email'**
  String get teamSearchHint;

  /// No description provided for @teamRoleAll.
  ///
  /// In ru, this message translates to:
  /// **'Все роли'**
  String get teamRoleAll;

  /// No description provided for @teamLoadMore.
  ///
  /// In ru, this message translates to:
  /// **'Загрузить ещё'**
  String get teamLoadMore;

  /// No description provided for @mvPublishValidating.
  ///
  /// In ru, this message translates to:
  /// **'Проверка импорта'**
  String get mvPublishValidating;

  /// No description provided for @mvPublishImported.
  ///
  /// In ru, this message translates to:
  /// **'Импортировано'**
  String get mvPublishImported;

  /// No description provided for @mvPublishImportFailed.
  ///
  /// In ru, this message translates to:
  /// **'Ошибка импорта'**
  String get mvPublishImportFailed;

  /// No description provided for @mvPublishNotPublished.
  ///
  /// In ru, this message translates to:
  /// **'Не опубликовано'**
  String get mvPublishNotPublished;

  /// No description provided for @mvPublishVerified.
  ///
  /// In ru, this message translates to:
  /// **'Проверено'**
  String get mvPublishVerified;

  /// No description provided for @mvPublishPublished.
  ///
  /// In ru, this message translates to:
  /// **'Опубликовано'**
  String get mvPublishPublished;

  /// No description provided for @mvRenameTitle.
  ///
  /// In ru, this message translates to:
  /// **'Переименовать модель'**
  String get mvRenameTitle;

  /// No description provided for @mvNameLabel.
  ///
  /// In ru, this message translates to:
  /// **'Название'**
  String get mvNameLabel;

  /// No description provided for @mvLinkCopied.
  ///
  /// In ru, this message translates to:
  /// **'Ссылка скопирована'**
  String get mvLinkCopied;

  /// No description provided for @mvMovedToTrash.
  ///
  /// In ru, this message translates to:
  /// **'Модель перемещена в корзину'**
  String get mvMovedToTrash;

  /// No description provided for @mvRetry.
  ///
  /// In ru, this message translates to:
  /// **'Повторить'**
  String get mvRetry;

  /// No description provided for @mvNoModels.
  ///
  /// In ru, this message translates to:
  /// **'Пока нет моделей'**
  String get mvNoModels;

  /// No description provided for @mvTitle.
  ///
  /// In ru, this message translates to:
  /// **'Модели'**
  String get mvTitle;

  /// No description provided for @mvTrash.
  ///
  /// In ru, this message translates to:
  /// **'Корзина'**
  String get mvTrash;

  /// No description provided for @mvFilterAll.
  ///
  /// In ru, this message translates to:
  /// **'Все'**
  String get mvFilterAll;

  /// No description provided for @mvFilterFavorites.
  ///
  /// In ru, this message translates to:
  /// **'Избранное'**
  String get mvFilterFavorites;

  /// No description provided for @mvSortNewest.
  ///
  /// In ru, this message translates to:
  /// **'Сначала новые'**
  String get mvSortNewest;

  /// No description provided for @mvSortOldest.
  ///
  /// In ru, this message translates to:
  /// **'Сначала старые'**
  String get mvSortOldest;

  /// No description provided for @mvNoModelsFilter.
  ///
  /// In ru, this message translates to:
  /// **'Нет моделей по фильтру'**
  String get mvNoModelsFilter;

  /// No description provided for @mvDownloadGlbOzon.
  ///
  /// In ru, this message translates to:
  /// **'Скачать .glb (Ozon)'**
  String get mvDownloadGlbOzon;

  /// No description provided for @mvDownloadUsdzWb.
  ///
  /// In ru, this message translates to:
  /// **'Скачать .usdz (Wildberries)'**
  String get mvDownloadUsdzWb;

  /// No description provided for @mvShare.
  ///
  /// In ru, this message translates to:
  /// **'Поделиться'**
  String get mvShare;

  /// No description provided for @mvRate.
  ///
  /// In ru, this message translates to:
  /// **'Оценить модель'**
  String get mvRate;

  /// No description provided for @mvVerifyLink.
  ///
  /// In ru, this message translates to:
  /// **'Ссылка для верификации'**
  String get mvVerifyLink;

  /// No description provided for @mvEdit.
  ///
  /// In ru, this message translates to:
  /// **'Редактировать'**
  String get mvEdit;

  /// No description provided for @mvRename.
  ///
  /// In ru, this message translates to:
  /// **'Переименовать'**
  String get mvRename;

  /// No description provided for @mvDelete.
  ///
  /// In ru, this message translates to:
  /// **'Удалить'**
  String get mvDelete;

  /// No description provided for @mvLinkCopiedMarketplace.
  ///
  /// In ru, this message translates to:
  /// **'Ссылка {mp} скопирована'**
  String mvLinkCopiedMarketplace(String mp);

  /// No description provided for @mvGlbSaved.
  ///
  /// In ru, this message translates to:
  /// **'GLB сохранён: {path}'**
  String mvGlbSaved(String path);

  /// No description provided for @mvPublicLinkTitle.
  ///
  /// In ru, this message translates to:
  /// **'Публичная ссылка §3.12'**
  String get mvPublicLinkTitle;

  /// No description provided for @mvUntil.
  ///
  /// In ru, this message translates to:
  /// **'До: {date}'**
  String mvUntil(String date);

  /// No description provided for @mvNoLocalPhotosTitle.
  ///
  /// In ru, this message translates to:
  /// **'Нет локальных фото'**
  String get mvNoLocalPhotosTitle;

  /// No description provided for @mvNoLocalPhotosBody.
  ///
  /// In ru, this message translates to:
  /// **'Для перегенерации нужны 12 исходников на устройстве. Восстановить из облака или снять заново?'**
  String get mvNoLocalPhotosBody;

  /// No description provided for @mvRestore.
  ///
  /// In ru, this message translates to:
  /// **'Восстановить'**
  String get mvRestore;

  /// No description provided for @mvCantDetectCategory.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось определить категорию/тариф'**
  String get mvCantDetectCategory;

  /// No description provided for @mvStorageExtended.
  ///
  /// In ru, this message translates to:
  /// **'Хранение продлено'**
  String get mvStorageExtended;

  /// No description provided for @mvDeleteTitle.
  ///
  /// In ru, this message translates to:
  /// **'Удалить модель?'**
  String get mvDeleteTitle;

  /// No description provided for @mvDeleteBody.
  ///
  /// In ru, this message translates to:
  /// **'Исходные фото и модель будут перемещены в корзину на 30 дней. Продолжить?'**
  String get mvDeleteBody;

  /// No description provided for @mvInTrash.
  ///
  /// In ru, this message translates to:
  /// **'В корзине'**
  String get mvInTrash;

  /// No description provided for @mvSourcesRestored.
  ///
  /// In ru, this message translates to:
  /// **'Исходники восстановлены'**
  String get mvSourcesRestored;

  /// No description provided for @mvCardLinkTitle.
  ///
  /// In ru, this message translates to:
  /// **'Ссылка на карточку'**
  String get mvCardLinkTitle;

  /// No description provided for @mvCardLinkHint.
  ///
  /// In ru, this message translates to:
  /// **'https://www.wildberries.ru/... или ozon.ru/...'**
  String get mvCardLinkHint;

  /// No description provided for @mvAdd.
  ///
  /// In ru, this message translates to:
  /// **'Добавить'**
  String get mvAdd;

  /// No description provided for @mvLinkStatus.
  ///
  /// In ru, this message translates to:
  /// **'Ссылка: {status}'**
  String mvLinkStatus(String status);

  /// No description provided for @mvRateTitle.
  ///
  /// In ru, this message translates to:
  /// **'Оцените качество модели от 1 до 5'**
  String get mvRateTitle;

  /// No description provided for @mvWhatsWrong.
  ///
  /// In ru, this message translates to:
  /// **'Что не так?'**
  String get mvWhatsWrong;

  /// No description provided for @mvReasonBlurry.
  ///
  /// In ru, this message translates to:
  /// **'размытые текстуры'**
  String get mvReasonBlurry;

  /// No description provided for @mvReasonHoles.
  ///
  /// In ru, this message translates to:
  /// **'дыры или артефакты'**
  String get mvReasonHoles;

  /// No description provided for @mvReasonScale.
  ///
  /// In ru, this message translates to:
  /// **'неправильный масштаб'**
  String get mvReasonScale;

  /// No description provided for @mvReasonColor.
  ///
  /// In ru, this message translates to:
  /// **'не тот цвет / освещение'**
  String get mvReasonColor;

  /// No description provided for @mvReasonOther.
  ///
  /// In ru, this message translates to:
  /// **'другое'**
  String get mvReasonOther;

  /// No description provided for @mvComment.
  ///
  /// In ru, this message translates to:
  /// **'Комментарий'**
  String get mvComment;

  /// No description provided for @mvLater.
  ///
  /// In ru, this message translates to:
  /// **'Позже'**
  String get mvLater;

  /// No description provided for @mvModelTitle.
  ///
  /// In ru, this message translates to:
  /// **'3D-модель'**
  String get mvModelTitle;

  /// No description provided for @mvGlbNotReady.
  ///
  /// In ru, this message translates to:
  /// **'GLB ещё не готов'**
  String get mvGlbNotReady;

  /// No description provided for @mvCloud.
  ///
  /// In ru, this message translates to:
  /// **'Облако: {days} дн. · продлений {used}/{max}'**
  String mvCloud(String days, String used, String max);

  /// No description provided for @mvLocalGlbSaved.
  ///
  /// In ru, this message translates to:
  /// **'Локальный GLB сохранён'**
  String get mvLocalGlbSaved;

  /// No description provided for @mvRegenerate.
  ///
  /// In ru, this message translates to:
  /// **'Перегенерировать'**
  String get mvRegenerate;

  /// No description provided for @mvUpdateGlb.
  ///
  /// In ru, this message translates to:
  /// **'Обновить GLB'**
  String get mvUpdateGlb;

  /// No description provided for @mvGlbLocal.
  ///
  /// In ru, this message translates to:
  /// **'GLB локально'**
  String get mvGlbLocal;

  /// No description provided for @mvDownloadWb.
  ///
  /// In ru, this message translates to:
  /// **'Скачать WB'**
  String get mvDownloadWb;

  /// No description provided for @mvDownloadOzon.
  ///
  /// In ru, this message translates to:
  /// **'Скачать Ozon'**
  String get mvDownloadOzon;

  /// No description provided for @mvSources.
  ///
  /// In ru, this message translates to:
  /// **'Исходники'**
  String get mvSources;

  /// No description provided for @mvExtend30.
  ///
  /// In ru, this message translates to:
  /// **'+30 дн.'**
  String get mvExtend30;

  /// No description provided for @mvToTrash.
  ///
  /// In ru, this message translates to:
  /// **'В корзину'**
  String get mvToTrash;

  /// No description provided for @mvLink.
  ///
  /// In ru, this message translates to:
  /// **'Ссылка'**
  String get mvLink;

  /// No description provided for @mvImOnWb.
  ///
  /// In ru, this message translates to:
  /// **'Я на WB'**
  String get mvImOnWb;

  /// No description provided for @mvImOnOzon.
  ///
  /// In ru, this message translates to:
  /// **'Я на Ozon'**
  String get mvImOnOzon;

  /// No description provided for @mvApiResult.
  ///
  /// In ru, this message translates to:
  /// **'API: {status}'**
  String mvApiResult(String status);

  /// No description provided for @orderLimitTitle.
  ///
  /// In ru, this message translates to:
  /// **'Лимит активных заказов'**
  String get orderLimitTitle;

  /// No description provided for @orderLimitBody.
  ///
  /// In ru, this message translates to:
  /// **'Достигнут лимит одновременных заказов для вашей роли. Дождитесь завершения текущих генераций или обратитесь к Owner.'**
  String get orderLimitBody;

  /// No description provided for @orderLimitOk.
  ///
  /// In ru, this message translates to:
  /// **'Понятно'**
  String get orderLimitOk;

  /// No description provided for @trashTitle.
  ///
  /// In ru, this message translates to:
  /// **'Корзина'**
  String get trashTitle;

  /// No description provided for @trashEmpty.
  ///
  /// In ru, this message translates to:
  /// **'Корзина пуста\nУдалённые модели хранятся 30 дней'**
  String get trashEmpty;

  /// No description provided for @trashRestore.
  ///
  /// In ru, this message translates to:
  /// **'Восстановить'**
  String get trashRestore;

  /// No description provided for @trashRestored.
  ///
  /// In ru, this message translates to:
  /// **'Восстановлено'**
  String get trashRestored;

  /// No description provided for @trashOrderLine.
  ///
  /// In ru, this message translates to:
  /// **'Заказ #{id} · в корзине {date}'**
  String trashOrderLine(String id, String date);

  /// No description provided for @trashPurgeLine.
  ///
  /// In ru, this message translates to:
  /// **'Удаление: {date}'**
  String trashPurgeLine(String date);

  /// No description provided for @prefPushEnabled.
  ///
  /// In ru, this message translates to:
  /// **'Push-уведомления'**
  String get prefPushEnabled;

  /// No description provided for @prefEmailEnabled.
  ///
  /// In ru, this message translates to:
  /// **'Email-уведомления'**
  String get prefEmailEnabled;

  /// No description provided for @prefGenerationDone.
  ///
  /// In ru, this message translates to:
  /// **'Генерация готова'**
  String get prefGenerationDone;

  /// No description provided for @prefRefund.
  ///
  /// In ru, this message translates to:
  /// **'Возврат средств'**
  String get prefRefund;

  /// No description provided for @prefNsfwBlocked.
  ///
  /// In ru, this message translates to:
  /// **'NSFW-блокировка'**
  String get prefNsfwBlocked;

  /// No description provided for @prefSourceExpire.
  ///
  /// In ru, this message translates to:
  /// **'Истечение исходников'**
  String get prefSourceExpire;

  /// No description provided for @prefCleanup.
  ///
  /// In ru, this message translates to:
  /// **'Очистка хранилища'**
  String get prefCleanup;

  /// No description provided for @prefPublishReminder.
  ///
  /// In ru, this message translates to:
  /// **'Напоминание опубликовать'**
  String get prefPublishReminder;

  /// No description provided for @prefSupportReply.
  ///
  /// In ru, this message translates to:
  /// **'Ответ поддержки'**
  String get prefSupportReply;

  /// No description provided for @profileInnLabel.
  ///
  /// In ru, this message translates to:
  /// **'ИНН (необязательно) §19.14.1'**
  String get profileInnLabel;

  /// No description provided for @profilePhoneLabel.
  ///
  /// In ru, this message translates to:
  /// **'Телефон (необязательно) §19.14.1'**
  String get profilePhoneLabel;

  /// No description provided for @profileFullNameLabel.
  ///
  /// In ru, this message translates to:
  /// **'ФИО (необязательно) §19.14.1'**
  String get profileFullNameLabel;

  /// No description provided for @profileExportFormat.
  ///
  /// In ru, this message translates to:
  /// **'Формат экспорта §19.14.3'**
  String get profileExportFormat;

  /// No description provided for @profileExportGlb.
  ///
  /// In ru, this message translates to:
  /// **'.glb (Ozon / универсальный)'**
  String get profileExportGlb;

  /// No description provided for @profileExportUsdz.
  ///
  /// In ru, this message translates to:
  /// **'.usdz (Wildberries / AR)'**
  String get profileExportUsdz;

  /// No description provided for @profileTheme.
  ///
  /// In ru, this message translates to:
  /// **'Тема оформления §19.14.3'**
  String get profileTheme;

  /// No description provided for @themeSystem.
  ///
  /// In ru, this message translates to:
  /// **'Системная'**
  String get themeSystem;

  /// No description provided for @themeLight.
  ///
  /// In ru, this message translates to:
  /// **'Светлая'**
  String get themeLight;

  /// No description provided for @themeDark.
  ///
  /// In ru, this message translates to:
  /// **'Тёмная'**
  String get themeDark;

  /// No description provided for @profileLanguage.
  ///
  /// In ru, this message translates to:
  /// **'Язык'**
  String get profileLanguage;

  /// No description provided for @profileNotificationsSection.
  ///
  /// In ru, this message translates to:
  /// **'Уведомления §19.14.3'**
  String get profileNotificationsSection;

  /// No description provided for @profileEventsSection.
  ///
  /// In ru, this message translates to:
  /// **'События §3.4.3'**
  String get profileEventsSection;

  /// No description provided for @profileSecuritySection.
  ///
  /// In ru, this message translates to:
  /// **'Безопасность §19.14.4'**
  String get profileSecuritySection;

  /// No description provided for @profileChangePassword.
  ///
  /// In ru, this message translates to:
  /// **'Изменить пароль'**
  String get profileChangePassword;

  /// No description provided for @profileChangePasswordTitle.
  ///
  /// In ru, this message translates to:
  /// **'Изменить пароль'**
  String get profileChangePasswordTitle;

  /// No description provided for @profileCurrentPassword.
  ///
  /// In ru, this message translates to:
  /// **'Текущий пароль'**
  String get profileCurrentPassword;

  /// No description provided for @profileNewPassword.
  ///
  /// In ru, this message translates to:
  /// **'Новый пароль'**
  String get profileNewPassword;

  /// No description provided for @profilePasswordConfirm.
  ///
  /// In ru, this message translates to:
  /// **'Подтверждение'**
  String get profilePasswordConfirm;

  /// No description provided for @profilePasswordChanged.
  ///
  /// In ru, this message translates to:
  /// **'Пароль изменён'**
  String get profilePasswordChanged;

  /// No description provided for @profileMinPassword.
  ///
  /// In ru, this message translates to:
  /// **'Минимум 8 символов'**
  String get profileMinPassword;

  /// No description provided for @profilePasswordMismatch.
  ///
  /// In ru, this message translates to:
  /// **'Пароли не совпадают'**
  String get profilePasswordMismatch;

  /// No description provided for @profile2faSection.
  ///
  /// In ru, this message translates to:
  /// **'Двухфакторная аутентификация §19.14.4'**
  String get profile2faSection;

  /// No description provided for @profile2faEnabled.
  ///
  /// In ru, this message translates to:
  /// **'2FA включена'**
  String get profile2faEnabled;

  /// No description provided for @profile2faDisabled.
  ///
  /// In ru, this message translates to:
  /// **'2FA выключена'**
  String get profile2faDisabled;

  /// No description provided for @profile2faOwnerRequired.
  ///
  /// In ru, this message translates to:
  /// **'Для Owner 2FA обязательна (§10.7.5)'**
  String get profile2faOwnerRequired;

  /// No description provided for @profile2faActiveHint.
  ///
  /// In ru, this message translates to:
  /// **'TOTP активен — Google Authenticator, 1Password или аналог.'**
  String get profile2faActiveHint;

  /// No description provided for @profile2faStep1.
  ///
  /// In ru, this message translates to:
  /// **'1. Отсканируйте QR в приложении-аутентификаторе'**
  String get profile2faStep1;

  /// No description provided for @profile2faStep2.
  ///
  /// In ru, this message translates to:
  /// **'2. Или введите секрет вручную'**
  String get profile2faStep2;

  /// No description provided for @profileSecretCopied.
  ///
  /// In ru, this message translates to:
  /// **'Секрет скопирован'**
  String get profileSecretCopied;

  /// No description provided for @profile2faCodeLabel.
  ///
  /// In ru, this message translates to:
  /// **'Код из Authenticator'**
  String get profile2faCodeLabel;

  /// No description provided for @profileConfirm2fa.
  ///
  /// In ru, this message translates to:
  /// **'Подтвердить 2FA'**
  String get profileConfirm2fa;

  /// No description provided for @profileEnable2fa.
  ///
  /// In ru, this message translates to:
  /// **'Включить 2FA'**
  String get profileEnable2fa;

  /// No description provided for @profile2faEnabledSnackbar.
  ///
  /// In ru, this message translates to:
  /// **'2FA включена'**
  String get profile2faEnabledSnackbar;

  /// No description provided for @profileDeleteAccountTitle.
  ///
  /// In ru, this message translates to:
  /// **'Удалить аккаунт?'**
  String get profileDeleteAccountTitle;

  /// No description provided for @profileDeleteAccountBody.
  ///
  /// In ru, this message translates to:
  /// **'Все модели и персональные данные будут удалены в течение 30 дней (§2.8.3). Финансовые записи анонимизируются и хранятся 5 лет.'**
  String get profileDeleteAccountBody;

  /// No description provided for @profileDeleteAccountBtn.
  ///
  /// In ru, this message translates to:
  /// **'Удалить'**
  String get profileDeleteAccountBtn;

  /// No description provided for @profileDeleteRequestAccepted.
  ///
  /// In ru, this message translates to:
  /// **'Запрос принят'**
  String get profileDeleteRequestAccepted;

  /// No description provided for @notifGenDoneTitle.
  ///
  /// In ru, this message translates to:
  /// **'Генерация завершена'**
  String get notifGenDoneTitle;

  /// No description provided for @notifGenDoneBody.
  ///
  /// In ru, this message translates to:
  /// **'Заказ #{id} готов к просмотру'**
  String notifGenDoneBody(String id);

  /// No description provided for @notifNsfwTitle.
  ///
  /// In ru, this message translates to:
  /// **'NSFW-блокировка'**
  String get notifNsfwTitle;

  /// No description provided for @notifNsfwBody.
  ///
  /// In ru, this message translates to:
  /// **'Заказ #{id} отклонён. Средства возвращены. Аккаунт на проверке до 24 ч.'**
  String notifNsfwBody(String id);

  /// No description provided for @notifGenFailedTitle.
  ///
  /// In ru, this message translates to:
  /// **'Ошибка генерации'**
  String get notifGenFailedTitle;

  /// No description provided for @notifGenFailedBody.
  ///
  /// In ru, this message translates to:
  /// **'Заказ #{id} не выполнен'**
  String notifGenFailedBody(String id);

  /// No description provided for @notifRefundTitle.
  ///
  /// In ru, this message translates to:
  /// **'Возврат средств'**
  String get notifRefundTitle;

  /// No description provided for @notifRefundBody.
  ///
  /// In ru, this message translates to:
  /// **'По заказу #{id} средства возвращены'**
  String notifRefundBody(String id);

  /// No description provided for @notifCancelledTitle.
  ///
  /// In ru, this message translates to:
  /// **'Заказ отменён'**
  String get notifCancelledTitle;

  /// No description provided for @notifCancelledBody.
  ///
  /// In ru, this message translates to:
  /// **'Заказ #{id} отменён'**
  String notifCancelledBody(String id);

  /// No description provided for @notifCompanyInviteTitle.
  ///
  /// In ru, this message translates to:
  /// **'Приглашение в компанию'**
  String get notifCompanyInviteTitle;

  /// No description provided for @publishGuideTitle.
  ///
  /// In ru, this message translates to:
  /// **'Как опубликовать'**
  String get publishGuideTitle;

  /// No description provided for @publishGuideIntro.
  ///
  /// In ru, this message translates to:
  /// **'Скачайте файлы модели и загрузите их в карточку товара на маркетплейсе.'**
  String get publishGuideIntro;

  /// No description provided for @publishGuideWbTitle.
  ///
  /// In ru, this message translates to:
  /// **'Wildberries'**
  String get publishGuideWbTitle;

  /// No description provided for @publishGuideWb1.
  ///
  /// In ru, this message translates to:
  /// **'1. Скачайте .usdz (кнопка «Скачать WB» в модели).'**
  String get publishGuideWb1;

  /// No description provided for @publishGuideWb2.
  ///
  /// In ru, this message translates to:
  /// **'2. Откройте карточку товара в кабинете WB → медиа → 3D.'**
  String get publishGuideWb2;

  /// No description provided for @publishGuideWb3.
  ///
  /// In ru, this message translates to:
  /// **'3. Загрузите .usdz для iOS-покупателей.'**
  String get publishGuideWb3;

  /// No description provided for @publishGuideOzonTitle.
  ///
  /// In ru, this message translates to:
  /// **'Ozon'**
  String get publishGuideOzonTitle;

  /// No description provided for @publishGuideOzon1.
  ///
  /// In ru, this message translates to:
  /// **'1. Скачайте .glb (кнопка «Скачать Ozon»).'**
  String get publishGuideOzon1;

  /// No description provided for @publishGuideOzon2.
  ///
  /// In ru, this message translates to:
  /// **'2. В кабинете Ozon откройте карточку → 3D-модель.'**
  String get publishGuideOzon2;

  /// No description provided for @publishGuideOzon3.
  ///
  /// In ru, this message translates to:
  /// **'3. Загрузите .glb для Android-покупателей.'**
  String get publishGuideOzon3;

  /// No description provided for @publishGuideOpenModels.
  ///
  /// In ru, this message translates to:
  /// **'К моделям'**
  String get publishGuideOpenModels;

  /// No description provided for @apiKeysTitle.
  ///
  /// In ru, this message translates to:
  /// **'API-ключи'**
  String get apiKeysTitle;

  /// No description provided for @apiKeysSubtitle.
  ///
  /// In ru, this message translates to:
  /// **'Owner · scopes · rate limit'**
  String get apiKeysSubtitle;

  /// No description provided for @apiKeysCreate.
  ///
  /// In ru, this message translates to:
  /// **'Создать ключ'**
  String get apiKeysCreate;

  /// No description provided for @apiKeysRevoke.
  ///
  /// In ru, this message translates to:
  /// **'Отозвать'**
  String get apiKeysRevoke;

  /// No description provided for @apiKeysCopyOnce.
  ///
  /// In ru, this message translates to:
  /// **'Скопируйте ключ — он больше не покажется'**
  String get apiKeysCopyOnce;

  /// No description provided for @apiKeysName.
  ///
  /// In ru, this message translates to:
  /// **'Название'**
  String get apiKeysName;

  /// No description provided for @apiKeysEmpty.
  ///
  /// In ru, this message translates to:
  /// **'Нет ключей'**
  String get apiKeysEmpty;

  /// No description provided for @apiKeysCreated.
  ///
  /// In ru, this message translates to:
  /// **'Ключ создан'**
  String get apiKeysCreated;

  /// No description provided for @profileCopySecretBtn.
  ///
  /// In ru, this message translates to:
  /// **'Скопировать секрет'**
  String get profileCopySecretBtn;

  /// No description provided for @profile2faCodeStep.
  ///
  /// In ru, this message translates to:
  /// **'3. Введите 6-значный код'**
  String get profile2faCodeStep;

  /// No description provided for @profile2faSetupHint.
  ///
  /// In ru, this message translates to:
  /// **'Защитите аккаунт одноразовыми кодами при входе.'**
  String get profile2faSetupHint;

  /// No description provided for @profileDeleteAccount.
  ///
  /// In ru, this message translates to:
  /// **'Удалить аккаунт'**
  String get profileDeleteAccount;

  /// No description provided for @profileLogout.
  ///
  /// In ru, this message translates to:
  /// **'Выйти'**
  String get profileLogout;

  /// No description provided for @catClothing.
  ///
  /// In ru, this message translates to:
  /// **'Одежда'**
  String get catClothing;

  /// No description provided for @catShoes.
  ///
  /// In ru, this message translates to:
  /// **'Обувь'**
  String get catShoes;

  /// No description provided for @catElectronics.
  ///
  /// In ru, this message translates to:
  /// **'Электроника'**
  String get catElectronics;

  /// No description provided for @catFurniture.
  ///
  /// In ru, this message translates to:
  /// **'Мебель'**
  String get catFurniture;

  /// No description provided for @catDecor.
  ///
  /// In ru, this message translates to:
  /// **'Декор / Интерьер'**
  String get catDecor;

  /// No description provided for @catToys.
  ///
  /// In ru, this message translates to:
  /// **'Игрушки'**
  String get catToys;

  /// No description provided for @catAdult.
  ///
  /// In ru, this message translates to:
  /// **'Интимные товары (18+)'**
  String get catAdult;

  /// No description provided for @catOther.
  ///
  /// In ru, this message translates to:
  /// **'Другое'**
  String get catOther;

  /// No description provided for @tierSmall.
  ///
  /// In ru, this message translates to:
  /// **'Малый'**
  String get tierSmall;

  /// No description provided for @tierLarge.
  ///
  /// In ru, this message translates to:
  /// **'Крупный'**
  String get tierLarge;

  /// No description provided for @forbIntimate.
  ///
  /// In ru, this message translates to:
  /// **'Интим'**
  String get forbIntimate;

  /// No description provided for @forbWeapons.
  ///
  /// In ru, this message translates to:
  /// **'Оружие'**
  String get forbWeapons;

  /// No description provided for @forbDrugs.
  ///
  /// In ru, this message translates to:
  /// **'Наркотики'**
  String get forbDrugs;

  /// No description provided for @angle00.
  ///
  /// In ru, this message translates to:
  /// **'Низ 0° (фронт)'**
  String get angle00;

  /// No description provided for @angle01.
  ///
  /// In ru, this message translates to:
  /// **'Низ 45°'**
  String get angle01;

  /// No description provided for @angle02.
  ///
  /// In ru, this message translates to:
  /// **'Низ 90° (лево)'**
  String get angle02;

  /// No description provided for @angle03.
  ///
  /// In ru, this message translates to:
  /// **'Низ 135°'**
  String get angle03;

  /// No description provided for @angle04.
  ///
  /// In ru, this message translates to:
  /// **'Низ 180° (тыл)'**
  String get angle04;

  /// No description provided for @angle05.
  ///
  /// In ru, this message translates to:
  /// **'Низ 225°'**
  String get angle05;

  /// No description provided for @angle06.
  ///
  /// In ru, this message translates to:
  /// **'Низ 270° (право)'**
  String get angle06;

  /// No description provided for @angle07.
  ///
  /// In ru, this message translates to:
  /// **'Низ 315°'**
  String get angle07;

  /// No description provided for @angle08.
  ///
  /// In ru, this message translates to:
  /// **'Верх вперёд 45°'**
  String get angle08;

  /// No description provided for @angle09.
  ///
  /// In ru, this message translates to:
  /// **'Верх вправо 45°'**
  String get angle09;

  /// No description provided for @angle10.
  ///
  /// In ru, this message translates to:
  /// **'Верх назад 45°'**
  String get angle10;

  /// No description provided for @angle11.
  ///
  /// In ru, this message translates to:
  /// **'Верх влево 45°'**
  String get angle11;

  /// No description provided for @wsSessionExpired.
  ///
  /// In ru, this message translates to:
  /// **'Сессия истекла. Войдите снова.'**
  String get wsSessionExpired;

  /// No description provided for @wsServerUnavailable.
  ///
  /// In ru, this message translates to:
  /// **'Сервер недоступен. Проверьте API_URL и сеть.'**
  String get wsServerUnavailable;

  /// No description provided for @wsQueueFailed.
  ///
  /// In ru, this message translates to:
  /// **'Не удалось подключиться к очереди. Повторите позже.'**
  String get wsQueueFailed;

  /// No description provided for @wsQueueError.
  ///
  /// In ru, this message translates to:
  /// **'Ошибка соединения с очередью'**
  String get wsQueueError;

  /// No description provided for @calSaved.
  ///
  /// In ru, this message translates to:
  /// **'Калибровка сохранена на 30 дней'**
  String get calSaved;

  /// No description provided for @calRefFractionError.
  ///
  /// In ru, this message translates to:
  /// **'Укажите долю эталона в кадре (0.1–0.9)'**
  String get calRefFractionError;

  /// No description provided for @calEnterDimensions.
  ///
  /// In ru, this message translates to:
  /// **'Введите размеры в метрах'**
  String get calEnterDimensions;

  /// No description provided for @calCurrentLine.
  ///
  /// In ru, this message translates to:
  /// **'Текущая: {method} · до {date}'**
  String calCurrentLine(String method, String date);

  /// No description provided for @calReset.
  ///
  /// In ru, this message translates to:
  /// **'Сбросить калибровку'**
  String get calReset;

  /// No description provided for @calIntro.
  ///
  /// In ru, this message translates to:
  /// **'Для опции «Масштаб 1:1» и мебели нужна калибровка (§3.7). Положите эталон рядом с товаром и укажите, какую долю кадра он занимает.'**
  String get calIntro;

  /// No description provided for @calMethod.
  ///
  /// In ru, this message translates to:
  /// **'Способ'**
  String get calMethod;

  /// No description provided for @calMethodCard.
  ///
  /// In ru, this message translates to:
  /// **'Банковская карта (85.6×54 мм)'**
  String get calMethodCard;

  /// No description provided for @calMethodA4.
  ///
  /// In ru, this message translates to:
  /// **'Лист A4 (210×297 мм)'**
  String get calMethodA4;

  /// No description provided for @calMethodQr.
  ///
  /// In ru, this message translates to:
  /// **'QR-код с PDF (100 мм)'**
  String get calMethodQr;

  /// No description provided for @calMethodManual.
  ///
  /// In ru, this message translates to:
  /// **'Ручной ввод размеров (м)'**
  String get calMethodManual;

  /// No description provided for @calRefWidth.
  ///
  /// In ru, this message translates to:
  /// **'Ширина эталона в кадре (0.1–0.9)'**
  String get calRefWidth;

  /// No description provided for @calRefHeight.
  ///
  /// In ru, this message translates to:
  /// **'Высота эталона в кадре (0.1–0.9)'**
  String get calRefHeight;

  /// No description provided for @calSave.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить калибровку'**
  String get calSave;

  /// No description provided for @calQrIntro.
  ///
  /// In ru, this message translates to:
  /// **'Скачайте PDF с QR-кодом эталона (100×100 мм), распечатайте и положите рядом с товаром.'**
  String get calQrIntro;

  /// No description provided for @calDownloadPdf.
  ///
  /// In ru, this message translates to:
  /// **'Скачать PDF QR'**
  String get calDownloadPdf;

  /// No description provided for @calQrSide.
  ///
  /// In ru, this message translates to:
  /// **'Сторона QR (мм)'**
  String get calQrSide;

  /// No description provided for @calQrWidth.
  ///
  /// In ru, this message translates to:
  /// **'QR в кадре — ширина (доля)'**
  String get calQrWidth;

  /// No description provided for @calQrHeight.
  ///
  /// In ru, this message translates to:
  /// **'QR в кадре — высота (доля)'**
  String get calQrHeight;

  /// No description provided for @calSaveQr.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить по QR'**
  String get calSaveQr;

  /// No description provided for @calManualW.
  ///
  /// In ru, this message translates to:
  /// **'Ширина товара (м)'**
  String get calManualW;

  /// No description provided for @calManualH.
  ///
  /// In ru, this message translates to:
  /// **'Высота товара (м)'**
  String get calManualH;

  /// No description provided for @calManualD.
  ///
  /// In ru, this message translates to:
  /// **'Глубина товара (м)'**
  String get calManualD;

  /// No description provided for @storUsedLine.
  ///
  /// In ru, this message translates to:
  /// **'Занято: {bytes} · папок: {models} · GLB: {glbs}'**
  String storUsedLine(String bytes, String models, String glbs);

  /// No description provided for @storAutoDownload.
  ///
  /// In ru, this message translates to:
  /// **'Автозагрузка GLB при завершении'**
  String get storAutoDownload;

  /// No description provided for @storAutoDownloadDesc.
  ///
  /// In ru, this message translates to:
  /// **'§3.3.2 — сохранять модель на устройство'**
  String get storAutoDownloadDesc;

  /// No description provided for @storAutoCleanup.
  ///
  /// In ru, this message translates to:
  /// **'Автоочистка GLB'**
  String get storAutoCleanup;

  /// No description provided for @storAutoCleanupDesc.
  ///
  /// In ru, this message translates to:
  /// **'Удалять не избранные старше {days} дн.'**
  String storAutoCleanupDesc(String days);

  /// No description provided for @storCleanupDays.
  ///
  /// In ru, this message translates to:
  /// **'Срок автоочистки (дней)'**
  String get storCleanupDays;

  /// No description provided for @storDays7.
  ///
  /// In ru, this message translates to:
  /// **'7 дней'**
  String get storDays7;

  /// No description provided for @storDays14.
  ///
  /// In ru, this message translates to:
  /// **'14 дней'**
  String get storDays14;

  /// No description provided for @storDays30.
  ///
  /// In ru, this message translates to:
  /// **'30 дней'**
  String get storDays30;

  /// No description provided for @storDays60.
  ///
  /// In ru, this message translates to:
  /// **'60 дней'**
  String get storDays60;

  /// No description provided for @storDays90.
  ///
  /// In ru, this message translates to:
  /// **'90 дней'**
  String get storDays90;

  /// No description provided for @storCleanupNow.
  ///
  /// In ru, this message translates to:
  /// **'Очистить сейчас'**
  String get storCleanupNow;

  /// No description provided for @storExportZip.
  ///
  /// In ru, this message translates to:
  /// **'Экспорт всех GLB в ZIP'**
  String get storExportZip;

  /// No description provided for @storZipCopied.
  ///
  /// In ru, this message translates to:
  /// **'ZIP: {path} (путь скопирован)'**
  String storZipCopied(String path);

  /// No description provided for @storGlbDeleted.
  ///
  /// In ru, this message translates to:
  /// **'Удалено локальных GLB: {count}'**
  String storGlbDeleted(String count);

  /// No description provided for @impIntro.
  ///
  /// In ru, this message translates to:
  /// **'Загрузите готовый GLB (до 50 МБ). Доступно только Owner компании §6.10.'**
  String get impIntro;

  /// No description provided for @impFileTooBig.
  ///
  /// In ru, this message translates to:
  /// **'Файл больше 50 МБ (§6.10)'**
  String get impFileTooBig;

  /// No description provided for @impOwnerOnly.
  ///
  /// In ru, this message translates to:
  /// **'Импорт доступен только Owner компании (§6.10)'**
  String get impOwnerOnly;

  /// No description provided for @impUploadParamsError.
  ///
  /// In ru, this message translates to:
  /// **'Сервер не вернул параметры загрузки'**
  String get impUploadParamsError;

  /// No description provided for @impValidating.
  ///
  /// In ru, this message translates to:
  /// **'Модель на проверке (GLB 2.0 / PBR / Draco)…'**
  String get impValidating;

  /// No description provided for @impDone.
  ///
  /// In ru, this message translates to:
  /// **'Модель импортирована'**
  String get impDone;

  /// No description provided for @impName.
  ///
  /// In ru, this message translates to:
  /// **'Название'**
  String get impName;

  /// No description provided for @impCategory.
  ///
  /// In ru, this message translates to:
  /// **'Категория'**
  String get impCategory;

  /// No description provided for @impPickGlb.
  ///
  /// In ru, this message translates to:
  /// **'Выбрать .glb'**
  String get impPickGlb;

  /// No description provided for @impSize.
  ///
  /// In ru, this message translates to:
  /// **'Размер: {size}'**
  String impSize(String size);

  /// No description provided for @impImporting.
  ///
  /// In ru, this message translates to:
  /// **'Импорт…'**
  String get impImporting;

  /// No description provided for @impBtn.
  ///
  /// In ru, this message translates to:
  /// **'Импортировать'**
  String get impBtn;

  /// No description provided for @impFree.
  ///
  /// In ru, this message translates to:
  /// **'Импорт бесплатный'**
  String get impFree;

  /// No description provided for @impPriceLine.
  ///
  /// In ru, this message translates to:
  /// **'Стоимость импорта: {price} ₽ (списание с баланса компании)'**
  String impPriceLine(String price);

  /// No description provided for @balStatusAuto.
  ///
  /// In ru, this message translates to:
  /// **'Статус обновится автоматически'**
  String get balStatusAuto;

  /// No description provided for @balTransactions.
  ///
  /// In ru, this message translates to:
  /// **'Транзакции'**
  String get balTransactions;

  /// No description provided for @balTotalLine.
  ///
  /// In ru, this message translates to:
  /// **'Всего: {total}'**
  String balTotalLine(String total);

  /// No description provided for @balEmpty.
  ///
  /// In ru, this message translates to:
  /// **'Нет операций'**
  String get balEmpty;

  /// No description provided for @balSuccess.
  ///
  /// In ru, this message translates to:
  /// **'Успешно'**
  String get balSuccess;

  /// No description provided for @balEmployee.
  ///
  /// In ru, this message translates to:
  /// **'Сотрудник §8'**
  String get balEmployee;

  /// No description provided for @balAll.
  ///
  /// In ru, this message translates to:
  /// **'Все'**
  String get balAll;

  /// No description provided for @balThresholdInvalid.
  ///
  /// In ru, this message translates to:
  /// **'Укажите корректный порог'**
  String get balThresholdInvalid;

  /// No description provided for @balDevMock.
  ///
  /// In ru, this message translates to:
  /// **'Баланс: {balance} ₽'**
  String balDevMock(String balance);

  /// No description provided for @consentUpdatedTitle.
  ///
  /// In ru, this message translates to:
  /// **'Обновлены условия'**
  String get consentUpdatedTitle;

  /// No description provided for @consentAcceptAllSnackbar.
  ///
  /// In ru, this message translates to:
  /// **'Примите все обновлённые документы'**
  String get consentAcceptAllSnackbar;

  /// No description provided for @consentIntro.
  ///
  /// In ru, this message translates to:
  /// **'Для продолжения работы примите новые версии документов (§2.8).'**
  String get consentIntro;

  /// No description provided for @consentRead.
  ///
  /// In ru, this message translates to:
  /// **'Читать'**
  String get consentRead;

  /// No description provided for @consentHide.
  ///
  /// In ru, this message translates to:
  /// **'Скрыть текст'**
  String get consentHide;

  /// No description provided for @consentAccept.
  ///
  /// In ru, this message translates to:
  /// **'Принимаю'**
  String get consentAccept;

  /// No description provided for @consentContinue.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить'**
  String get consentContinue;

  /// No description provided for @consentDocVersion.
  ///
  /// In ru, this message translates to:
  /// **'{title} · v{version}'**
  String consentDocVersion(String title, String version);

  /// No description provided for @consentSaving.
  ///
  /// In ru, this message translates to:
  /// **'Сохранение…'**
  String get consentSaving;

  /// No description provided for @shootLinkTitle.
  ///
  /// In ru, this message translates to:
  /// **'Съёмка по ссылке'**
  String get shootLinkTitle;

  /// No description provided for @shootLinkCorpMode.
  ///
  /// In ru, this message translates to:
  /// **'Выберите корпоративный режим'**
  String get shootLinkCorpMode;

  /// No description provided for @shootLinkTier.
  ///
  /// In ru, this message translates to:
  /// **'Тариф'**
  String get shootLinkTier;

  /// No description provided for @shootLinkCreate.
  ///
  /// In ru, this message translates to:
  /// **'Создать ссылку и QR'**
  String get shootLinkCreate;

  /// No description provided for @shootLinkCopied.
  ///
  /// In ru, this message translates to:
  /// **'Ссылка скопирована'**
  String get shootLinkCopied;

  /// No description provided for @shootLinkCopy.
  ///
  /// In ru, this message translates to:
  /// **'Копировать'**
  String get shootLinkCopy;

  /// No description provided for @gdCameraRequired.
  ///
  /// In ru, this message translates to:
  /// **'Нужен доступ к камере'**
  String get gdCameraRequired;

  /// No description provided for @gdTurnToMarker.
  ///
  /// In ru, this message translates to:
  /// **'Поверните к AR-метке {azimuth}° / {elevation}°'**
  String gdTurnToMarker(String azimuth, String elevation);

  /// No description provided for @gdFpsWait.
  ///
  /// In ru, this message translates to:
  /// **'Подождите ({fps} FPS, энергосбережение)'**
  String gdFpsWait(String fps);

  /// No description provided for @gdAlignMarker.
  ///
  /// In ru, this message translates to:
  /// **'Совместите камеру с AR-меткой'**
  String get gdAlignMarker;

  /// No description provided for @ucDraftNotFound.
  ///
  /// In ru, this message translates to:
  /// **'Черновик съёмки не найден'**
  String get ucDraftNotFound;

  /// No description provided for @ucForbiddenCategory.
  ///
  /// In ru, this message translates to:
  /// **'Вы выбрали запрещённую категорию. Заказ будет отклонён без возврата средств.'**
  String get ucForbiddenCategory;

  /// No description provided for @ucNoViewFile.
  ///
  /// In ru, this message translates to:
  /// **'Нет файла ракурса {index}'**
  String ucNoViewFile(String index);

  /// No description provided for @gyroTiltDown.
  ///
  /// In ru, this message translates to:
  /// **'наклоните телефон вниз'**
  String get gyroTiltDown;

  /// No description provided for @gyroTiltUp.
  ///
  /// In ru, this message translates to:
  /// **'поднимите телефон'**
  String get gyroTiltUp;

  /// No description provided for @gyroTurnPitch.
  ///
  /// In ru, this message translates to:
  /// **'Поверните телефон: {dir} (~{pitch}°)'**
  String gyroTurnPitch(String dir, String pitch);

  /// No description provided for @gyroTurnDegrees.
  ///
  /// In ru, this message translates to:
  /// **'Поверните телефон примерно на {deg}° {dir}'**
  String gyroTurnDegrees(String deg, String dir);

  /// No description provided for @gyroLeft.
  ///
  /// In ru, this message translates to:
  /// **'влево'**
  String get gyroLeft;

  /// No description provided for @gyroRight.
  ///
  /// In ru, this message translates to:
  /// **'вправо'**
  String get gyroRight;

  /// No description provided for @qaBlur.
  ///
  /// In ru, this message translates to:
  /// **'размытие'**
  String get qaBlur;

  /// No description provided for @qaOffCenter.
  ///
  /// In ru, this message translates to:
  /// **'не по центру'**
  String get qaOffCenter;

  /// No description provided for @qaOverexposed.
  ///
  /// In ru, this message translates to:
  /// **'пересвет'**
  String get qaOverexposed;

  /// No description provided for @qaOk.
  ///
  /// In ru, this message translates to:
  /// **'ok'**
  String get qaOk;

  /// No description provided for @qaCenterPhone.
  ///
  /// In ru, this message translates to:
  /// **'Сместите телефон так, чтобы товар был в центре'**
  String get qaCenterPhone;

  /// No description provided for @qaCloser.
  ///
  /// In ru, this message translates to:
  /// **'Приблизьте телефон так, чтобы товар занимал ~70% экрана'**
  String get qaCloser;

  /// No description provided for @qaFarther.
  ///
  /// In ru, this message translates to:
  /// **'Отдалите телефон так, чтобы товар занимал ~70% экрана'**
  String get qaFarther;

  /// No description provided for @checkoutPromoApply.
  ///
  /// In ru, this message translates to:
  /// **'Применить'**
  String get checkoutPromoApply;

  /// No description provided for @checkoutPromoApplied.
  ///
  /// In ru, this message translates to:
  /// **'Скидка −{amount} ₽'**
  String checkoutPromoApplied(String amount);

  /// No description provided for @checkoutPromoInvalid.
  ///
  /// In ru, this message translates to:
  /// **'Промокод недействителен'**
  String get checkoutPromoInvalid;

  /// No description provided for @campaignBannerDismiss.
  ///
  /// In ru, this message translates to:
  /// **'Скрыть'**
  String get campaignBannerDismiss;

  /// No description provided for @campaignBannerCta.
  ///
  /// In ru, this message translates to:
  /// **'Подробнее'**
  String get campaignBannerCta;

  /// No description provided for @companyDefaultName.
  ///
  /// In ru, this message translates to:
  /// **'Компания'**
  String get companyDefaultName;

  /// No description provided for @paymentStatusPending.
  ///
  /// In ru, this message translates to:
  /// **'Ожидает оплаты'**
  String get paymentStatusPending;

  /// No description provided for @paymentStatusSucceeded.
  ///
  /// In ru, this message translates to:
  /// **'Оплачено'**
  String get paymentStatusSucceeded;

  /// No description provided for @paymentStatusCanceled.
  ///
  /// In ru, this message translates to:
  /// **'Отменено'**
  String get paymentStatusCanceled;

  /// No description provided for @draftRestoreTitle.
  ///
  /// In ru, this message translates to:
  /// **'Восстановить черновики?'**
  String get draftRestoreTitle;

  /// No description provided for @draftRestoreBody.
  ///
  /// In ru, this message translates to:
  /// **'Найдено {count} облачных бэкапов (TTL 7 дней, §3.3.2). Восстановить незавершённые съёмки?'**
  String draftRestoreBody(String count);

  /// No description provided for @draftRestoredSnackbar.
  ///
  /// In ru, this message translates to:
  /// **'Черновики восстановлены из облака'**
  String get draftRestoredSnackbar;

  /// No description provided for @resumeDraftTitle.
  ///
  /// In ru, this message translates to:
  /// **'Незавершённая съёмка'**
  String get resumeDraftTitle;

  /// No description provided for @resumeDraftBody.
  ///
  /// In ru, this message translates to:
  /// **'У вас есть черновик ({category}, {count}/{total} кадров). Продолжить или начать заново?'**
  String resumeDraftBody(String category, String count, String total);

  /// No description provided for @resumeDraftDiscard.
  ///
  /// In ru, this message translates to:
  /// **'Заново'**
  String get resumeDraftDiscard;

  /// No description provided for @resumeDraftContinue.
  ///
  /// In ru, this message translates to:
  /// **'Продолжить'**
  String get resumeDraftContinue;

  /// No description provided for @mvSearchHint.
  ///
  /// In ru, this message translates to:
  /// **'Поиск по названию'**
  String get mvSearchHint;

  /// No description provided for @mvFilterTierAll.
  ///
  /// In ru, this message translates to:
  /// **'Все тарифы'**
  String get mvFilterTierAll;

  /// No description provided for @mvFilterAuthorAll.
  ///
  /// In ru, this message translates to:
  /// **'Все авторы'**
  String get mvFilterAuthorAll;

  /// No description provided for @mvFilterAuthor.
  ///
  /// In ru, this message translates to:
  /// **'Автор'**
  String get mvFilterAuthor;

  /// No description provided for @mvClearDates.
  ///
  /// In ru, this message translates to:
  /// **'Сбросить даты'**
  String get mvClearDates;

  /// No description provided for @balancePresetsLabel.
  ///
  /// In ru, this message translates to:
  /// **'Сохранённые представления'**
  String get balancePresetsLabel;

  /// No description provided for @balanceSavePreset.
  ///
  /// In ru, this message translates to:
  /// **'Сохранить как…'**
  String get balanceSavePreset;

  /// No description provided for @balancePresetNameHint.
  ///
  /// In ru, this message translates to:
  /// **'Название представления'**
  String get balancePresetNameHint;

  /// No description provided for @balancePresetSaved.
  ///
  /// In ru, this message translates to:
  /// **'Представление сохранено'**
  String get balancePresetSaved;

  /// No description provided for @balancePresetDeleted.
  ///
  /// In ru, this message translates to:
  /// **'Представление удалено'**
  String get balancePresetDeleted;

  /// No description provided for @balanceApplyPreset.
  ///
  /// In ru, this message translates to:
  /// **'Применить'**
  String get balanceApplyPreset;

  /// No description provided for @profileSessionsSection.
  ///
  /// In ru, this message translates to:
  /// **'Активные сессии §19.14.4'**
  String get profileSessionsSection;

  /// No description provided for @profileSessionRevoke.
  ///
  /// In ru, this message translates to:
  /// **'Завершить'**
  String get profileSessionRevoke;

  /// No description provided for @profileSessionsRevokeOthers.
  ///
  /// In ru, this message translates to:
  /// **'Завершить другие сессии'**
  String get profileSessionsRevokeOthers;

  /// No description provided for @profileSessionsRevokeOthersDone.
  ///
  /// In ru, this message translates to:
  /// **'Другие сессии завершены'**
  String get profileSessionsRevokeOthersDone;

  /// No description provided for @profileSessionsEmpty.
  ///
  /// In ru, this message translates to:
  /// **'Нет других активных сессий'**
  String get profileSessionsEmpty;

  /// No description provided for @profileDisable2fa.
  ///
  /// In ru, this message translates to:
  /// **'Отключить 2FA'**
  String get profileDisable2fa;

  /// No description provided for @profileDisable2faTitle.
  ///
  /// In ru, this message translates to:
  /// **'Отключить 2FA?'**
  String get profileDisable2faTitle;

  /// No description provided for @profileDisable2faBody.
  ///
  /// In ru, this message translates to:
  /// **'Введите код из приложения-аутентификатора для подтверждения.'**
  String get profileDisable2faBody;

  /// No description provided for @profile2faDisabledSnackbar.
  ///
  /// In ru, this message translates to:
  /// **'2FA отключена'**
  String get profile2faDisabledSnackbar;

  /// No description provided for @mvApiUploadTitle.
  ///
  /// In ru, this message translates to:
  /// **'Загрузка через API'**
  String get mvApiUploadTitle;

  /// No description provided for @mvApiSkuLabel.
  ///
  /// In ru, this message translates to:
  /// **'SKU'**
  String get mvApiSkuLabel;

  /// No description provided for @mvApiUploadBtn.
  ///
  /// In ru, this message translates to:
  /// **'Загрузка API'**
  String get mvApiUploadBtn;

  /// No description provided for @mvLoadMore.
  ///
  /// In ru, this message translates to:
  /// **'Загрузить ещё'**
  String get mvLoadMore;
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
