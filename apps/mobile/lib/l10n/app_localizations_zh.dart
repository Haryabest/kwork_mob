// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Chinese (`zh`).
class AppLocalizationsZh extends AppLocalizations {
  AppLocalizationsZh([String locale = 'zh']) : super(locale);

  @override
  String get appName => 'KWork Mob';

  @override
  String get authTitle => '登录';

  @override
  String get email => '邮箱';

  @override
  String get password => '密码';

  @override
  String get login => '登录';

  @override
  String get register => '注册';

  @override
  String get forgotPassword => '忘记密码？';

  @override
  String get home => '首页';

  @override
  String get models => '模型';

  @override
  String get orders => '订单';

  @override
  String get support => '支持';

  @override
  String get profile => '个人资料';

  @override
  String get shoot => '拍摄商品';

  @override
  String get queue => '队列';

  @override
  String get faq => '常见问题';

  @override
  String get personalMode => '个人';

  @override
  String get corporateMode => '企业';

  @override
  String get onboarding1 => '从12个角度拍摄商品';

  @override
  String get onboarding2 => '支付套餐并等待生成';

  @override
  String get onboarding3 => '下载 .glb / .usdz 用于电商平台';

  @override
  String get onboarding4 => '在 WB 或 Ozon 发布模型';

  @override
  String get onboardingSub1 => '12 个 Guided Dome 角度 → 电商平台 3D 模型';

  @override
  String get onboardingSub2 =>
      'ARKit / ARCore 或陀螺仪引导 ±15° 角度。1:1 比例 — 在个人资料中用银行卡或 A4 校准。';

  @override
  String get onboardingSub3 => '下载 GLB/USDZ 并发布到 Wildberries 或 Ozon';

  @override
  String get onboardingSub4 => '温度超过 40°C 时拍摄将切换至节能模式（15 FPS）';

  @override
  String get skip => '跳过';

  @override
  String get alreadyHaveAccount => '已有账号？登录';

  @override
  String get continueBtn => '继续';

  @override
  String get errorNetwork => '无网络连接';

  @override
  String get comingSoon => '功能开发中';

  @override
  String get save => '保存';

  @override
  String get cancel => '取消';

  @override
  String get confirm => '确认';

  @override
  String get done => '完成';

  @override
  String get account => '账户';

  @override
  String get langRu => 'Русский';

  @override
  String get langEn => 'English';

  @override
  String get langKk => 'Қазақша';

  @override
  String get langZh => '中文';

  @override
  String get companyTopupTitle => '企业余额';

  @override
  String get companyTopupSubtitle => '充值账户 · §19.14.2';

  @override
  String get companyPoliciesTitle => '企业策略';

  @override
  String get companyPoliciesSubtitle => '权限与通知 · §19.14.2';

  @override
  String companyBalanceLabel(String balance) {
    return '企业余额：$balance ₽';
  }

  @override
  String get policiesMaxConcurrent => '默认并发订单上限';

  @override
  String get policiesNoMonthlyLimit => '无月度支出上限';

  @override
  String get policiesMonthlyLimit => '月度支出上限（₽）';

  @override
  String get policiesAllowedCategories => '允许的商品类别';

  @override
  String get policiesAllowDownload => '摄影师可下载模型';

  @override
  String get policiesAllowLinks => '摄影师可添加发布链接';

  @override
  String get policiesRequire2fa => '要求所有成员启用 2FA';

  @override
  String get policiesAutoBlock => '不活跃自动锁定（天）';

  @override
  String get policiesLowBalanceThreshold => '低余额阈值（₽）';

  @override
  String get policiesNotifySection => 'Owner 通知（§3.19）';

  @override
  String get policiesNotifyHint => '企业事件 push/邮件 接收人';

  @override
  String get policiesSaved => '策略已保存';

  @override
  String get policiesInvalidConcurrent => '请输入 1 至 20 的订单上限';

  @override
  String get policiesInvalidAutoBlock => '请输入有效的自动锁定天数';

  @override
  String get policiesInvalidThreshold => '请输入有效的余额阈值';

  @override
  String get policiesInvalidMonthly => '请输入有效的月度上限';

  @override
  String get notifyGenerationDone => '生成完成';

  @override
  String get notifyPhotographerUploaded => '摄影师已上传照片';

  @override
  String get notifySourceExpire => '云副本即将过期';

  @override
  String get notifyLowBalance => '企业余额不足';

  @override
  String get audienceOwnerOnly => '仅 Owner';

  @override
  String get audienceOwnerManager => 'Owner + Manager';

  @override
  String get audienceAll => '所有成员';

  @override
  String get balanceTitle => '余额';

  @override
  String get balanceCompanyTitle => '企业余额';

  @override
  String get balanceUnavailable => '您的角色无法查看余额';

  @override
  String lowBalanceBanner(String balance, String threshold) {
    return '企业余额不足：$balance ₽（阈值 $threshold ₽）。请充值 §20.3.5';
  }

  @override
  String get topup => '充值';

  @override
  String get topupMinAmount => '最低 100 ₽';

  @override
  String get balanceTopupSuccess => '余额已充值';

  @override
  String get companyTopupSuccess => '企业余额已充值';

  @override
  String get paymentCanceled => '支付已取消';

  @override
  String get lowBalanceThreshold => '低余额阈值，₽ §20.3.5';

  @override
  String get saveThreshold => '保存阈值';

  @override
  String get thresholdSaved => '低余额阈值已保存 §20.3.5';

  @override
  String get topupCompanyBtn => '充值企业余额 §19.14.2';

  @override
  String get topupAmount => '充值金额';

