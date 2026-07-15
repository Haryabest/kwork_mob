// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'KWork Mob';

  @override
  String get authTitle => 'Sign in';

  @override
  String get email => 'Email';

  @override
  String get password => 'Password';

  @override
  String get login => 'Sign in';

  @override
  String get register => 'Sign up';

  @override
  String get forgotPassword => 'Forgot password?';

  @override
  String get home => 'Home';

  @override
  String get models => 'Models';

  @override
  String get orders => 'Orders';

  @override
  String get support => 'Support';

  @override
  String get profile => 'Profile';

  @override
  String get shoot => 'Shoot product';

  @override
  String get queue => 'Queue';

  @override
  String get faq => 'FAQ';

  @override
  String get personalMode => 'Personal';

  @override
  String get corporateMode => 'Company';

  @override
  String get onboarding1 => 'Capture the product from 12 angles';

  @override
  String get onboarding2 => 'Pay the tariff and wait for generation';

  @override
  String get onboarding3 => 'Download .glb / .usdz for the marketplace';

  @override
  String get onboarding4 => 'Publish the model on WB or Ozon';

  @override
  String get onboardingSub1 =>
      '12 Guided Dome angles → 3D model for marketplaces';

  @override
  String get onboardingSub2 =>
      'ARKit / ARCore or gyroscope guides ±15° angles. For 1:1 scale — calibrate with a card or A4 in profile.';

  @override
  String get onboardingSub3 =>
      'Download GLB/USDZ and publish on Wildberries or Ozon';

  @override
  String get onboardingSub4 =>
      'Above 40°C shooting switches to power saving (15 FPS)';

  @override
  String get skip => 'Skip';

  @override
  String get alreadyHaveAccount => 'Already have an account? Sign in';

  @override
  String get continueBtn => 'Continue';

  @override
  String get errorNetwork => 'No internet connection';

  @override
  String get comingSoon => 'Screen under development';

  @override
  String get save => 'Save';

  @override
  String get cancel => 'Cancel';

  @override
  String get confirm => 'Confirm';

  @override
  String get done => 'Done';

  @override
  String get account => 'Account';

  @override
  String get langRu => 'Русский';

  @override
  String get langEn => 'English';

  @override
  String get langKk => 'Қазақша';

  @override
  String get langZh => '中文';

  @override
  String get companyTopupTitle => 'Company balance';

  @override
  String get companyTopupSubtitle => 'Top up account · §19.14.2';

  @override
  String get companyPoliciesTitle => 'Company policies';

  @override
  String get companyPoliciesSubtitle => 'Access and notifications · §19.14.2';

  @override
  String companyBalanceLabel(String balance) {
    return 'Company balance: $balance ₽';
  }

  @override
  String get policiesMaxConcurrent => 'Default concurrent order limit';

  @override
  String get policiesNoMonthlyLimit => 'No monthly spending limit';

  @override
  String get policiesMonthlyLimit => 'Monthly spending limit (₽)';

  @override
  String get policiesAllowedCategories => 'Allowed categories';

  @override
  String get policiesAllowDownload => 'Photographer can download models';

  @override
  String get policiesAllowLinks => 'Photographer can add publication links';

  @override
  String get policiesRequire2fa => 'Require 2FA for all members';

  @override
  String get policiesAutoBlock => 'Auto-block after inactivity (days)';

  @override
  String get policiesLowBalanceThreshold => 'Low balance threshold (₽)';

  @override
  String get policiesNotifySection => 'Owner notifications (§3.19)';

  @override
  String get policiesNotifyHint => 'Who receives push/email for company events';

  @override
  String get policiesSaved => 'Policies saved';

  @override
  String get policiesInvalidConcurrent => 'Enter order limit between 1 and 20';

  @override
  String get policiesInvalidAutoBlock => 'Enter a valid auto-block period';

  @override
  String get policiesInvalidThreshold => 'Enter a valid balance threshold';

  @override
  String get policiesInvalidMonthly => 'Enter a valid monthly limit';

  @override
  String get notifyGenerationDone => 'Generation completed';

  @override
  String get notifyPhotographerUploaded => 'Photographer uploaded photos';

  @override
  String get notifySourceExpire => 'Cloud copy expiring';

  @override
  String get notifyLowBalance => 'Low company balance';

  @override
  String get audienceOwnerOnly => 'Owner only';

  @override
  String get audienceOwnerManager => 'Owner + Manager';

  @override
  String get audienceAll => 'All members';

  @override
  String get balanceTitle => 'Balance';

  @override
  String get balanceCompanyTitle => 'Company balance';

  @override
  String get balanceUnavailable => 'Balance is not available for your role';

  @override
  String lowBalanceBanner(String balance, String threshold) {
    return 'Low company balance: $balance ₽ (threshold $threshold ₽). Top up §20.3.5';
  }

  @override
  String get topup => 'Top up';

  @override
  String get topupMinAmount => 'Minimum 100 ₽';

  @override
  String get balanceTopupSuccess => 'Balance topped up';

  @override
  String get companyTopupSuccess => 'Company balance topped up';

  @override
  String get paymentCanceled => 'Payment canceled';

  @override
  String get lowBalanceThreshold => 'Low balance threshold, ₽ §20.3.5';

  @override
  String get saveThreshold => 'Save threshold';

  @override
  String get thresholdSaved => 'Low balance threshold saved §20.3.5';

  @override
  String get topupCompanyBtn => 'Top up company balance §19.14.2';

  @override
  String get topupAmount => 'Top-up amount';

  @override
  String get topupCompanyAmount => 'Company top-up §19.14.2';

  @override
  String get topupCard => 'Pay by card';

  @override
  String get topupSbpQr => 'SBP QR';

  @override
  String get sbpQrTitle => 'SBP — scan QR code';

  @override
  String get sbpAutoStatus => 'Status updates automatically';

  @override
  String get copyPayload => 'Copy payload';

  @override
  String get dateFrom => 'Date from';

  @override
  String get dateTo => 'Date to';

  @override
  String get txTypeLabel => 'Transaction type';

  @override
  String get txTypeAll => 'All';

  @override
  String get txTypeTopup => 'Top-ups';

  @override
  String get txTypeCharge => 'Charges';

  @override
  String get txTypeRefund => 'Refunds';

  @override
  String get perPage => 'Per page §20.3.4';

  @override
  String get applyFilters => 'Apply filters';

  @override
  String get exportCsv => 'Export CSV §20.3.4';

  @override
  String get exporting => 'Exporting…';

  @override
  String get companyTopupScreenTitle => 'Company top-up';

  @override
  String get companyTopupScreenHint =>
      'Owner: top up corporate account via YooKassa §19.14.2';

  @override
  String get languageInterface => 'Interface language';

  @override
  String get team => 'Team';

  @override
  String get switchMode => 'Personal / Company mode';

  @override
  String get localStorage => 'Local storage';

  @override
  String get localStorageSub => 'GLB, auto cleanup, ZIP export';

  @override
  String get calibration => 'Scale calibration';

  @override
  String get calibrationSub => 'Card / A4 / QR · §3.7';

  @override
  String get importModel => 'Import model';

  @override
  String get importModelSub => 'Ready GLB · §6.10';

  @override
  String get saveProfile => 'Save profile';

  @override
  String get profileSaved => 'Profile saved';

  @override
  String balanceLabel(String amount) {
    return 'Balance: $amount ₽';
  }
}
