---
name: ehire-env-login
description: 切换 Ehire 调试包的系统 Wi-Fi 代理到 QA/DEV 环境，并用内部短信验证码登录网才或商业化测试账号进入主页；已在主页时先退出再登录。用户要求切换 QA/DEV 环境、登录网才/商业化测试账号、或执行四组「环境×账号」登录组合时使用。
---

# Ehire 环境切换与测试账号登录

把「改系统设置里的主机名 → 启动 App → 退出旧账号 → 手机号验证码登录」串成可重复执行的流程。仅适用于 **debug 包**（登录页底部有「域账号环境 / 系统代理」调试区）。

## 账号矩阵

| 账号类型 | `--product` | QA 环境 `10.100.2.150:3128` | DEV 环境 `10.100.6.106:3128` |
| --- | --- | --- | --- |
| 网才 | `wangcai` | 13501010102 | 18516139412 |
| 商业化 | `commercial` | 17717845700 | 13348296722（绑定多个企业，会停在「切换企业」页） |

## 实测状态

已在 vivo V2408A（Android 16）上跑通：

| 组合 | 结果 |
| --- | --- |
| 网才 + QA | 通过（含极验自动滑动、内部短信自动填码） |
| 网才 + DEV | 通过 |
| 商业化 + QA | 通过（极验自动滑动） |
| 商业化 + DEV | 登录请求成功，但 13348296722 绑定多个企业，App 停在「切换企业」页；脚本已能识别并提示，需人工点一个企业的「登录」 |

## 一键执行（推荐）

```bash
cd <workspace>
python3 .trae/skills/ehire-env-login/scripts/login.py --product wangcai --env qa
python3 .trae/skills/ehire-env-login/scripts/login.py --product commercial --env dev
```

也支持中文：`--product 网才 --env qa`、`--product 商业化 --env dev`；`--phone` 可覆盖默认号码。

脚本做的事：切换系统代理 → 启动 App → 若在主页则退出到登录页 → 输入手机号 → 获取短信验证码 → 极验出现则自动滑动 → 内部短信平台自动填码 → 校验进入 `EhireHomeActivity`。

## 前置条件

1. 设备已连接并在 `adb devices` 中为 `device`。
2. 已安装 Ehire debug 包（`com.job.android.ehire`）。
3. 目标环境的内部短信域账号已登录：登录页调试区显示「域账号环境：QA环境/DEV环境 · 已登录」。
   - 若显示「未登录」，先在登录页点击「登录」完成 SSO（该步骤需要人工账号密码，不写入脚本），再重跑命令。
4. 设备已连接 Wi-Fi（代理按当前 Wi-Fi 网络生效）。

## 分步执行（排查时使用）

### 1. 切换系统代理

```bash
python3 .trae/skills/ehire-env-login/scripts/switch_proxy.py qa    # 10.100.2.150:3128
python3 .trae/skills/ehire-env-login/scripts/switch_proxy.py dev   # 10.100.6.106:3128
```

实际修改路径：设置 → WLAN → 当前网络 → 代理 → 手动 → 主机名/端口（与手工操作一致；设备未 root，不能用 `settings put global http_proxy`）。

App 在登录页会通过 `SystemProxyHelper` + 2 秒轮询读取 `LinkProperties.httpProxy`，自动把域账号环境切到同名环境。

### 2. 检查/处理极验

```bash
python3 .trae/skills/ehire-env-login/scripts/geetest.py --check   # 有极验/无极验
python3 .trae/skills/ehire-env-login/scripts/geetest.py           # 自动滑动
```

原理：截屏后在验证弹窗图片区找最暗的拼图缺口，按「缺口左边 − 拼图块初始左边」换算拖动距离，`adb swipe` 拖动；失败自动微调重试 4 次。

### 3. 登录

```bash
python3 .trae/skills/ehire-env-login/scripts/login.py --product wangcai --env dev
```

## 关键判断

- 主页：`topResumedActivity` 为 `com.ehire.android.pages.EhireHomeActivity`。
  - 网才底部入口：人才管理 / 人才望远镜 / 人才搜索 / 消息 / 我的
  - 商业化底部入口：人才推荐 / 搜索人才 / 会员中心 / 消息 / 我的
- 登录页：`com.job.android.pages.loginregister.LoginRegisterActivity`，含「获取短信验证码」。
- 退出登录路径：我的 → 右上角设置图标 → 滚动到底部 → 退出登录 → 确定。
  - 右上角图标按从右往左尝试，命中 `SettingActivity` 即停止（网才/商业化图标数量不同，商业化最右侧是积分入口）。
- 退出登录会走本地清理（网络失败也会回登录页），所以「先切代理、再退出旧账号」是安全的。
- 登录成功后内部验证码助手会轮询 90 秒并自动填充；脚本等待主页最长 150 秒。
- 登录前会 force-stop 重启一次 App，避免单实例 `EhireLaunchActivity` 错误页复用时新 token 不生效（表现为「未获取到登录信息」）。
- 若停在 `SwitchCompanyActivity`（切换企业），说明该手机号绑定了多个企业：脚本会立即提示，人工点一个企业的「登录」即可进入主页。

## 故障排查

| 现象 | 处理 |
| --- | --- |
| 登录页显示「未登录」 | 点「登录」完成对应环境 SSO，再重跑 |
| 极验反复失败 | 看 `/tmp/ehire_geetest.png` 截图；重跑 `geetest.py`；仍失败则人工拖动后重跑登录 |
| 提示请求过于频繁 | 点登录页「清除QA环境验证码」或「清除DEV环境验证码」，等 10 秒再重跑 |
| `uiautomator dump` 报 could not get idle state | 页面持续动画时会一直失败；脚本对「我的」页已加坐标兜底，其它页面等 2 秒重试即可 |
| 主页出现升级/权限弹窗 | 脚本自动点「我知道了 / 允许 / 跳过」；新弹窗文案需补充到 `login.py` 的 `handle_popups` |
| 停在「切换企业」页 | 该账号绑定多个企业，人工点第一个企业的「登录」；下次可换单企业账号跑全自动 |
| 系统设置文案不同 | 脚本按文本查找；非 vivo/中文系统需调整 `switch_proxy.py` 的文案 |

## 验证与收尾

```bash
adb shell dumpsys activity activities | grep topResumedActivity
```

- 成功：`EhireHomeActivity`，且登录页调试区显示「系统代理：QA环境 · 10.100.2.150:3128」（或 DEV 对应 IP）。
- 失败时先看当前 activity 和登录页「域账号环境 / 系统代理」两行文本，不要反复盲试。
- 测试完成后如设备需要归还，把代理留在目标环境即可；不需要额外清理。

## 已知限制

- 代理切换依赖系统设置 UI，已按 vivo V2408A（Android 16）的中文文案实测；其它 OEM/语言需微调文本。
- release 包没有内部验证码助手，无法自动取码，本 skill 不适用。
- 极验缺口识别基于亮度对比，极端暗色背景可能失败，此时按提示人工完成一次即可。