  @override
  String get topupCompanyAmount => '企业充值 §19.14.2';

  @override
  String get topupCard => '银行卡充值';

  @override
  String get topupSbpQr => 'SBP 二维码';

  @override
  String get sbpQrTitle => 'SBP — 扫描二维码';

  @override
  String get sbpAutoStatus => '状态将自动更新';

  @override
  String get copyPayload => '复制 payload';

  @override
  String get dateFrom => '起始日期';

  @override
  String get dateTo => '结束日期';

  @override
  String get txTypeLabel => '交易类型';

  @override
  String get txTypeAll => '全部';

  @override
  String get txTypeTopup => '充值';

  @override
  String get txTypeCharge => '扣款';

  @override
  String get txTypeRefund => '退款';

  @override
  String get perPage => '每页 §20.3.4';

  @override
  String get applyFilters => '应用筛选';

  @override
  String get exportCsv => '导出 CSV §20.3.4';

  @override
  String get exporting => '导出中…';

  @override
  String get companyTopupScreenTitle => '企业充值';

  @override
  String get companyTopupScreenHint => 'Owner：通过 YooKassa 充值企业账户 §19.14.2';

  @override
  String get languageInterface => '界面语言';

  @override
  String get team => '团队';

  @override
  String get switchMode => '个人 / 企业模式';

  @override
  String get localStorage => '本地存储';

  @override
  String get localStorageSub => 'GLB、自动清理、ZIP 导出';

  @override
  String get calibration => '比例校准';

  @override
  String get calibrationSub => '银行卡 / A4 / QR · §3.7';

  @override
  String get importModel => '导入模型';

  @override
  String get importModelSub => '现成 GLB · §6.10';

  @override
  String get saveProfile => '保存资料';

  @override
  String get profileSaved => '资料已保存';

  @override
  String balanceLabel(String amount) {
    return '余额：$amount ₽';
  }

  @override
  String get exportShareText => '交易 §20.3.4';

  @override
  String get exportSuccess => 'CSV 已导出';

  @override
  String get open => '打开';

  @override
  String get notificationDefault => '通知';

  @override
  String get authCreateAccount => '创建账户';

  @override
  String get authVerifyEmail => '邮箱验证';

  @override
  String get authAccountType => '账户类型';

  @override
  String get authForgotPasswordTitle => '密码恢复';

  @override
  String get authNewPasswordTitle => '新密码';

  @override
  String get authTwoFaTitle => '输入 2FA 验证码';

  @override
  String get authSendLink => '发送链接';

  @override
  String get authSavePassword => '保存密码';

  @override
  String get authRememberMe => '记住我';

  @override
  String get authPasswordConfirm => '确认密码';

  @override
  String get authConsents => '我接受用户协议、隐私政策、要约、权利确认及禁止内容规则';

  @override
  String get authEmailCode => '邮件验证码（6 位）';

  @override
  String get authIndividual => '个人';

  @override
  String get authLegal => '法人 / 个体工商户';

  @override
  String get authFullNameOptional => '姓名（可选）';

  @override
  String get authOrgName => '组织名称';

  @override
  String get authInn => '税号';

  @override
  String get authOgrn => 'OGRN / OGRNIP';

  @override
  String get authLegalAddress => '法定地址';

  @override
  String get authDirectorName => '负责人姓名';

  @override
  String get authBankName => '银行';

  @override
  String get authBik => 'BIC';

  @override
  String get authCheckingAccount => '结算账户';

  @override
  String get authResetToken => '邮件中的令牌';

  @override
  String get authNewPasswordField => '新密码';

  @override
  String get authAuthenticatorCode => '验证器代码';

  @override
  String get authBack => '返回';

  @override
  String get authBackToLogin => '返回登录';

  @override
  String get authAcceptTerms => '请接受服务条款';

  @override
  String get authPasswordUpdated => '密码已更新，请用新密码登录';

  @override
  String authDevCode(String code) {
    return 'Dev 码：$code';
  }

  @override
  String authDevToken(String token) {
    return 'Dev 令牌：$token';
  }

  @override
  String get shootCategoryTitle => '商品类别';

  @override
  String get shootCategoryLabel => '类别';

  @override
  String get shootCategoryRestricted => '您的公司角色不可使用此类别';

  @override
  String get corpPolicyDenied => '公司政策不允许此操作';

  @override
  String get shootForbiddenCategories => '禁止类别';

  @override
  String get shootForbiddenHint => '若勾选 — 不会创建订单，不会扣款';

  @override
  String get shootAgeConfirmed => '年龄已验证';

  @override
  String get shootAgeConfirmedSub => '无需再次输入日期';

  @override
  String get shootBirthDate => '出生日期 (YYYY-MM-DD)';

  @override
  String get shootBirthDateHint => '验证成功后保存到个人资料';

  @override
  String get shootScaleRequired => '比例 (m) — 家具必填';

  @override
  String get shootCalibrationBtn => '校准：银行卡 / A4 / QR (§3.7)';

  @override
  String get shootLength => '长';

  @override
  String get shootWidth => '宽';

  @override
  String get shootHeight => '高';

  @override
  String get shootModelName => '模型名称（可选）';

  @override
  String get shootModelNameHint => '例如：Nike Air 运动鞋';

  @override
  String get shootTier => '套餐';

  @override
  String get shootGhostMeshHint => 'Ghost Mesh — 双指缩放';

  @override
  String get shootNext => '继续拍摄';

  @override
  String get shootAgeConfirmTitle => '确认您已满 18 岁';

  @override
  String get shootAgeConfirmBody => '请输入出生日期 (YYYY-MM-DD)。';

