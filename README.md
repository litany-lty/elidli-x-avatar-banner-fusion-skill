# X Avatar–Banner Fusion Skill / X 头像横幅融合技能

这是一个开源、可直接放入 Agent Skills 目录的通用技能。它把“真实头像由 X 平台叠在横幅左下角”的经验做成：**执行规则 + 生成提示词 + 几何校准工具 + 已验证背景参考图**。

## 许可与隐私

代码与示例纯背景以 MIT 许可证发布。仓库不包含任何个人头像或 X 主页截图。成功背景图仅用于展示设计原理；不同用户、设备的精确位置必须根据真实客户端截图重新测量。

## 安装

将 ZIP 解压后的 `elidli-x-avatar-banner-fusion-skill` 文件夹完整放入你使用的智能体技能目录，例如项目内 `.agents/skills/` 或 `.claude/skills/`，并按该客户端要求刷新技能索引。也可以直接让支持 Agent Skills 的智能体读取 `SKILL.md`。无需连接账号或预设 API Key。

仅当需要运行校准脚本时安装 Pillow：

```bash
python3 -m pip install -r requirements.txt
```

支持 Python 3.9+，macOS、Windows、Linux。画图动作使用当前 Agent 的图像生成能力；本包**不携带生成模型或 API**。

## 对智能体说什么

> 使用 elidli-x-avatar-banner-fusion Skill，为我做一张 X 主页横幅。主题是【...】，风格是【...】，颜色是【...】，只生成背景，不改头像；如果我给了主页截图，请先反推头像叠加位置再生成，并提供对位预览。

最少提供主题即可。头像原图可选；完整展开横幅的主页截图可提升精度。

## 零截图快速预览

```bash
python3 scripts/banner_fusion.py report --config references/example_layout.json
python3 scripts/make_demo_banner.py --out output/demo_banner.png
python3 scripts/banner_fusion.py preview \
  --banner output/demo_banner.png \
  --config references/example_layout.json \
  --out examples/reference_with_avatar_guide.png --guide
```

预览里的辅助圆只用于校准，**绝对不是最终背景**。

## 精准获取布局参数（需要实际截图坐标）

```bash
# 可先生成网格，辅助读取像素坐标
python3 scripts/banner_fusion.py grid \
  --image your_profile_screenshot.jpg --out screenshot_grid.png --step 100

# 输入真实截图中的“横幅显示矩形”和头像实际边框圆心、半径
python3 scripts/banner_fusion.py measure \
  --banner-box 0 0 691 230 --avatar 94 278 72 \
  --target 1536 512 --out layout.json

python3 scripts/banner_fusion.py preview \
  --banner new_banner.png --config layout.json \
  --avatar-image avatar.png --out preview.png
```

上例 `691×230`、`(94,278),r=72` 都是**说明参数格式的示意值**，不是所有 X 用户的固定布局。

## 现有背景位置偏高

```bash
python3 scripts/banner_fusion.py shift \
  --input new_banner.png --dy 24 --out banner_lowered.png
```

这是快速位移验证，不是内容智能填充；移动太多会裁断底部。最终高质量版本最好回到图像生成/编辑工具进行局部修正。

## 文件说明

| 位置 | 内容 |
|---|---|
| `SKILL.md` | Agent 执行说明与验收要求 |
| `references/geometry.md` | 正确的头像-横幅坐标变换与相交公式 |
| `references/prompt_templates.md` | 母提示词、精准值插入、偏移修复提示词 |
| `references/example_layout.json` | 单一成功案例的经验性初稿参数 |
| `references/success_case.md` | 从成功案例中提炼的几何与构图规则 |
| `assets/success_reference_1536x512.webp` | 成功案例的 3:1 纯背景示例（不包含头像） |
| `scripts/banner_fusion.py` | 可运行的测量/网格/预览/截屏预览/平移工具 |
| `tests/test_banner_fusion.py` | 自动测试 |

注意：X 不同客户端及版本会调整排版。没有真实应用截图时，任何固定坐标都只是初稿。**成功关键是用叠加后的截图校准，不是无限盲目重新生成。**

## GitHub 项目

https://github.com/litany-lty/elidli-x-avatar-banner-fusion-skill

适配截图优先于固定坐标。使用者需在本地对头像叠加位置进行校准。

## 可复用演示图

`examples/geometry_guide.svg` 是示意图，不包含任何用户头像。`scripts/make_demo_banner.py` 生成的背景仅用于冒烟测试，不代表实际生图质量。公开仓库额外包含经确认的成功纯背景展示素材（已压缩为 WebP）；不包含真实头像、个人主页截图或登录资料。

### 成功背景参考（仅供欣赏与理解视觉结构）

![成功纯横幅示例](assets/success_reference_1536x512.webp)
