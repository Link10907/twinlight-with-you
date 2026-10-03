# Twinlight · 与你同光

**把有出处的记录，变成一片可以探索的星系。**

这是一个可复用 Agent Skill + 本地编译器。页面沿用 Twinlight V10 的交互与视觉结构；不同的人只替换经过审查的内容、确定性布局和独立分层卡图。仓库不附带任何真实用户的聊天、照片、人物总结或私人卡面。

> 当前版本：1.0.0。示例完全虚构。演示里的星盘是明确标注的分层占位素材，不是假装生成好的专属人物插画。

## 先运行示例

需要 Python 3.10+。Node.js 用于 JS 语法检查；Chromium + Playwright 用于浏览器测试，不是普通用户打开页面的前提。

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell 对应：.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/twinlight.py demo --out outputs/demo
```

用浏览器打开 `outputs/demo/index.html`。文件内嵌本地素材，不请求 CDN、分析服务或模型接口。源历史不会自动上传。`profile.json` 仍然包含个人摘要，不应把本地输出目录默认公开。

将整个仓库目录作为 `twinlight-with-you` 放入宿主支持的 Skills 目录，或让宿主读取根目录 `SKILL.md`。目录位置因宿主而异。本 Skill 使用标准 `SKILL.md` + `scripts/` + `references/` + `assets/` 结构，不声称所有产品会自动识别安装。

对宿主说：

> 使用 twinlight-with-you。先说明你能读取哪些历史；按证据提取，不要把我的提问写成能力。生成本地审查稿，保持固定模板，审查后再生成人物分层卡。

## 工作分工

```text
显式提供的历史 JSON
  → 本地规范化 / 选定分支 / 分块与覆盖清单
  → 宿主 AI：逐块提取，有证据的事实与排除理由
  → 合并与纠错：计划、问题、成果、第三方内容分开
  → 受 JSON Schema 约束的主题 / 叙事 / SSR 人物理解
  → 机械审计 + 本人审查
  → 确定性布局 + 独立分层人物生图
  → 固定网页模板 → 本地预览 → 明确许可后分享
```

**Python 不会替 AI 理解文意，也不会偷偷调用外部模型。** 它负责规范化、引用核对、冲突检查、稳定排列和构建。宿主模型负责语义判断与可用的图像工具调用。缺少图像能力时只交付生图 brief 和待生成占位状态。

## 准确提取如何落地

每条事实含 `message_id`、原文 SHA-256、字符起止位置、原话、事实类型、语境和审查状态。每条用户消息都必须有处置记录：提取了哪些事实，或为何排除。每句公开文案和每个主题、卡片关键词都要指回可发布事实。

程序会阻止引用助手话语、原话改写、偏移错误、陈旧摘要、未处置的消息、未解决的当前状态冲突、把计划标为已完成、发布敏感/被替代事实。**它不能机械证明一段原话真的蕴含某个总结**，因此提供 `review.md` 做语义复核，不宣称“100% 准确”或“读过所有历史”。

更多：[`references/extraction.md`](references/extraction.md)、[`prompts/`](prompts/)、[`schemas/`](schemas/)。

## 星体数量和位置

主星对应稳定主题，支持 **1–8 颗**；每颗主星的主题行星支持 **0–8 颗**。通常 3–6 个大主题更易读，但资料只有一个主题时不补齐。一次提问不自动产生一颗“掌握该技能”的星；反复重复同一问题也不会膨胀成很多颗星。

主题/行星语义 ID 与 owner ID 生成稳定种子；同一分析结果的排列可复现。增量更新使用 `layout.lock.json` 保留已有坐标、轨道和材质。尺寸最多轻微表达记录跨度，不是熟练度、人格分数或比较排名。详见 [`references/layout.md`](references/layout.md)。

## 保留的体验

首页为有旋转与流动感的个人光点星系；靠近主星后才展现行星。选中使用主体发光，不套硬圈。14 秒终章依次展示 AI 星系点亮、交融、实际总结者署名的提问、SSR 卡。允许暂停、跳过和减动效；开启音乐需要用户交互。

卡片前景、人物、背景具有独立视差，文字/边框钉在卡面；镭射随观察方向变化。公式改编自 MIT 授权的 RuiC-card-skill，保留完整署名。本仓库**没有运行或交付其 Blender/GLB 流水线，也不把 2.5D 卡面叫作完整三维人物模型**。

## 真实资料的本地流程

把个人材料放在 `.gitignore` 排除的 `private/`。

```bash
python scripts/twinlight.py ingest private/history-input.json --out private/history.json
python scripts/twinlight.py chunk private/history.json --out private/chunks
python scripts/twinlight.py init-analysis private/history.json \
  --owner-id your-stable-id --name 你的昵称 \
  --provider openai --attribution-source host_metadata --out private/analysis.json