  @override
  String get shootInvalidDate => '日期无效 (YYYY-MM-DD)';

  @override
  String get shootAgeOnly18 => '仅 18 岁及以上可创建模型';

  @override
  String get shootBirthRequired => '请填写 18+ 出生日期';

  @override
  String get shootForbiddenTitle => '禁止类别';

  @override
  String get shootForbiddenBody => '您选择了禁止类别，订单将被拒绝且不退款。是否继续？';

  @override
  String get shootOrderBlocked => '不会创建订单 — 请更换类别';

  @override
  String shootStorageFree(String need, String free) {
    return '请释放手机存储空间（需要 $need MB，可用约 $free MB）';
  }

  @override
  String shootStorageFreeUnknown(String need) {
    return '请释放手机存储空间（需要 $need MB）';
  }

  @override
  String get shootQualityTitle => '质量检查';

  @override
  String get shootQualityLow => '照片质量较低，请改善拍摄条件';

  @override
  String get shootQualityLowTitle => '质量较低';

  @override
  String get shootQualityLowDialog => '部分帧质量较低，可能导致模型缺陷。是否继续？';

  @override
  String get yes => '是';

  @override
  String get no => '否';

  @override
  String get shootQualityContinue => '继续上传';

  @override
  String get shootQualityContinueForce => '忽略错误继续';

  @override
  String get shootQualityRestart => '从头重新拍摄';

  @override
  String shootArHint(String tier, String scale) {
    return 'AR：套餐「$tier」，尺寸 $scale';
  }

  @override
  String get shootTitle => '拍摄';

  @override
  String get shootOverheatTitle => '手机过热';

  @override
  String shootOverheatBody(String temp) {
    return '电池温度 ≈ $temp°C（>45°C）。建议暂停直至冷却。继续将启用节能模式（15 FPS）。';
  }

  @override
  String get shootAbort => '停止';

  @override
  String get shootExit => '退出';

  @override
  String get shootCalibrateShort => '校准';

  @override
  String get shootArCameraActive => 'AR 相机已激活';

  @override
  String shootAngleLine(
    String current,
    String total,
    String label,
    String backend,
  ) {
    return '角度 $current/$total · $label · $backend';
  }

  @override
  String get uploadPhotoTitle => '上传照片';

  @override
  String get uploadPreparing => '准备中…';

  @override
  String uploadResumeFound(String done) {
    return '发现未完成的上传 ($done/12)';
  }

  @override
  String get uploadResumeHint => '§3.4.1：进度已本地保存。断线后将从最后一张照片继续。';

  @override
  String get uploadBuildingZip => '打包 ZIP + SHA-256…';

  @override
  String uploadSha256(String hash) {
    return 'SHA-256: $hash…';
  }

  @override
  String get uploadPresigned => '获取 presigned URL…';

  @override
  String get uploadEncrypting => 'E2E 照片加密…';

  @override
  String uploadProgress(String current, String total) {
    return '上传 $current/$total…';
  }

  @override
  String uploadUploaded(String done) {
    return '已上传 $done/12';
  }

  @override
  String get uploadInterrupted => '上传中断 — 可继续';

  @override
  String get uploadUploading => '上传中…';

  @override
  String get uploadContinue => '继续上传';

  @override
  String get upload12Photos => '上传 12 张照片';

  @override
  String get checkoutTitle => '支付';

  @override
  String get checkoutPayTitle => '订单支付';

  @override
  String get checkoutSubmitGeneration => '提交生成';

  @override
  String get checkoutNeedCalibration => '需要校准';

  @override
  String get checkoutCalibrationBody => '1:1 比例请用银行卡、A4 或 QR 校准 (§3.7)。';

  @override
  String get checkoutCalibrate => '校准';

  @override
  String checkoutCategory(String label) {
    return '类别：$label';
  }

  @override
  String checkoutTier(String label) {
    return '套餐：$label';
  }

  @override
  String checkoutBasePrice(String amount) {
    return '基础价格：$amount ₽';
  }

  @override
  String get checkoutUpsells => '附加服务';

  @override
  String checkoutTotal(String amount) {
    return '合计：$amount ₽';
  }

  @override
  String get checkoutPromo => '优惠码';

  @override
  String get checkoutFioOptional => '姓名（可选）';

  @override
  String get checkoutFioHint => '可跳过';

  @override
  String get checkoutFioTaxHint => '姓名用于 My Tax 收据 (§19.8.1)';

  @override
  String get checkoutPayCard => '银行卡支付';

  @override
  String get checkoutPaySbp => 'SBP 二维码支付';

  @override
  String get checkoutSbpOrderTitle => 'SBP — 订单支付';

  @override
  String get guestShootTitle => '链接拍摄';

  @override
  String guestTask(String id) {
    return '任务 $id…';
  }

  @override
  String guestMeta(String category, String tier) {
    return '类别：$category · 套餐：$tier';
  }

  @override
  String get guestHint => '访客模式：通过 AR 或相册拍摄 12 个角度 (§3.15)。';

  @override
  String get guestStartAr => '开始 AR 拍摄';

  @override
  String get guestGallery12 => '从相册选 12 张';

  @override
  String guestPhotosRequired(String need, String selected) {
    return '需要恰好 $need 张照片（已选 $selected）';
  }

  @override
  String get guestUploadTitle => '通过链接发送';

  @override
  String get guestReadyToSend => '准备发送';

  @override
  String get guestGettingUrls => '获取 upload URL…';

  @override
  String guestUploading(String current) {
    return '上传 $current/12…';
  }

  @override
  String get guestConfirming => '确认中…';

  @override
  String get guestSentToOwner => '照片已发送给所有者';

