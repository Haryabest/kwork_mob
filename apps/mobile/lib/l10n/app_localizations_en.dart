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

  @override
  String get exportShareText => 'Transactions §20.3.4';

  @override
  String get exportSuccess => 'CSV exported';

  @override
  String get open => 'Open';

  @override
  String get notificationDefault => 'Notification';

  @override
  String get authCreateAccount => 'Create an account';

  @override
  String get authVerifyEmail => 'Email verification';

  @override
  String get authAccountType => 'Account type';

  @override
  String get authForgotPasswordTitle => 'Password recovery';

  @override
  String get authNewPasswordTitle => 'New password';

  @override
  String get authTwoFaTitle => 'Enter 2FA code';

  @override
  String get authSendLink => 'Send link';

  @override
  String get authSavePassword => 'Save password';

  @override
  String get authRememberMe => 'Remember me';

  @override
  String get authPasswordConfirm => 'Confirm password';

  @override
  String get authConsents =>
      'I accept the agreement, privacy policy, offer, rights confirmation and prohibited content rules';

  @override
  String get authEmailCode => 'Code from email (6 digits)';

  @override
  String get authIndividual => 'Individual';

  @override
  String get authLegal => 'Legal entity / sole proprietor';

  @override
  String get authFullNameOptional => 'Full name (optional)';

  @override
  String get authOrgName => 'Organization name';

  @override
  String get authInn => 'TIN';

  @override
  String get authOgrn => 'OGRN / OGRNIP';

  @override
  String get authLegalAddress => 'Legal address';

  @override
  String get authDirectorName => 'Director full name';

  @override
  String get authBankName => 'Bank';

  @override
  String get authBik => 'BIC';

  @override
  String get authCheckingAccount => 'Checking account';

  @override
  String get authResetToken => 'Token from email';

  @override
  String get authNewPasswordField => 'New password';

  @override
  String get authAuthenticatorCode => 'Authenticator code';

  @override
  String get authBack => 'Back';

  @override
  String get authBackToLogin => 'Back to sign in';

  @override
  String get authAcceptTerms => 'Accept the terms of service';

  @override
  String get authPasswordUpdated =>
      'Password updated. Sign in with your new password';

  @override
  String authDevCode(String code) {
    return 'Dev code: $code';
  }

  @override
  String authDevToken(String token) {
    return 'Dev token: $token';
  }

  @override
  String get shootCategoryTitle => 'Product category';

  @override
  String get shootCategoryLabel => 'Category';

  @override
  String get shootForbiddenCategories => 'Forbidden categories';

  @override
  String get shootForbiddenHint =>
      'If selected — order is not created and funds are not charged';

  @override
  String get shootAgeConfirmed => 'Age verified';

  @override
  String get shootAgeConfirmedSub => 'No need to enter date again';

  @override
  String get shootBirthDate => 'Date of birth (YYYY-MM-DD)';

  @override
  String get shootBirthDateHint =>
      'Saved to profile after successful verification';

  @override
  String get shootScaleRequired => 'Scale (m) — required for furniture';

  @override
  String get shootCalibrationBtn => 'Calibration: card / A4 / QR (§3.7)';

  @override
  String get shootLength => 'Length';

  @override
  String get shootWidth => 'Width';

  @override
  String get shootHeight => 'Height';

  @override
  String get shootModelName => 'Model name (optional)';

  @override
  String get shootModelNameHint => 'e.g. Nike Air sneakers';

  @override
  String get shootTier => 'Tariff';

  @override
  String get shootGhostMeshHint => 'Ghost Mesh — pinch to scale';

  @override
  String get shootNext => 'Continue to shoot';

  @override
  String get shootAgeConfirmTitle => 'Confirm you are 18+';

  @override
  String get shootAgeConfirmBody => 'Enter date of birth (YYYY-MM-DD).';

  @override
  String get shootInvalidDate => 'Invalid date (YYYY-MM-DD)';

  @override
  String get shootAgeOnly18 => 'Model creation is available from age 18 only';

  @override
  String get shootBirthRequired => 'Enter date of birth for 18+';

  @override
  String get shootForbiddenTitle => 'Forbidden category';

  @override
  String get shootForbiddenBody =>
      'You selected a forbidden category. The order will be rejected without refund. Continue?';

  @override
  String get shootOrderBlocked => 'Order will not be created — change category';

  @override
  String shootStorageFree(String need, String free) {
    return 'Free up phone storage (need $need MB, ~$free MB available)';
  }

  @override
  String shootStorageFreeUnknown(String need) {
    return 'Free up phone storage (need $need MB)';
  }

  @override
  String get shootQualityTitle => 'Quality check';

  @override
  String get shootQualityLow =>
      'Low photo quality. Try to improve shooting conditions';

  @override
  String get shootQualityLowTitle => 'Low quality';

  @override
  String get shootQualityLowDialog =>
      'Some frames have low quality, which may result in a defective model. Continue?';

  @override
  String get yes => 'Yes';

  @override
  String get no => 'No';

  @override
  String get shootQualityContinue => 'Continue to upload';

  @override
  String get shootQualityContinueForce => 'Continue despite errors';

  @override
  String get shootQualityRestart => 'Restart shoot from beginning';

  @override
  String shootArHint(String tier, String scale) {
    return 'AR: tariff «$tier», dimensions $scale';
  }

  @override
  String get shootTitle => 'Shoot';

  @override
  String get shootOverheatTitle => 'Phone overheating';

  @override
  String shootOverheatBody(String temp) {
    return 'Battery temperature ≈ $temp°C (>45°C). We recommend stopping until cooled. Continuing enables power saving (15 FPS).';
  }

  @override
  String get shootAbort => 'Stop';

  @override
  String get shootExit => 'Exit';

  @override
  String get shootCalibrateShort => 'Cal.';

  @override
  String get shootArCameraActive => 'AR camera active';

  @override
  String shootAngleLine(
    String current,
    String total,
    String label,
    String backend,
  ) {
    return 'Angle $current/$total · $label · $backend';
  }

  @override
  String get uploadPhotoTitle => 'Photo upload';

  @override
  String get uploadPreparing => 'Preparing…';

  @override
  String uploadResumeFound(String done) {
    return 'Incomplete upload found ($done/12)';
  }

  @override
  String get uploadResumeHint =>
      '§3.4.1: progress saved locally. Upload resumes from the last photo after disconnect.';

  @override
  String get uploadBuildingZip => 'Building ZIP + SHA-256…';

  @override
  String uploadSha256(String hash) {
    return 'SHA-256: $hash…';
  }

  @override
  String get uploadPresigned => 'Getting presigned URLs…';

  @override
  String get uploadEncrypting => 'E2E photo encryption…';

  @override
  String uploadProgress(String current, String total) {
    return 'Uploading $current/$total…';
  }

  @override
  String uploadUploaded(String done) {
    return 'Uploaded $done/12';
  }

  @override
  String get uploadInterrupted => 'Upload interrupted — you can continue';

  @override
  String get uploadUploading => 'Uploading…';

  @override
  String get uploadContinue => 'Continue upload';

  @override
  String get upload12Photos => 'Upload 12 photos';

  @override
  String get checkoutTitle => 'Payment';

  @override
  String get checkoutPayTitle => 'Order payment';

  @override
  String get checkoutSubmitGeneration => 'Submit for generation';

  @override
  String get checkoutNeedCalibration => 'Calibration required';

  @override
  String get checkoutCalibrationBody =>
      'For 1:1 scale, calibrate with card, A4 or QR (§3.7).';

  @override
  String get checkoutCalibrate => 'Calibrate';

  @override
  String checkoutCategory(String label) {
    return 'Category: $label';
  }

  @override
  String checkoutTier(String label) {
    return 'Tariff: $label';
  }

  @override
  String checkoutBasePrice(String amount) {
    return 'Base price: $amount ₽';
  }

  @override
  String get checkoutUpsells => 'Add-on services';

  @override
  String checkoutTotal(String amount) {
    return 'Total: $amount ₽';
  }

  @override
  String get checkoutPromo => 'Promo code';

  @override
  String get checkoutFioOptional => 'Full name (optional)';

  @override
  String get checkoutFioHint => 'Can be skipped';

  @override
  String get checkoutFioTaxHint => 'Name is used for My Tax receipt (§19.8.1)';

  @override
  String get checkoutPayCard => 'Pay by card';

  @override
  String get checkoutPaySbp => 'Pay via SBP (QR)';

  @override
  String get checkoutSbpOrderTitle => 'SBP — order payment';

  @override
  String get guestShootTitle => 'Shoot via link';

  @override
  String guestTask(String id) {
    return 'Task $id…';
  }

  @override
  String guestMeta(String category, String tier) {
    return 'Category: $category · tariff: $tier';
  }

  @override
  String get guestHint => 'Guest mode: 12 angles via AR or gallery (§3.15).';

  @override
  String get guestStartAr => 'Start AR shoot';

  @override
  String get guestGallery12 => '12 photos from gallery';

  @override
  String guestPhotosRequired(String need, String selected) {
    return 'Exactly $need photos required (selected $selected)';
  }

  @override
  String get guestUploadTitle => 'Send via link';

  @override
  String get guestReadyToSend => 'Ready to send';

  @override
  String get guestGettingUrls => 'Getting upload URLs…';

  @override
  String guestUploading(String current) {
    return 'Uploading $current/12…';
  }

  @override
  String get guestConfirming => 'Confirming…';

  @override
  String get guestSentToOwner => 'Photos sent to owner';

  @override
  String get guestSend12Photos => 'Send 12 photos';

  @override
  String get guestLinkUsed => 'Link used. Company owner will be notified.';

  @override
  String get prefTopupFailed => 'Top-up failed';

  @override
  String homePendingUploadTitle(String uploaded, String total) {
    return 'Incomplete photo upload ($uploaded/$total)';
  }

  @override
  String get homePendingUploadHint =>
      'Upload was interrupted. You can continue from the last frame.';

  @override
  String homeModePrefix(String mode) {
    return 'Mode: $mode';
  }

  @override
  String get homeNoCompanies => 'No linked companies';

  @override
  String get homeSwitchModeTitle => 'Switch mode?';

  @override
  String get homeSwitchModeBody => 'Confirm switching Personal / Company';

  @override
  String get homeShootLinkQr => 'Shoot via link (QR)';

  @override
  String get ordersExecutorFilter => 'Assignee §3.16.2';

  @override
  String get ordersAllMembers => 'All team members';

  @override
  String get ordersEmpty => 'No orders';

  @override
  String get orderStatusPending => 'New';

  @override
  String get orderStatusAwaitingPayment => 'Awaiting payment';

  @override
  String get orderStatusQueued => 'Queued';

  @override
  String get orderStatusProcessing => 'Processing';

  @override
  String get orderStatusCompleted => 'Ready';

  @override
  String get orderStatusFailed => 'Error';

  @override
  String get orderStatusCancelled => 'Cancelled';

  @override
  String get orderStatusPaid => 'Paid';

  @override
  String get orderStatusBlockedNsfw => 'NSFW block';

  @override
  String get notificationsTitle => 'Notifications';

  @override
  String get notificationsEmpty => 'No notifications';

  @override
  String get queueGenerationTitle => 'Model generation';

  @override
  String get queueCancelTitle => 'Cancel generation';

  @override
  String get queueCancelWarning =>
      'Warning! Cancelling during generation does not refund your payment, as the compute resources have already been used. Cancel anyway?';

  @override
  String get queueUnderstand => 'I understand';

  @override
  String get queueReconnectWs => 'Reconnect WebSocket';

  @override
  String get queueNsfwBlocked =>
      'Order blocked: NSFW in imported textures. Funds returned to the company balance. Account under manual review for up to 24h (§10.8).';

  @override
  String queueStatus(String status) {
    return 'Status: $status';
  }

  @override
  String queuePosition(String pos, String ewt) {
    return 'Queue position: $pos. Estimated wait time: $ewt min';
  }

  @override
  String get queueWsConnected => 'WebSocket: connected';

  @override
  String get queueWsErrorShort => 'WebSocket: error';

  @override
  String get queueWsConnecting => 'WebSocket: …';

  @override
  String get queueRefresh => 'Refresh';

  @override
  String get queueCancelOrder => 'Cancel';

  @override
  String get faqSupportTitle => 'FAQ / Support';

  @override
  String get faqTab => 'FAQ';

  @override
  String get faqMyTickets => 'My tickets';

  @override
  String faqLoadError(String error) {
    return 'Loading error: $error';
  }

  @override
  String get faqQuestionMin => 'Question: at least 10 characters';

  @override
  String get faqDefaultSubject => 'Question from the app';

  @override
  String get faqQuestionSent => 'Question sent';

  @override
  String get faqEmpty => 'No FAQ items yet';

  @override
  String get faqAskPrompt => 'Didn\'t find an answer? Ask a question';

  @override
  String get faqSubjectOptional => 'Subject (optional)';

  @override
  String get faqYourQuestion => 'Your question';

  @override
  String get faqSending => 'Sending…';

  @override
  String get faqSend => 'Send';

  @override
  String get faqNoTickets => 'No tickets';

  @override
  String faqTicketDefault(String id) {
    return 'Ticket #$id';
  }

  @override
  String get faqSupportRole => 'Support';

  @override
  String get faqYouRole => 'You';

  @override
  String get faqClarifyHint => 'Clarifying question…';

  @override
  String get faqReply => 'Reply';

  @override
  String get faqClose => 'Close';

  @override
  String get faqTicketClosed => 'Ticket closed';

  @override
  String get teamTitle => 'Team';

  @override
  String get teamNoAccess => 'No access to the team';

  @override
  String get teamMembers => 'Members';

  @override
  String get teamNoMembers => 'No members';

  @override
  String get teamInvite => 'Invite';

  @override
  String get teamAudit => 'Audit';

  @override
  String get teamNoAudit => 'No audit records';

  @override
  String get teamExtendAllTitle => 'Extend all sources';

  @override
  String get teamExtendAllBody =>
      'Extend cloud source storage for all company models by 30 days. Limit — 3 extensions per model (§9.1.2).';

  @override
  String get teamExtend => 'Extend';

  @override
  String get teamExtendAllBtn => 'Extend all sources §9.1.2';

  @override
  String get teamMemberFallback => 'Member';

  @override
  String get teamRole => 'Role';

  @override
  String get teamActiveOrdersLimit => 'Active orders limit';

  @override
  String get teamInviteSent => 'Invitation sent';

  @override
  String get teamInviteSentWithLink => 'Invitation sent · link copied';

  @override
  String teamMemberSubtitle(String role, String limit) {
    return '$role · limit $limit orders';
  }

  @override
  String teamCompany(String id) {
    return 'Company #$id';
  }

  @override
  String get teamSendInvite => 'Send invitation';

  @override
  String get mvPublishValidating => 'Import validating';

  @override
  String get mvPublishImported => 'Imported';

  @override
  String get mvPublishImportFailed => 'Import failed';

  @override
  String get mvPublishNotPublished => 'Not published';

  @override
  String get mvPublishVerified => 'Verified';

  @override
  String get mvPublishPublished => 'Published';

  @override
  String get mvRenameTitle => 'Rename model';

  @override
  String get mvNameLabel => 'Name';

  @override
  String get mvLinkCopied => 'Link copied';

  @override
  String get mvMovedToTrash => 'Model moved to trash';

  @override
  String get mvRetry => 'Retry';

  @override
  String get mvNoModels => 'No models yet';

  @override
  String get mvTitle => 'Models';

  @override
  String get mvTrash => 'Trash';

  @override
  String get mvFilterAll => 'All';

  @override
  String get mvFilterFavorites => 'Favorites';

  @override
  String get mvSortNewest => 'Newest first';

  @override
  String get mvSortOldest => 'Oldest first';

  @override
  String get mvNoModelsFilter => 'No models for this filter';

  @override
  String get mvDownloadGlbOzon => 'Download .glb (Ozon)';

  @override
  String get mvDownloadUsdzWb => 'Download .usdz (Wildberries)';

  @override
  String get mvShare => 'Share';

  @override
  String get mvRate => 'Rate model';

  @override
  String get mvVerifyLink => 'Verification link';

  @override
  String get mvEdit => 'Edit';

  @override
  String get mvRename => 'Rename';

  @override
  String get mvDelete => 'Delete';

  @override
  String mvLinkCopiedMarketplace(String mp) {
    return '$mp link copied';
  }

  @override
  String mvGlbSaved(String path) {
    return 'GLB saved: $path';
  }

  @override
  String get mvPublicLinkTitle => 'Public link §3.12';

  @override
  String mvUntil(String date) {
    return 'Until: $date';
  }

  @override
  String get mvNoLocalPhotosTitle => 'No local photos';

  @override
  String get mvNoLocalPhotosBody =>
      'Regeneration requires 12 source photos on the device. Restore from cloud or reshoot?';

  @override
  String get mvRestore => 'Restore';

  @override
  String get mvCantDetectCategory => 'Could not detect category/tier';

  @override
  String get mvStorageExtended => 'Storage extended';

  @override
  String get mvDeleteTitle => 'Delete model?';

  @override
  String get mvDeleteBody =>
      'Source photos and the model will be moved to trash for 30 days. Continue?';

  @override
  String get mvInTrash => 'In trash';

  @override
  String get mvSourcesRestored => 'Sources restored';

  @override
  String get mvCardLinkTitle => 'Product card link';

  @override
  String get mvCardLinkHint => 'https://www.wildberries.ru/... or ozon.ru/...';

  @override
  String get mvAdd => 'Add';

  @override
  String mvLinkStatus(String status) {
    return 'Link: $status';
  }

  @override
  String get mvRateTitle => 'Rate the model quality from 1 to 5';

  @override
  String get mvWhatsWrong => 'What\'s wrong?';

  @override
  String get mvReasonBlurry => 'blurry textures';

  @override
  String get mvReasonHoles => 'holes or artifacts';

  @override
  String get mvReasonScale => 'wrong scale';

  @override
  String get mvReasonColor => 'wrong color / lighting';

  @override
  String get mvReasonOther => 'other';

  @override
  String get mvComment => 'Comment';

  @override
  String get mvLater => 'Later';

  @override
  String get mvModelTitle => '3D model';

  @override
  String get mvGlbNotReady => 'GLB not ready yet';

  @override
  String mvCloud(String days, String used, String max) {
    return 'Cloud: $days days · extensions $used/$max';
  }

  @override
  String get mvLocalGlbSaved => 'Local GLB saved';

  @override
  String get mvRegenerate => 'Regenerate';

  @override
  String get mvUpdateGlb => 'Update GLB';

  @override
  String get mvGlbLocal => 'GLB local';

  @override
  String get mvDownloadWb => 'Download WB';

  @override
  String get mvDownloadOzon => 'Download Ozon';

  @override
  String get mvSources => 'Sources';

  @override
  String get mvExtend30 => '+30 days';

  @override
  String get mvToTrash => 'To trash';

  @override
  String get mvLink => 'Link';

  @override
  String get mvImOnWb => 'I\'m on WB';

  @override
  String get mvImOnOzon => 'I\'m on Ozon';

  @override
  String mvApiResult(String status) {
    return 'API: $status';
  }

  @override
  String get orderLimitTitle => 'Active order limit';

  @override
  String get orderLimitBody =>
      'You reached the concurrent order limit for your role. Wait for current generations to finish or contact the Owner.';

  @override
  String get orderLimitOk => 'OK';

  @override
  String get trashTitle => 'Trash';

  @override
  String get trashEmpty =>
      'Trash is empty\nDeleted models are kept for 30 days';

  @override
  String get trashRestore => 'Restore';

  @override
  String get trashRestored => 'Restored';

  @override
  String trashOrderLine(String id, String date) {
    return 'Order #$id · trashed $date';
  }

  @override
  String trashPurgeLine(String date) {
    return 'Purge: $date';
  }

  @override
  String get prefPushEnabled => 'Push notifications';

  @override
  String get prefEmailEnabled => 'Email notifications';

  @override
  String get prefGenerationDone => 'Generation complete';

  @override
  String get prefRefund => 'Refund';

  @override
  String get prefNsfwBlocked => 'NSFW block';

  @override
  String get prefSourceExpire => 'Source expiry';

  @override
  String get prefCleanup => 'Storage cleanup';

  @override
  String get prefPublishReminder => 'Publish reminder';

  @override
  String get prefSupportReply => 'Support reply';

  @override
  String get profileInnLabel => 'Tax ID (optional) §19.14.1';

  @override
  String get profilePhoneLabel => 'Phone (optional) §19.14.1';

  @override
  String get profileFullNameLabel => 'Full name (optional) §19.14.1';

  @override
  String get profileExportFormat => 'Export format §19.14.3';

  @override
  String get profileExportGlb => '.glb (Ozon / universal)';

  @override
  String get profileExportUsdz => '.usdz (Wildberries / AR)';

  @override
  String get profileTheme => 'Theme §19.14.3';

  @override
  String get themeSystem => 'System';

  @override
  String get themeLight => 'Light';

  @override
  String get themeDark => 'Dark';

  @override
  String get profileLanguage => 'Language';

  @override
  String get profileNotificationsSection => 'Notifications §19.14.3';

  @override
  String get profileEventsSection => 'Events §3.4.3';

  @override
  String get profileSecuritySection => 'Security §19.14.4';

  @override
  String get profileChangePassword => 'Change password';

  @override
  String get profileChangePasswordTitle => 'Change password';

  @override
  String get profileCurrentPassword => 'Current password';

  @override
  String get profileNewPassword => 'New password';

  @override
  String get profilePasswordConfirm => 'Confirm';

  @override
  String get profilePasswordChanged => 'Password changed';

  @override
  String get profileMinPassword => 'At least 8 characters';

  @override
  String get profilePasswordMismatch => 'Passwords do not match';

  @override
  String get profile2faSection => 'Two-factor authentication §19.14.4';

  @override
  String get profile2faEnabled => '2FA enabled';

  @override
  String get profile2faDisabled => '2FA disabled';

  @override
  String get profile2faOwnerRequired => '2FA is required for Owner (§10.7.5)';

  @override
  String get profile2faActiveHint =>
      'TOTP active — Google Authenticator, 1Password, etc.';

  @override
  String get profile2faStep1 => '1. Scan QR in your authenticator app';

  @override
  String get profile2faStep2 => '2. Or enter the secret manually';

  @override
  String get profileSecretCopied => 'Secret copied';

  @override
  String get profile2faCodeLabel => 'Authenticator code';

  @override
  String get profileConfirm2fa => 'Confirm 2FA';

  @override
  String get profileEnable2fa => 'Enable 2FA';

  @override
  String get profile2faEnabledSnackbar => '2FA enabled';

  @override
  String get profileDeleteAccountTitle => 'Delete account?';

  @override
  String get profileDeleteAccountBody =>
      'All models and personal data will be deleted within 30 days (§2.8.3). Financial records are anonymized and kept for 5 years.';

  @override
  String get profileDeleteAccountBtn => 'Delete';

  @override
  String get profileDeleteRequestAccepted => 'Request accepted';

  @override
  String get notifGenDoneTitle => 'Generation complete';

  @override
  String notifGenDoneBody(String id) {
    return 'Order #$id is ready';
  }

  @override
  String get notifNsfwTitle => 'NSFW blocked';

  @override
  String notifNsfwBody(String id) {
    return 'Order #$id rejected. Funds refunded. Account under review up to 24h.';
  }

  @override
  String get notifGenFailedTitle => 'Generation failed';

  @override
  String notifGenFailedBody(String id) {
    return 'Order #$id failed';
  }

  @override
  String get notifRefundTitle => 'Refund';

  @override
  String notifRefundBody(String id) {
    return 'Order #$id refunded';
  }

  @override
  String get notifCancelledTitle => 'Order cancelled';

  @override
  String notifCancelledBody(String id) {
    return 'Order #$id cancelled';
  }

  @override
  String get notifCompanyInviteTitle => 'Company invite';

  @override
  String get publishGuideTitle => 'How to publish';

  @override
  String get publishGuideIntro =>
      'Download model files and upload them to your marketplace product card.';

  @override
  String get publishGuideWbTitle => 'Wildberries';

  @override
  String get publishGuideWb1 =>
      '1. Download .usdz (Download WB button in the model).';

  @override
  String get publishGuideWb2 =>
      '2. Open product card in WB seller → media → 3D.';

  @override
  String get publishGuideWb3 => '3. Upload .usdz for iOS buyers.';

  @override
  String get publishGuideOzonTitle => 'Ozon';

  @override
  String get publishGuideOzon1 => '1. Download .glb (Download Ozon button).';

  @override
  String get publishGuideOzon2 =>
      '2. In Ozon seller open product card → 3D model.';

  @override
  String get publishGuideOzon3 => '3. Upload .glb for Android buyers.';

  @override
  String get publishGuideOpenModels => 'Go to models';

  @override
  String get apiKeysTitle => 'API keys';

  @override
  String get apiKeysSubtitle => 'Owner · scopes · rate limit';

  @override
  String get apiKeysCreate => 'Create key';

  @override
  String get apiKeysRevoke => 'Revoke';

  @override
  String get apiKeysCopyOnce => 'Copy the key — it won\'t be shown again';

  @override
  String get apiKeysName => 'Name';

  @override
  String get apiKeysEmpty => 'No keys';

  @override
  String get apiKeysCreated => 'Key created';

  @override
  String get profileCopySecretBtn => 'Copy secret';

  @override
  String get profile2faCodeStep => '3. Enter 6-digit code';

  @override
  String get profile2faSetupHint =>
      'Protect your account with one-time codes at sign-in.';

  @override
  String get profileDeleteAccount => 'Delete account';

  @override
  String get profileLogout => 'Log out';

  @override
  String get catClothing => 'Clothing';

  @override
  String get catShoes => 'Shoes';

  @override
  String get catElectronics => 'Electronics';

  @override
  String get catFurniture => 'Furniture';

  @override
  String get catDecor => 'Decor / Interior';

  @override
  String get catToys => 'Toys';

  @override
  String get catAdult => 'Adult products (18+)';

  @override
  String get catOther => 'Other';

  @override
  String get tierSmall => 'Small';

  @override
  String get tierLarge => 'Large';

  @override
  String get forbIntimate => 'Intimate';

  @override
  String get forbWeapons => 'Weapons';

  @override
  String get forbDrugs => 'Drugs';

  @override
  String get angle00 => 'Low 0° (front)';

  @override
  String get angle01 => 'Low 45°';

  @override
  String get angle02 => 'Low 90° (left)';

  @override
  String get angle03 => 'Low 135°';

  @override
  String get angle04 => 'Low 180° (back)';

  @override
  String get angle05 => 'Low 225°';

  @override
  String get angle06 => 'Low 270° (right)';

  @override
  String get angle07 => 'Low 315°';

  @override
  String get angle08 => 'Top forward 45°';

  @override
  String get angle09 => 'Top right 45°';

  @override
  String get angle10 => 'Top back 45°';

  @override
  String get angle11 => 'Top left 45°';

  @override
  String get wsSessionExpired => 'Session expired. Sign in again.';

  @override
  String get wsServerUnavailable =>
      'Server unavailable. Check API_URL and network.';

  @override
  String get wsQueueFailed => 'Could not connect to queue. Try again later.';

  @override
  String get wsQueueError => 'Queue connection error';

  @override
  String get calSaved => 'Calibration saved for 30 days';

  @override
  String get calRefFractionError =>
      'Enter reference fraction in frame (0.1–0.9)';

  @override
  String get calEnterDimensions => 'Enter dimensions in meters';

  @override
  String calCurrentLine(String method, String date) {
    return 'Current: $method · until $date';
  }

  @override
  String get calReset => 'Reset calibration';

  @override
  String get calIntro =>
      'Scale 1:1 and furniture require calibration (§3.7). Place a reference next to the product and specify its frame fraction.';

  @override
  String get calMethod => 'Method';

  @override
  String get calMethodCard => 'Bank card (85.6×54 mm)';

  @override
  String get calMethodA4 => 'A4 sheet (210×297 mm)';

  @override
  String get calMethodQr => 'QR code from PDF (100 mm)';

  @override
  String get calMethodManual => 'Manual dimensions (m)';

  @override
  String get calRefWidth => 'Reference width in frame (0.1–0.9)';

  @override
  String get calRefHeight => 'Reference height in frame (0.1–0.9)';

  @override
  String get calSave => 'Save calibration';

  @override
  String get calQrIntro =>
      'Download the QR reference PDF (100×100 mm), print and place next to the product.';

  @override
  String get calDownloadPdf => 'Download QR PDF';

  @override
  String get calQrSide => 'QR side (mm)';

  @override
  String get calQrWidth => 'QR in frame — width (fraction)';

  @override
  String get calQrHeight => 'QR in frame — height (fraction)';

  @override
  String get calSaveQr => 'Save from QR';

  @override
  String get calManualW => 'Product width (m)';

  @override
  String get calManualH => 'Product height (m)';

  @override
  String get calManualD => 'Product depth (m)';

  @override
  String storUsedLine(String bytes, String models, String glbs) {
    return 'Used: $bytes · folders: $models · GLB: $glbs';
  }

  @override
  String get storAutoDownload => 'Auto-download GLB on completion';

  @override
  String get storAutoDownloadDesc => '§3.3.2 — save model on device';

  @override
  String get storAutoCleanup => 'Auto-cleanup GLB';

  @override
  String storAutoCleanupDesc(String days) {
    return 'Delete non-favorites older than $days days';
  }

  @override
  String get storCleanupDays => 'Auto-cleanup period (days)';

  @override
  String get storDays7 => '7 days';

  @override
  String get storDays14 => '14 days';

  @override
  String get storDays30 => '30 days';

  @override
  String get storDays60 => '60 days';

  @override
  String get storDays90 => '90 days';

  @override
  String get storCleanupNow => 'Clean up now';

  @override
  String get storExportZip => 'Export all GLB to ZIP';

  @override
  String storZipCopied(String path) {
    return 'ZIP: $path (path copied)';
  }

  @override
  String storGlbDeleted(String count) {
    return 'Deleted local GLB files: $count';
  }

  @override
  String get impIntro =>
      'Upload a GLB file (up to 50 MB). Company Owner only §6.10.';

  @override
  String get impFileTooBig => 'File exceeds 50 MB (§6.10)';

  @override
  String get impOwnerOnly =>
      'Import is available to company Owner only (§6.10)';

  @override
  String get impUploadParamsError => 'Server did not return upload parameters';

  @override
  String get impValidating => 'Model validating (GLB 2.0 / PBR / Draco)…';

  @override
  String get impDone => 'Model imported';

  @override
  String get impName => 'Name';

  @override
  String get impCategory => 'Category';

  @override
  String get impPickGlb => 'Choose .glb';

  @override
  String impSize(String size) {
    return 'Size: $size';
  }

  @override
  String get impImporting => 'Importing…';

  @override
  String get impBtn => 'Import';

  @override
  String get impFree => 'Import is free';

  @override
  String impPriceLine(String price) {
    return 'Import cost: $price ₽ (charged to company balance)';
  }

  @override
  String get balStatusAuto => 'Status updates automatically';

  @override
  String get balTransactions => 'Transactions';

  @override
  String balTotalLine(String total) {
    return 'Total: $total';
  }

  @override
  String get balEmpty => 'No transactions';

  @override
  String get balSuccess => 'Success';

  @override
  String get balEmployee => 'Employee §8';

  @override
  String get balAll => 'All';

  @override
  String get balThresholdInvalid => 'Enter a valid threshold';

  @override
  String balDevMock(String balance) {
    return 'Balance: $balance ₽';
  }

  @override
  String get consentUpdatedTitle => 'Terms updated';

  @override
  String get consentAcceptAllSnackbar => 'Accept all updated documents';

  @override
  String get consentIntro => 'Accept new document versions to continue (§2.8).';

  @override
  String get consentRead => 'Read';

  @override
  String get consentHide => 'Hide text';

  @override
  String get consentAccept => 'I accept';

  @override
  String get consentContinue => 'Continue';

  @override
  String get consentSaving => 'Saving…';

  @override
  String get shootLinkTitle => 'Shoot by link';

  @override
  String get shootLinkCorpMode => 'Switch to corporate mode';

  @override
  String get shootLinkTier => 'Tier';

  @override
  String get shootLinkCreate => 'Create link and QR';

  @override
  String get shootLinkCopied => 'Link copied';

  @override
  String get shootLinkCopy => 'Copy';

  @override
  String get gdCameraRequired => 'Camera access required';

  @override
  String gdTurnToMarker(String azimuth, String elevation) {
    return 'Turn to AR marker $azimuth° / $elevation°';
  }

  @override
  String gdFpsWait(String fps) {
    return 'Wait ($fps FPS, power saving)';
  }

  @override
  String get gdAlignMarker => 'Align camera with AR marker';

  @override
  String get ucDraftNotFound => 'Shoot draft not found';

  @override
  String get ucForbiddenCategory =>
      'Forbidden category selected. Order will be rejected without refund.';

  @override
  String ucNoViewFile(String index) {
    return 'Missing view file $index';
  }

  @override
  String get gyroTiltDown => 'tilt phone down';

  @override
  String get gyroTiltUp => 'raise phone';

  @override
  String gyroTurnPitch(String dir, String pitch) {
    return 'Rotate phone: $dir (~$pitch°)';
  }

  @override
  String gyroTurnDegrees(String deg, String dir) {
    return 'Rotate phone about $deg° $dir';
  }

  @override
  String get gyroLeft => 'left';

  @override
  String get gyroRight => 'right';

  @override
  String get qaBlur => 'blur';

  @override
  String get qaOffCenter => 'off center';

  @override
  String get qaOverexposed => 'overexposed';

  @override
  String get qaOk => 'ok';

  @override
  String get qaCenterPhone => 'Move phone so the product is centered';

  @override
  String get qaCloser => 'Move closer so the product fills ~70% of screen';

  @override
  String get qaFarther => 'Move back so the product fills ~70% of screen';

  @override
  String get checkoutPromoApply => 'Apply';

  @override
  String checkoutPromoApplied(String amount) {
    return 'Discount −$amount ₽';
  }

  @override
  String get checkoutPromoInvalid => 'Invalid promocode';

  @override
  String get campaignBannerDismiss => 'Dismiss';

  @override
  String get companyDefaultName => 'Company';

  @override
  String get paymentStatusPending => 'Pending payment';

  @override
  String get paymentStatusSucceeded => 'Paid';

  @override
  String get paymentStatusCanceled => 'Canceled';

  @override
  String get draftRestoreTitle => 'Restore drafts?';

  @override
  String draftRestoreBody(String count) {
    return 'Found $count cloud backups (TTL 7 days, §3.3.2). Restore unfinished shoots?';
  }

  @override
  String get draftRestoredSnackbar => 'Drafts restored from cloud';

  @override
  String get resumeDraftTitle => 'Unfinished shoot';

  @override
  String resumeDraftBody(String category, String count, String total) {
    return 'You have a draft ($category, $count/$total frames). Continue or start over?';
  }

  @override
  String get resumeDraftDiscard => 'Start over';

  @override
  String get resumeDraftContinue => 'Continue';

  @override
  String get mvSearchHint => 'Search by name';

  @override
  String get mvFilterTierAll => 'All tiers';

  @override
  String get mvFilterAuthorAll => 'All authors';

  @override
  String get mvFilterAuthor => 'Author';

  @override
  String get mvClearDates => 'Clear dates';

  @override
  String get balancePresetsLabel => 'Saved views';

  @override
  String get balanceSavePreset => 'Save as…';

  @override
  String get balancePresetNameHint => 'View name';

  @override
  String get balancePresetSaved => 'View saved';

  @override
  String get balancePresetDeleted => 'View deleted';

  @override
  String get balanceApplyPreset => 'Apply';

  @override
  String get profileSessionsSection => 'Active sessions §19.14.4';

  @override
  String get profileSessionRevoke => 'Revoke';

  @override
  String get profileSessionsRevokeOthers => 'Revoke other sessions';

  @override
  String get profileSessionsRevokeOthersDone => 'Other sessions revoked';

  @override
  String get profileSessionsEmpty => 'No other active sessions';

  @override
  String get mvApiUploadTitle => 'API upload';

  @override
  String get mvApiSkuLabel => 'SKU';

  @override
  String get mvApiUploadBtn => 'API upload';

  @override
  String get mvLoadMore => 'Load more';
}
