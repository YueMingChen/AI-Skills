# 商业化简历详情场景清单

`debug.ehire.mock` 的已验证场景（scene_shot.py 第一个参数）。路径以 `ModuleResume/.../resumedetailonl/` 为根。

| scene | 触发位置 | 产出 |
|---|---|---|
| lock | `vm/OnlResumeVM.checkResumePrivilege()` 直接返回 false 并 `showNoPrivilegeLiveData=true` | 无查看权限挡板 |
| compass | `vm/OnlResumeVM.getCompassInfo()` 成功回调改 `free=false; compassRights=false; vip=false`，并 `show=true` | 人才罗盘付费/领取态 |
| more | `OnlResumeFragment` → `mViewModel.showMoreBtn()` | 更多操作弹层 |
| share | `OnlResumeFragment.showShareDialog()`（原 private 改 internal） | 分享弹层 |
| jobselect | `OnlQuickChatHelper().startPositionSelectActivity(...)` | 选择职位半屏 |
| account | `OnlQuickChatHelper().showAccountManagerDialog(...)` | 完善信息/账号弹窗 |
| gift | `ARouter RouterPath.Home.ModuleHomeService?.showClaimFreeGiftPackageDialog(...)` | 免费礼包弹窗（ARouter 服务为空时无弹窗） |
| screenshot | `OnlResumeDetailVM.pm.screenShotTipShow.set(true)` | 截图提示浮层，实际文案是「保存投递信息」 |
| phoneguide | `mViewModel.pm.showPhoneGuide()` | 电话引导气泡 |
| newtask | `showNewTaskGuideLiveData.postValue(true)` | 底栏新手引导 |
| interview | `Intent(OnlInterviewActivity)` + JOBID/JOBNAME/COID/CONAME/ACCOUNTID/USERID/NAME/FROMMODULE | 面试邀约页（参数不全时页面可能立即结束） |
| vipunlock | `OnlDownloadResumeVipUnlockDialog(activity, "", "非会员", "", null, {}, {})` | 会员解锁弹窗 |
| auth | `ARouter RouterPath.Resume.OnlResumeCallShowAuthenticationActivity` | 实名认证提醒页 |
| pdf | `mViewModel.queryAsset()` | PDF 导出链路；无独立预览页，最终是分享弹层 |
| wechat | `vm/OnlBottomViewModel` 强制 `resume.ischangewechat = "1"` | 底栏「交换微信」按钮（否则显示「邀请投递」） |
| phoneab | `vm/OnlBottomViewModel` 强制 HR 类型 1 分支 | 底栏「获取电话」按钮（AB 实验分组） |
| skilltag | 打开技能标签弹窗 | 技能标签（技能 / 经验） |
| dynamic | 打开操作动态页 | 全部动态 / 简历评价 |
| callguide | 虚拟号拨打后引导 | 「自动打招呼 / 一键回拨」 |
| attach | `OnlPdfResumeShowActivity` + `attachmentType=1` + 本地 PDF | 附件简历全屏预览 |
| attachpf | `OnlPdfResumeShowActivity` + `attachmentType=0` + 本地 PDF | 附件作品全屏预览 |

## 实现要点

- 场景分发集中在 `OnlResumeFragment.initLiveData()` 末尾的 `applyDebugMockIfNeeded()`，`postDelayed` 2500ms 等页面渲染后再触发。
- 数据类场景（lock / compass / wechat / phoneab）优先改 ViewModel 数据或优先级判断，不要伪造整页 UI。
- 弹窗类场景直接调用真实业务组件，保证截图里的样式与线上一致。
- 依赖本地数据的场景（attach / attachpf / pdf）在 ViewModel 里按场景加载预置文件，避免依赖候选人是否真的投递过附件。
- 每个场景跑完要清理返回栈，否则下一个场景可能截到上一个页面。