  @override
  String guestMissingFrame(String index) {
    return '缺少视角文件 $index';
  }

  @override
  String get guestSend12Photos => '发送 12 张照片';

  @override
  String get guestLinkUsed => '链接已使用。企业所有者将收到通知。';

  @override
  String get prefTopupFailed => '充值失败';

  @override
  String homePendingUploadTitle(String uploaded, String total) {
    return '未完成的照片上传 ($uploaded/$total)';
  }

  @override
  String get homePendingUploadHint => '上传已中断，可从最后一帧继续。';

  @override
  String homeModePrefix(String mode) {
    return '模式：$mode';
  }

  @override
  String get homeNoCompanies => '没有关联的公司';

  @override
  String get homeSwitchModeTitle => '切换模式？';

  @override
  String get homeSwitchModeBody => '确认切换个人 / 公司';

  @override
  String get homeShootLinkQr => '链接拍摄 (QR)';

  @override
  String get ordersExecutorFilter => '执行人 §3.16.2';

  @override
  String get ordersAllMembers => '全部员工';

  @override
  String get ordersEmpty => '暂无订单';

  @override
  String get orderStatusPending => '新建';

  @override
  String get orderStatusAwaitingPayment => '待付款';

  @override
  String get orderStatusQueued => '排队中';

  @override
  String get orderStatusProcessing => '处理中';

  @override
  String get orderStatusCompleted => '已完成';

  @override
  String get orderStatusFailed => '错误';

  @override
  String get orderStatusCancelled => '已取消';

  @override
  String get orderStatusPaid => '已付款';

  @override
  String get orderStatusBlockedNsfw => 'NSFW 拦截';

  @override
  String get notificationsTitle => '通知';

  @override
  String get notificationsEmpty => '暂无通知';

  @override
  String get queueGenerationTitle => '模型生成';

  @override
  String get queueCancelTitle => '取消生成';

  @override
  String get queueCancelWarning => '注意！生成过程中取消不会退款，因为计算资源已被消耗。仍要取消吗？';

  @override
  String get queueUnderstand => '我明白';

  @override
  String get queueReconnectWs => '重新连接 WebSocket';

  @override
  String get queueNsfwBlocked =>
      '订单被拦截：导入贴图含 NSFW 内容。款项已退回公司余额。账户将进行最多 24 小时的人工审核 (§10.8)。';

  @override
  String queueStatus(String status) {
    return '状态：$status';
  }

  @override
  String queuePosition(String pos, String ewt) {
    return '排队位置：$pos。预计等待时间：$ewt 分钟';
  }

  @override
  String get queueWsConnected => 'WebSocket：已连接';

  @override
  String get queueWsErrorShort => 'WebSocket：错误';

  @override
  String get queueWsConnecting => 'WebSocket：…';

  @override
  String get queueRefresh => '刷新';

  @override
  String get queueCancelOrder => '取消';

  @override
  String get faqSupportTitle => '常见问题 / 支持';

  @override
  String get faqTab => '常见问题';

  @override
  String get faqMyTickets => '我的工单';

  @override
  String faqLoadError(String error) {
    return '加载错误：$error';
  }

  @override
  String get faqQuestionMin => '问题：至少 10 个字符';

  @override
  String get faqDefaultSubject => '来自应用的提问';

  @override
  String get faqQuestionSent => '问题已发送';

  @override
  String get faqEmpty => '暂无常见问题';

  @override
  String get faqAskPrompt => '没有找到答案？提个问题吧';

  @override
  String get faqSubjectOptional => '主题（可选）';

  @override
  String get faqYourQuestion => '您的问题';

  @override
  String get faqSending => '发送中…';

  @override
  String get faqSend => '发送';

  @override
  String get faqNoTickets => '暂无工单';

  @override
  String faqTicketDefault(String id) {
    return '工单 #$id';
  }

  @override
  String get faqSupportRole => '支持';

  @override
  String get faqYouRole => '您';

  @override
  String get faqClarifyHint => '补充提问…';

  @override
  String get faqReply => '回复';

  @override
  String get faqClose => '关闭';

  @override
  String get faqTicketClosed => '工单已关闭';

  @override
  String get teamTitle => '团队';

  @override
  String get teamNoAccess => '无团队访问权限';

  @override
  String get teamMembers => '成员';

  @override
  String get teamNoMembers => '暂无成员';

  @override
  String get teamInvite => '邀请';

  @override
  String get teamAudit => '审计';

  @override
  String get teamNoAudit => '暂无审计记录';

  @override
  String get teamExtendAllTitle => '延长所有源文件';

  @override
  String get teamExtendAllBody =>
      '将公司所有模型的云端源文件存储延长 30 天。限制——每个模型 3 次延长 (§9.1.2)。';

  @override
  String get teamExtend => '延长';

  @override
  String get teamExtendAllBtn => '延长所有源文件 §9.1.2';

  @override
  String get teamMemberFallback => '成员';

  @override
  String get teamRole => '角色';

  @override
  String get teamActiveOrdersLimit => '活跃订单上限';

  @override
  String get teamInviteSent => '邀请已发送';

  @override
  String get teamInviteSentWithLink => '邀请已发送 · 链接已复制';

  @override
  String teamMemberSubtitle(String role, String limit) {
    return '$role · 上限 $limit 个订单';
  }

  @override
  String teamCompany(String id) {
    return '公司 #$id';
  }

  @override
  String get teamSendInvite => '发送邀请';

  @override
  String get teamSearchHint => '姓名或邮箱';

  @override
  String get teamRoleAll => '所有角色';

  @override
  String get teamLoadMore => '加载更多';

