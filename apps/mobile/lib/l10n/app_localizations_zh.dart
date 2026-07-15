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
}
