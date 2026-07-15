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
}