  @override
  String get mvPublishValidating => '导入校验中';

  @override
  String get mvPublishImported => '已导入';

  @override
  String get mvPublishImportFailed => '导入失败';

  @override
  String get mvPublishNotPublished => '未发布';

  @override
  String get mvPublishVerified => '已验证';

  @override
  String get mvPublishPublished => '已发布';

  @override
  String get mvRenameTitle => '重命名模型';

  @override
  String get mvNameLabel => '名称';

  @override
  String get mvLinkCopied => '链接已复制';

  @override
  String get mvMovedToTrash => '模型已移至回收站';

  @override
  String get mvRetry => '重试';

  @override
  String get mvNoModels => '暂无模型';

  @override
  String get mvTitle => '模型';

  @override
  String get mvTrash => '回收站';

  @override
  String get mvFilterAll => '全部';

  @override
  String get mvFilterFavorites => '收藏';

  @override
  String get mvSortNewest => '最新优先';

  @override
  String get mvSortOldest => '最早优先';

  @override
  String get mvNoModelsFilter => '该筛选条件下无模型';

  @override
  String get mvDownloadGlbOzon => '下载 .glb (Ozon)';

  @override
  String get mvDownloadUsdzWb => '下载 .usdz (Wildberries)';

  @override
  String get mvShare => '分享';

  @override
  String get mvRate => '评价模型';

  @override
  String get mvVerifyLink => '验证链接';

  @override
  String get mvEdit => '编辑';

  @override
  String get mvRename => '重命名';

  @override
  String get mvDelete => '删除';

  @override
  String mvLinkCopiedMarketplace(String mp) {
    return '$mp 链接已复制';
  }

  @override
  String mvGlbSaved(String path) {
    return 'GLB 已保存：$path';
  }

  @override
  String get mvPublicLinkTitle => '公开链接 §3.12';

  @override
  String mvUntil(String date) {
    return '至：$date';
  }

  @override
  String get mvNoLocalPhotosTitle => '无本地照片';

  @override
  String get mvNoLocalPhotosBody => '重新生成需要设备上有 12 张源照片。从云端恢复还是重新拍摄？';

  @override
  String get mvRestore => '恢复';

  @override
  String get mvCantDetectCategory => '无法识别类目/套餐';

  @override
  String get mvStorageExtended => '存储已延长';

  @override
  String get mvDeleteTitle => '删除模型？';

  @override
  String get mvDeleteBody => '源照片和模型将移至回收站 30 天。是否继续？';

  @override
  String get mvInTrash => '已在回收站';

  @override
  String get mvSourcesRestored => '源文件已恢复';

  @override
  String get mvCardLinkTitle => '商品卡链接';

  @override
  String get mvCardLinkHint => 'https://www.wildberries.ru/... 或 ozon.ru/...';

  @override
  String get mvAdd => '添加';

  @override
  String mvLinkStatus(String status) {
    return '链接：$status';
  }

  @override
  String get mvRateTitle => '请为模型质量打分（1 到 5）';

  @override
  String get mvWhatsWrong => '哪里不对？';

  @override
  String get mvReasonBlurry => '纹理模糊';

  @override
  String get mvReasonHoles => '破洞或伪影';

  @override
  String get mvReasonScale => '比例不对';

  @override
  String get mvReasonColor => '颜色/光照不对';

  @override
  String get mvReasonOther => '其他';

  @override
  String get mvComment => '备注';

  @override
  String get mvLater => '稍后';

  @override
  String get mvModelTitle => '3D 模型';

  @override
  String get mvGlbNotReady => 'GLB 尚未就绪';

  @override
  String mvCloud(String days, String used, String max) {
    return '云端：$days 天 · 续期 $used/$max';
  }

  @override
  String get mvLocalGlbSaved => '本地 GLB 已保存';

  @override
  String get mvRegenerate => '重新生成';

  @override
  String get mvUpdateGlb => '更新 GLB';

  @override
  String get mvGlbLocal => 'GLB 本地';

  @override
  String get mvDownloadWb => '下载 WB';

  @override
  String get mvDownloadOzon => '下载 Ozon';

  @override
  String get mvSources => '源文件';

  @override
  String get mvExtend30 => '+30 天';

  @override
  String get mvToTrash => '移至回收站';

  @override
  String get mvLink => '链接';

  @override
  String get mvImOnWb => '我在 WB';

  @override
  String get mvImOnOzon => '我在 Ozon';

  @override
  String mvApiResult(String status) {
    return 'API：$status';
  }

  @override
  String get orderLimitTitle => '活跃订单上限';

  @override
  String get orderLimitBody => '已达到您角色的并发订单上限。请等待当前生成完成或联系 Owner。';

  @override
  String get orderLimitOk => '知道了';

  @override
  String get trashTitle => '回收站';

  @override
  String get trashEmpty => '回收站为空\n已删除模型保留 30 天';

  @override
  String get trashRestore => '恢复';

  @override
  String get trashRestored => '已恢复';

  @override
  String trashOrderLine(String id, String date) {
    return '订单 #$id · 删除于 $date';
  }

  @override
  String trashPurgeLine(String date) {
    return '永久删除：$date';
  }

  @override
  String get prefPushEnabled => '推送通知';

  @override
  String get prefEmailEnabled => '邮件通知';

  @override
  String get prefGenerationDone => '生成完成';

  @override
  String get prefRefund => '退款';

  @override
  String get prefNsfwBlocked => 'NSFW 拦截';

  @override
  String get prefSourceExpire => '源文件过期';

  @override
  String get prefCleanup => '存储清理';

  @override
  String get prefPublishReminder => '发布提醒';

