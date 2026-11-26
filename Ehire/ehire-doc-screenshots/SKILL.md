---
name: ehire-doc-screenshots
description: Ehire 排期与需求文档截图适配层。按全局 android-doc-screenshots 的通用流程执行，提供本项目构建、mock 属性、场景触发点与场景清单。当为 Ehire 文档补截图或 mock 商业化简历详情场景时使用。
---

# Ehire 适配层

先加载全局 skill `android-doc-screenshots`，按它的锚点、采集、校验、嵌图流程执行。这里只写本项目差异，通用方法不重复。

## 构建与安装

- 确认 `BUILD_EHIRE_WITH_AAR`、`BUILD_IM_WITH_AAR`。改动业务模块时确认 `aar2source.gradle` 的 `SOURCE_MODULES` 包含该模块，否则本地修改不进包。
- 内网 Maven 不可达时用 `sh gradlew :app:assembleDebug --offline`。
- `INSTALL_FAILED_ABORTED` 时在手机上点「继续安装」。
- 商业化简历详情依赖商业化账号；虚拟号、会员态、实名状态会改变页面结构。

## 截图入口

- 脚本：`docs/商业化简历详情RN改造/screenshots/scene_shot.py`，行为是回首页 → `setprop` 场景 → 点第一个候选人 → 等待 → 截图。
- 嵌图脚本：同目录 `embed_screenshots.py`，只改 D 列并按最多 3 张图算列宽。
- 文档：`docs/商业化简历详情RN改造/商业化简历详情RN改造排期.xlsx`。

## Mock 约定

- 属性名：`debug.ehire.mock`。
- 读取：`OnlDebugMock` 反射 `SystemProperties.get` 实时读取；不要用 `System.getProperty`。
- 分发：`OnlResumeFragment.initLiveData()` 末尾的 `applyDebugMockIfNeeded()`，`postDelayed` 2500ms 等渲染完成。
- 数据类场景改 `OnlResumeVM`（权限态、罗盘）/ `OnlBottomViewModel`（交换微信、电话 AB 分组），复用真实 UI。
- 场景与触发位置清单见 `references/scenes.md`。

## 文档结构注意

- 排期表行结构可能被用户调整（合并、插入），截图前先按 C 列功能名重建行号映射。
- 图片锚点不会随行移动，结构变更后必须重嵌并校验。
- 企业微信在线表格无法自动化插图，按通用 skill 的交付方案处理，不要在线文档上硬试。

## 清理清单

交付或合入前移除：

- `ModuleResume/.../resumedetailonl/util/OnlDebugMock.kt`
- `app/src/com/job/android/ehire/application/DebugMockProxy.java` 及 `AppMain` 中的调用
- `app/res/raw/` 内置 mock 证书、`network_security_config.xml` 的 `debug-overrides`
- 各文件中 `applyDebugMockIfNeeded` 场景分支，以及为 mock 放宽的 `private → internal`
- `docs/商业化简历详情RN改造/mock/` 下的代理 mock 脚本（如已废弃）
- 设备侧：`debug.ehire.mock` 属性、`files/ehire-pdf-cache/*_mock.pdf`、mock_scene/proxy 文件
- 清理后跑一次 `sh gradlew :ModuleResume:compileDebugKotlin --offline` 验证