```

上面的 OpenAI 只适用于确实由 GPT 生成这次总结。Claude 应传 `--provider anthropic`；未知则保持默认 `unknown`，不要照抄。版本不知道就不填 `--model`。

由宿主按提示词完成分析；分块可先输出批次结果，再运行：

```bash
python scripts/twinlight.py merge-extractions private/history.json private/analysis.json \
  private/chunks/manifest.json private/chunk-results --out private/analysis.json
# 随后按提示词消歧、纠错，填写 themes 和 card。
python scripts/twinlight.py verify private/history.json private/analysis.json
python scripts/twinlight.py review private/history.json private/analysis.json --out private/review.md
python scripts/twinlight.py art-brief private/history.json private/analysis.json --out private/art-brief.json
python scripts/twinlight.py build private/history.json private/analysis.json --out outputs/preview
```

没有提供图层时明确显示待生成；不能点击导出成“已审核个人卡”。实际生图完成、真透明度和左右视角均核对后：

```bash
python scripts/twinlight.py validate-art private/card/layers.json
# 只有本人确实同意文本与图像公开时才执行下面的许可记录：
python scripts/twinlight.py approve private/history.json private/analysis.json \
  --by 你的昵称 --scope share --layers private/card/layers.json \
  --ack-reviewed --out private/approval.json
python scripts/twinlight.py build private/history.json private/analysis.json \
  --layers private/card/layers.json --approval private/approval.json \
  --out outputs/release
```

图层清单的 `art_status=approved` 由实际视觉审查决定，校验器不会自动改它。许可绑定分析与素材字节；改一处需重审。许可收据不是身份认证、法律证明或防复制技术。详见 [`references/privacy.md`](references/privacy.md)。

## 测试

```bash
python -m unittest discover -s tests -v
python scripts/twinlight.py demo --out outputs/demo
node --check outputs/demo/compiled-check.js
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/verify_browser.py --html outputs/demo/index.html --out verification/browser
python scripts/check_capacity.py
```

浏览器脚本记录 WebGL 是否可用，降级情况下不会把 CSS 结果报成 GPU 着色器通过。`--require-webgl` 可让 CI 在缺少完整 GPU/软件 WebGL 时失败。测试使用虚构数据，不能替代真实用户语义准确率评估。

## 目录

```text
SKILL.md                     宿主执行入口
prompts/                     提取、消歧、叙事、生图、审查
schemas/                     分析、证据、历史、布局、图层、许可契约
scripts/twinlight.py          命令行入口
scripts/twinlight_core/       本地规范化、审计、编译、素材与布局
assets/template/             固定 V10 衍生前端、程序纹理与原创合成配乐
assets/ai-history.json       少量可核验的 AI 历史锚点，不是完整发展年表
examples/demo/              完全虚构的端到端示例
references/                 工作流、隐私、画面与来源说明
tests/                      回归测试
```

## 已知边界

只内置文档列明的 ChatGPT mapping、Claude chat_messages 与 generic JSON 文本适配器；不扫描账户、不读取删掉的聊天、不分析导出中的图片/语音，不把格式失败解释为没有历史。模型自由写作仍有随机性；冻结的分析和素材才是确定性编译输入。网页运行时导入新的 profile 不会自动生图，必须在本地重建并重新审核。

模板保留 V10 分阶段覆盖模块以减少视觉回归，尚不是组件化前端框架。顶多八个主题是明确容量约束，不是心理学分类。星系/行星是艺术表达，不是引力模拟。生产部署、真机性能与真实语料语义评估仍需单独完成。

## License

本仓库原创代码采用 MIT；第三方公式和代码见 [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md)。不分发字体、官方游戏角色或真实用户素材。用户照片与生成图的权利取决于素材授权和工具条款，不自动继承代码许可。