  @override
  String get prefSupportReply => '客服回复';

  @override
  String get profileInnLabel => '税号（可选）§19.14.1';

  @override
  String get profilePhoneLabel => '电话（可选）§19.14.1';

  @override
  String get profileFullNameLabel => '姓名（可选）§19.14.1';

  @override
  String get profileExportFormat => '导出格式 §19.14.3';

  @override
  String get profileExportGlb => '.glb（Ozon / 通用）';

  @override
  String get profileExportUsdz => '.usdz（Wildberries / AR）';

  @override
  String get profileTheme => '主题 §19.14.3';

  @override
  String get themeSystem => '跟随系统';

  @override
  String get themeLight => '浅色';

  @override
  String get themeDark => '深色';

  @override
  String get profileLanguage => '语言';

  @override
  String get profileNotificationsSection => '通知 §19.14.3';

  @override
  String get profileEventsSection => '事件 §3.4.3';

  @override
  String get profileSecuritySection => '安全 §19.14.4';

  @override
  String get profileChangePassword => '修改密码';

  @override
  String get profileChangePasswordTitle => '修改密码';

  @override
  String get profileCurrentPassword => '当前密码';

  @override
  String get profileNewPassword => '新密码';

  @override
  String get profilePasswordConfirm => '确认';

  @override
  String get profilePasswordChanged => '密码已修改';

  @override
  String get profileMinPassword => '至少 8 个字符';

  @override
  String get profilePasswordMismatch => '两次密码不一致';

  @override
  String get profile2faSection => '双因素认证 §19.14.4';

  @override
  String get profile2faEnabled => '2FA 已启用';

  @override
  String get profile2faDisabled => '2FA 未启用';

  @override
  String get profile2faOwnerRequired => 'Owner 必须启用 2FA（§10.7.5）';

  @override
  String get profile2faActiveHint =>
      'TOTP 已激活 — Google Authenticator、1Password 等。';

  @override
  String get profile2faStep1 => '1. 在验证器应用中扫描二维码';

  @override
  String get profile2faStep2 => '2. 或手动输入密钥';

  @override
  String get profileSecretCopied => '密钥已复制';

  @override
  String get profile2faCodeLabel => '验证器代码';

  @override
  String get profileConfirm2fa => '确认 2FA';

  @override
  String get profileEnable2fa => '启用 2FA';

  @override
  String get profile2faEnabledSnackbar => '2FA 已启用';

  @override
  String get profileDeleteAccountTitle => '删除账户？';

  @override
  String get profileDeleteAccountBody =>
      '所有模型和个人数据将在 30 天内删除（§2.8.3）。财务记录将匿名化并保留 5 年。';

  @override
  String get profileDeleteAccountBtn => '删除';

  @override
  String get profileDeleteRequestAccepted => '请求已接受';

  @override
  String get notifGenDoneTitle => '生成完成';

  @override
  String notifGenDoneBody(String id) {
    return '订单 #$id 已就绪';
  }

  @override
  String get notifNsfwTitle => 'NSFW 拦截';

  @override
  String notifNsfwBody(String id) {
    return '订单 #$id 被拒绝。已退款。账户审核最多 24 小时。';
  }

  @override
  String get notifGenFailedTitle => '生成失败';

  @override
  String notifGenFailedBody(String id) {
    return '订单 #$id 失败';
  }

  @override
  String get notifRefundTitle => '退款';

  @override
  String notifRefundBody(String id) {
    return '订单 #$id 已退款';
  }

  @override
  String get notifCancelledTitle => '订单已取消';

  @override
  String notifCancelledBody(String id) {
    return '订单 #$id 已取消';
  }

  @override
  String get notifCompanyInviteTitle => '公司邀请';

  @override
  String get publishGuideTitle => '如何发布';

  @override
  String get publishGuideIntro => '下载模型文件并上传到 marketplace 商品卡片。';

  @override
  String get publishGuideWbTitle => 'Wildberries';

  @override
  String get publishGuideWb1 => '1. 下载 .usdz（模型中的「下载 WB」）。';

  @override
  String get publishGuideWb2 => '2. 在 WB 卖家后台打开商品 → 媒体 → 3D。';

  @override
  String get publishGuideWb3 => '3. 为 iOS 买家上传 .usdz。';

  @override
  String get publishGuideOzonTitle => 'Ozon';

  @override
  String get publishGuideOzon1 => '1. 下载 .glb（下载 Ozon）。';

  @override
  String get publishGuideOzon2 => '2. 在 Ozon 后台打开商品 → 3D 模型。';

  @override
  String get publishGuideOzon3 => '3. 为 Android 买家上传 .glb。';

  @override
  String get publishGuideOpenModels => '前往模型';

  @override
  String get apiKeysTitle => 'API 密钥';

  @override
  String get apiKeysSubtitle => 'Owner · scopes · rate limit';

  @override
  String get apiKeysCreate => '创建密钥';

  @override
  String get apiKeysRevoke => '撤销';

  @override
  String get apiKeysCopyOnce => '请复制密钥 — 不会再次显示';

  @override
  String get apiKeysName => '名称';

  @override
  String get apiKeysEmpty => '暂无密钥';

  @override
  String get apiKeysCreated => '密钥已创建';

  @override
  String get profileCopySecretBtn => '复制密钥';

  @override
  String get profile2faCodeStep => '3. 输入 6 位代码';

  @override
  String get profile2faSetupHint => '使用一次性代码保护登录安全。';

  @override
  String get profileDeleteAccount => '删除账户';

  @override
  String get profileLogout => '退出登录';

  @override
  String get catClothing => '服装';

