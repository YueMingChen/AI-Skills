#!/usr/bin/env bash
# vivo 自动确认安装方案 - 一键安装脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${VIVO_INSTALL_DIR:-$HOME/projects/vivo-auto-install}"

if [ -n "${TRAE_SKILLS_DIR:-}" ]; then
  SKILL_ROOT="$TRAE_SKILLS_DIR"
elif [ -d "$HOME/.trae-cn" ]; then
  SKILL_ROOT="$HOME/.trae-cn/skills"
elif [ -d "$HOME/.trae" ]; then
  SKILL_ROOT="$HOME/.trae/skills"
else
  SKILL_ROOT=""
fi

echo "==> 检查源文件"
for f in "$SCRIPT_DIR/vclick.py" "$SCRIPT_DIR/skill/vivo-auto-install/SKILL.md"; do
  if [ ! -f "$f" ]; then
    echo "缺少文件: $f"
    exit 1
  fi
done

echo "==> 安装脚本到 $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/vclick.py" "$INSTALL_DIR/vclick.py"
chmod +x "$INSTALL_DIR/vclick.py"

if [ -n "$SKILL_ROOT" ]; then
  echo "==> 安装 Trae skill 到 $SKILL_ROOT/vivo-auto-install"
  mkdir -p "$SKILL_ROOT/vivo-auto-install"
  sed "s#@SCRIPT_PATH@#$INSTALL_DIR/vclick.py#g" \
    "$SCRIPT_DIR/skill/vivo-auto-install/SKILL.md" \
    > "$SKILL_ROOT/vivo-auto-install/SKILL.md"
else
  echo "==> 未检测到 Trae，跳过 skill 安装（可设置 TRAE_SKILLS_DIR 手动指定）"
fi

echo "==> 校验"
python3 -m py_compile "$INSTALL_DIR/vclick.py"
python3 "$INSTALL_DIR/vclick.py" --help >/dev/null
if [ -n "$SKILL_ROOT" ]; then
  grep -q "$INSTALL_DIR/vclick.py" "$SKILL_ROOT/vivo-auto-install/SKILL.md"
fi

if command -v adb >/dev/null 2>&1; then
  echo "==> adb: $(command -v adb)"
else
  echo "警告: 未找到 adb，请先安装 Android SDK Platform-Tools 并加入 PATH"
fi

echo
echo "安装完成"
echo "  安装 APK  : python3 $INSTALL_DIR/vclick.py /path/to/app.apk"
echo "  Studio 模式: python3 $INSTALL_DIR/vclick.py --watch"
echo "  新开一个 AI 对话后 skill 生效"
