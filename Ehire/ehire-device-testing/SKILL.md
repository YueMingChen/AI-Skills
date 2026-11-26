---
name: ehire-device-testing
description: 在真机上验证 Ehire Android 功能改动。用 adb、uiautomator、logcat 核对 UI 文案、点击链路与接口字段并截图留证，输出测试报告。当用户要求真机测试、验证改动或提供测试截图报告时使用。不要用于纯静态代码分析。
---

# Ehire Android 真机测试

在 vivo/小米等真机上验证 Ehire Android 功能改动，覆盖 UI 文案、点击链路、接口字段核对与截图留证。适用于 AGENTS.md 里「验证与交付」环节的真机回归。

## 核心原则

- 先读提交 diff 理解改动与影响范围，再设计测试用例；不确定的字段语义以接口响应和相邻实现为准。
- 测试包必须包含目标改动。当前工作区常有未提交代码（可能编译不过），用独立 worktree 基于目标 commit 构建，避免污染工作区。
- 截图要对应「真实数据分支」，用 logcat 抓接口响应字段确认截图里的候选人是预期场景，不要只看文案。

## 1. 代码改动定位

```bash
git show --stat <commit>            # 看改了哪些文件
git show <commit>                   # 看完整 diff
git log --oneline -S "<字段名>" -- <模块>   # 追溯字段引入历史
```

简历详情附件入口的核心逻辑在 `ModuleResume/.../resumedetail/vm/newui/NewItemAttachmentPM.kt` 与 `NewCellBasicInfoPM.kt`，字段定义在 `resumedetail/bean/JavaResume.kt`。改前先读 `ModuleResume/.../resumedetail/README.md` 确认是 `resumedetail`（网才）还是 `resumedetailonl`（商业化）链路。

## 2. 构建测试包（独立 worktree）

```bash
git worktree add --detach /tmp/ehire_<commit> <commit>

# worktree 里子模块 jobs_ehire_module / jobs_im / im_base 是空目录，
# 必须 rsync 复制源码（用符号链接会触发 packageDebugResources IllegalStateException）
for m in jobs_ehire_module jobs_im im_base; do
  rsync -a --exclude build --exclude .git --exclude .gradle \
    /Users/yuming/projects/EhireProject/$m/ /tmp/ehire_<commit>/$m/
done

cp /Users/yuming/projects/EhireProject/gradle.properties /tmp/ehire_<commit>/gradle.properties
cp /Users/yuming/projects/EhireProject/local.properties  /tmp/ehire_<commit>/local.properties

# 内网 Maven 10.100.6.123:8081 需绕过本机代理，否则 502/连接失败
cd /tmp/ehire_<commit>
sh gradlew :app:assembleDebug \
  -Dhttp.nonProxyHosts=10.100.6.123 \
  -Dhttps.nonProxyHosts=10.100.6.123 \
  -DsocksNonProxyHosts=10.100.6.123 \
  --console=plain
```

产物在 `<worktree>/app/build/outputs/apk/debug/app-debug.apk`。构建完成后 `git worktree remove --force` 清理。

## 3. 真机连接与安装

```bash
adb devices -l                       # 确认 device 在线（离线需重新插拔 USB / adb kill-server && adb start-server）
adb install -r <worktree>/app/build/outputs/apk/debug/app-debug.apk
adb shell monkey -p com.job.android.ehire -c android.intent.category.LAUNCHER 1   # 启动
adb shell dumpsys activity activities | grep topResumedActivity   # 确认前台页面
```

设备可能中途掉线；先 `adb devices -l` 再操作，失败就等几十秒重连。

## 4. UI 自动化定位（uiautomator + 脚本）

```bash
adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1
adb shell cat /sdcard/ui.xml > /tmp/ui.xml
python3 .trae/skills/ehire-device-testing/scripts/uiparse.py /tmp/ui.xml          # 全部节点 text + bounds + 中心
python3 .trae/skills/ehire-device-testing/scripts/uiparse.py /tmp/ui.xml --text 附件   # 过滤关键词
python3 .trae/skills/ehire-device-testing/scripts/uiparse.py /tmp/ui.xml --clickable       # 只列可点击卡片
```

操作命令：

```bash
adb shell input tap <cx> <cy>       # 点击中心坐标
adb shell input swipe 540 1950 540 800 300   # 上滑列表
adb shell input text "649037242"    # 输入文本（先 tap 聚焦输入框）
adb shell input keyevent 4          # 返回键
```

注意：输入框聚焦后键盘弹起会改变下方按钮坐标，需重新 `uiautomator dump` 再取坐标。文本输入用 `input text`，输入后 dump 确认输入框值无多余字符（偶发多一个点号）。

## 5. 接口字段核对（logcat 抓 okhttp）

```bash
adb logcat -c                       # 清空旧日志
# 触发页面/点击动作后
adb logcat -d > /tmp/log.txt
grep -oE '\-\-> (GET|POST) https?://[^ ]+' /tmp/log.txt | sort -u    # 列出请求
grep -oE '"showResumeEnclosure":"[^"]*"' /tmp/log.txt | sort | uniq -c
grep -oE '"hasenclosure":"[^"]*"' /tmp/log.txt | sort | uniq -c
```

简历详情接口是 `resumedtl/getresume`，响应体以 `D axxx` 分行打印（不是单行 JSON）。关键字段：

- `showResumeEnclosure`：是否展示「附件个人信息」入口（"1" 展示）
- `hasenclosure`：候选人是否有附件简历（"1" 有 → 「查看附件」；否则 → 「索要附件信息」）
- `resumeid`：人才 ID，用于与详情页顶部「人才ID」对齐，确认截图对应当前候选人

每次点击/进入页面前先 `logcat -c`，只分析本次动作产生的响应，避免混入相邻候选人数据。

## 6. 测试数据定位（简历详情场景）

- 人才管理列表（我的职位 → 待处理/合适）可用「筛选 → 姓名/ID」输入人才 ID 精准定位候选人。
- 列表卡片中心坐标用 `uiparse.py --clickable` 找 ViewGroup，取 y 中心。
- 进入详情后 dump 确认顶部「人才ID」与预期一致，再核对附件行文案。

## 7. 截图留证与报告

```bash
adb exec-out screencap -p > /tmp/<name>.png
```

- 截图存到 `<workspace>/test-reports/<需求目录>/screenshots/`，文件名带序号与场景，报告用相对路径引用。
- 报告 markdown 放 `<workspace>/test-reports/<需求目录>/`，包含：测试信息表、改动说明、测试数据（含人才ID与字段值）、用例与结果表、截图证据、结论与未覆盖项。
- 同一候选人在改动前后各截一张（旧包 vs 新包），证明文案变化来自本次提交。

## 注意事项

- 点击行为（如发邀请话术、是否跳聊天页）多为存量逻辑，本次需求可能只改文案；真机实测若与预期跳转不一致，先查 `ischat` 等状态是否影响分支，再下结论。
- 图片用 `computer://` 链接，源码/配置用 `file:///` 链接，见全局 File Delivery 规则。