  @override
  String get catShoes => '鞋类';

  @override
  String get catElectronics => '电子产品';

  @override
  String get catFurniture => '家具';

  @override
  String get catDecor => '装饰 / 室内';

  @override
  String get catToys => '玩具';

  @override
  String get catAdult => '成人用品 (18+)';

  @override
  String get catOther => '其他';

  @override
  String get tierSmall => '小型';

  @override
  String get tierLarge => '大型';

  @override
  String get forbIntimate => '情趣';

  @override
  String get forbWeapons => '武器';

  @override
  String get forbDrugs => '毒品';

  @override
  String get angle00 => '低 0°（正面）';

  @override
  String get angle01 => '低 45°';

  @override
  String get angle02 => '低 90°（左）';

  @override
  String get angle03 => '低 135°';

  @override
  String get angle04 => '低 180°（背面）';

  @override
  String get angle05 => '低 225°';

  @override
  String get angle06 => '低 270°（右）';

  @override
  String get angle07 => '低 315°';

  @override
  String get angle08 => '高 前 45°';

  @override
  String get angle09 => '高 右 45°';

  @override
  String get angle10 => '高 后 45°';

  @override
  String get angle11 => '高 左 45°';

  @override
  String get wsSessionExpired => '会话已过期，请重新登录。';

  @override
  String get wsServerUnavailable => '服务器不可用，请检查 API_URL 和网络。';

  @override
  String get wsQueueFailed => '无法连接队列，请稍后重试。';

  @override
  String get wsQueueError => '队列连接错误';

  @override
  String get calSaved => '校准已保存 30 天';

  @override
  String get calRefFractionError => '请输入参考物在画面中的比例 (0.1–0.9)';

  @override
  String get calEnterDimensions => '请输入尺寸（米）';

  @override
  String calCurrentLine(String method, String date) {
    return '当前：$method · 至 $date';
  }

  @override
  String get calReset => '重置校准';

  @override
  String get calIntro => '1:1 比例和家具需要校准 (§3.7)。将参考物放在商品旁并指定画面比例。';

  @override
  String get calMethod => '方式';

  @override
  String get calMethodCard => '银行卡 (85.6×54 mm)';

  @override
  String get calMethodA4 => 'A4 纸 (210×297 mm)';

  @override
  String get calMethodQr => 'PDF QR (100 mm)';

  @override
  String get calMethodManual => '手动输入尺寸 (m)';

  @override
  String get calRefWidth => '参考物宽度比例 (0.1–0.9)';

  @override
  String get calRefHeight => '参考物高度比例 (0.1–0.9)';

  @override
  String get calSave => '保存校准';

  @override
  String get calQrIntro => '下载 QR 参考 PDF (100×100 mm)，打印并放在商品旁。';

  @override
  String get calDownloadPdf => '下载 QR PDF';

  @override
  String get calQrSide => 'QR 边长 (mm)';

  @override
  String get calQrWidth => 'QR 画面宽度比例';

  @override
  String get calQrHeight => 'QR 画面高度比例';

  @override
  String get calSaveQr => '按 QR 保存';

  @override
  String get calManualW => '商品宽度 (m)';

  @override
  String get calManualH => '商品高度 (m)';

  @override
  String get calManualD => '商品深度 (m)';

  @override
  String storUsedLine(String bytes, String models, String glbs) {
    return '已用：$bytes · 文件夹：$models · GLB：$glbs';
  }

  @override
  String get storAutoDownload => '完成时自动下载 GLB';

  @override
  String get storAutoDownloadDesc => '§3.3.2 — 在设备上保存模型';

  @override
  String get storAutoCleanup => 'GLB 自动清理';

  @override
  String storAutoCleanupDesc(String days) {
    return '删除超过 $days 天的非收藏 GLB';
  }

  @override
  String get storCleanupDays => '自动清理周期（天）';

  @override
  String get storDays7 => '7 天';

  @override
  String get storDays14 => '14 天';

  @override
  String get storDays30 => '30 天';

  @override
  String get storDays60 => '60 天';

  @override
  String get storDays90 => '90 天';

  @override
  String get storCleanupNow => '立即清理';

  @override
  String get storExportZip => '导出全部 GLB 为 ZIP';

  @override
  String storZipCopied(String path) {
    return 'ZIP：$path（路径已复制）';
  }

  @override
  String storGlbDeleted(String count) {
    return '已删除本地 GLB：$count';
  }

  @override
  String get impIntro => '上传 GLB（最大 50 MB）。仅公司 Owner §6.10。';

  @override
  String get impFileTooBig => '文件超过 50 MB (§6.10)';

  @override
  String get impOwnerOnly => '仅公司 Owner 可导入 (§6.10)';

  @override
  String get impUploadParamsError => '服务器未返回上传参数';

  @override
  String get impValidating => '模型验证中 (GLB 2.0 / PBR / Draco)…';

  @override
  String get impDone => '模型已导入';

  @override
  String get impName => '名称';

  @override
  String get impCategory => '类别';

  @override
  String get impPickGlb => '选择 .glb';

  @override
  String impSize(String size) {
    return '大小：$size';
  }

  @override
  String get impImporting => '导入中…';

  @override
  String get impBtn => '导入';

  @override
  String get impFree => '导入免费';

  @override
  String impPriceLine(String price) {
    return '导入费用：$price ₽（从公司余额扣除）';
  }

  @override
  String get balStatusAuto => '状态将自动更新';

  @override
  String get balTransactions => '交易';

  @override
  String balTotalLine(String total) {
    return '共：$total';
  }

  @override
  String get balEmpty => '暂无交易';

  @override
  String get balSuccess => '成功';

  @override
  String get balEmployee => '员工 §8';

  @override
  String get balAll => '全部';

  @override
  String get balThresholdInvalid => '请输入有效阈值';

  @override
  String balDevMock(String balance) {
    return '余额：$balance ₽';
  }

  @override
  String get consentUpdatedTitle => '条款已更新';

  @override
  String get consentAcceptAllSnackbar => '请接受所有更新的文档';

  @override
  String get consentIntro => '接受新版本文档以继续 (§2.8)。';

  @override
  String get consentRead => '阅读';

  @override
  String get consentHide => '隐藏文本';

  @override
  String get consentAccept => '我接受';

  @override
  String get consentContinue => '继续';

  @override
  String consentDocVersion(String title, String version) {
    return '$title · v$version';
  }

  @override
  String get consentSaving => '保存中…';

  @override
  String get shootLinkTitle => '链接拍摄';

  @override
  String get shootLinkCorpMode => '请切换到公司模式';

  @override
  String get shootLinkTier => '套餐';

  @override
  String get shootLinkCreate => '创建链接和 QR';

  @override
  String get shootLinkCopied => '链接已复制';

  @override
  String get shootLinkCopy => '复制';

  @override
  String get gdCameraRequired => '需要相机权限';

  @override
  String gdTurnToMarker(String azimuth, String elevation) {
    return '转向 AR 标记 $azimuth° / $elevation°';
  }

  @override
  String gdFpsWait(String fps) {
    return '请稍候（$fps FPS，省电模式）';
  }

  @override
  String get gdAlignMarker => '将相机对准 AR 标记';

  @override
  String get ucDraftNotFound => '未找到拍摄草稿';

  @override
  String get ucForbiddenCategory => '选择了禁止类别，订单将被拒绝且不退款。';

  @override
  String ucNoViewFile(String index) {
    return '缺少视角文件 $index';
  }

  @override
  String get gyroTiltDown => '向下倾斜手机';

  @override
  String get gyroTiltUp => '抬起手机';

  @override
  String gyroTurnPitch(String dir, String pitch) {
    return '旋转手机：$dir（约 $pitch°）';
  }

  @override
  String gyroTurnDegrees(String deg, String dir) {
    return '将手机旋转约 $deg° $dir';
  }

  @override
  String get gyroLeft => '向左';

  @override
  String get gyroRight => '向右';

  @override
  String get qaBlur => '模糊';

  @override
  String get qaOffCenter => '未居中';

  @override
  String get qaOverexposed => '过曝';

  @override
  String get qaOk => 'ok';

  @override
  String get qaCenterPhone => '移动手机使商品居中';

  @override
  String get qaCloser => '靠近一些，使商品约占屏幕 70%';

  @override
  String get qaFarther => '远离一些，使商品约占屏幕 70%';

  @override
  String get checkoutPromoApply => '应用';

  @override
  String checkoutPromoApplied(String amount) {
    return '折扣 −$amount ₽';
  }

  @override
  String get checkoutPromoInvalid => '优惠码无效';

  @override
  String get campaignBannerDismiss => '关闭';

  @override
  String get campaignBannerCta => '了解更多';

  @override
  String get companyDefaultName => '公司';

  @override
  String get paymentStatusPending => '待支付';

  @override
  String get paymentStatusSucceeded => '已支付';

  @override
  String get paymentStatusCanceled => '已取消';

  @override
  String get draftRestoreTitle => '恢复草稿？';

  @override
  String draftRestoreBody(String count) {
    return '找到 $count 个云备份（TTL 7 天，§3.3.2）。恢复未完成的拍摄？';
  }

  @override
  String get draftRestoredSnackbar => '已从云端恢复草稿';

  @override
  String get resumeDraftTitle => '未完成的拍摄';

  @override
  String resumeDraftBody(String category, String count, String total) {
    return '您有草稿（$category，$count/$total 帧）。继续还是重新开始？';
  }

  @override
  String get resumeDraftDiscard => '重新开始';

  @override
  String get resumeDraftContinue => '继续';

  @override
  String get mvSearchHint => '按名称搜索';

  @override
  String get mvFilterTierAll => '全部套餐';

  @override
  String get mvFilterAuthorAll => '全部作者';

  @override
  String get mvFilterAuthor => '作者';

  @override
  String get mvClearDates => '清除日期';

  @override
  String get balancePresetsLabel => '已保存视图';

  @override
  String get balanceSavePreset => '另存为…';

  @override
  String get balancePresetNameHint => '视图名称';

  @override
  String get balancePresetSaved => '视图已保存';

  @override
  String get balancePresetDeleted => '视图已删除';

  @override
  String get balanceApplyPreset => '应用';

  @override
  String get profileSessionsSection => '活跃会话 §19.14.4';

  @override
  String get profileSessionRevoke => '终止';

  @override
  String get profileSessionsRevokeOthers => '终止其他会话';

  @override
  String get profileSessionsRevokeOthersDone => '已终止其他会话';

  @override
  String get profileSessionsEmpty => '没有其他活跃会话';

  @override
  String get profileDisable2fa => '禁用 2FA';

  @override
  String get profileDisable2faTitle => '禁用 2FA？';

  @override
  String get profileDisable2faBody => '请输入验证器应用中的代码以确认。';

  @override
  String get profile2faDisabledSnackbar => '2FA 已禁用';

  @override
  String get mvApiUploadTitle => 'API 上传';

  @override
  String get mvApiSkuLabel => 'SKU';

  @override
  String get mvApiUploadBtn => 'API 上传';

  @override
  String get mvLoadMore => '加载更多';
}
