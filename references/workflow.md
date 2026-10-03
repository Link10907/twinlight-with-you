# 工作流与工件边界

Lite 的执行见 `AGENT.md`；这里保存严格模式的内部步骤。两种模式都从当前人的授权资料开始，且采用 `references/art-direction.md` 的原型与原生独立图层流程。命令由宿主执行，不要求用户操作 JSON 或证据偏移。

## 严格模式：准备与来源

使用 `prompts/00-intake.md`，确认可用文件、资料范围、稳定匿名 owner ID、当前总结者、角色/照片授权与分享意图。已经明确的偏好与授权不用重复询问。记忆是查找线索，不是用户消息或原始导出；不得将其重包成原始逐句证据。

当前对话材料可按文档中的 generic JSON adapter 整理，保留真实可见角色与消息 ID，并标 `current_chat`。不声称读取不可见聊天、删除记录、账户全量历史或图片/语音证据。导出分支不明或形状不支持时报告缺口，不猜格式或换用 demo。

每人独立 `private/<run>/` 与输出目录；不读取 `examples/` 的人物内容，不复用别人的 layout、卡图、approval。固定模板与结构 schema 可复用。

## 规范化与分块

```bash
python scripts/twinlight.py ingest private/<run>/history-input.json --format auto --out private/<run>/history.json
python scripts/twinlight.py chunk private/<run>/history.json --out private/<run>/chunks
python scripts/twinlight.py init-analysis private/<run>/history.json --owner-id <本次owner> --name <昵称> --out private/<run>/analysis.json
```

实际总结者 metadata 已知时传入对应 `--provider` 与 `--attribution-source`；模型版本未知留空。不能因为 export 来自 Claude 就把 GPT 写的摘要署名为 Claude，也不能照抄示例供应商。

每个 map worker 阅读整个分配块及必要邻近上下文，按 `prompts/01-extract.md` 和 `schemas/chunk-result.schema.json` 输出。每块恰有 `chunk_path`、`chunk_sha256`、`history_digest`、`facts` 与 `message_dispositions`。每条用户消息要有事实或排除理由；助手文本不能独立证明用户成就。

不手工数字符。先填 `message_id + quote`，重复引文加 0-based `occurrence`，由程序计算偏移和 hash：

```bash
python scripts/twinlight.py anchor private/<run>/history.json private/<run>/chunk-results/chunk-0001.json --out private/<run>/chunk-results/chunk-0001.json
python scripts/twinlight.py validate-chunk private/<run>/history.json private/<run>/chunks/manifest.json private/<run>/chunk-results/chunk-0001.json
python scripts/twinlight.py merge-extractions private/<run>/history.json private/<run>/analysis.json private/<run>/chunks/manifest.json private/<run>/chunk-results --out private/<run>/analysis.json
```

引用位置为完整消息的绝对字符位置；片段内位置需要加 `segment.start`。超长消息先回读完整/邻近片段，不能据半句话定性。

合并验证所有块恰有一个结果、摘要与源一致及用户片段处置。相同 fact ID 只在语义字段一致时合并引用；矛盾显式修正，不能最后写入者获胜。合并后清空旧 themes/card，防止旧故事套新证据。修复出错候选与处置，不改 hash 或关闭校验绕过。

## 消歧、叙事与审查

按 `prompts/02-reconcile.md` 合并同义事实，保留证据。区分本人、第三方、引用、角色扮演、问题、计划和成果。纠错用 `supersedes`，未决矛盾不进公开文本。消息日期不等于事件日期，未知日期保持未知。

按 `prompts/03-narrative.md` 填 analysis：1–8 个真实支持的主题，每主题 0–8 个话题。不用题材热度推断能力，不为了页面整齐凑固定组数。没有可支持主题时交付材料缺口，不生成填充经历。

每句公开文案、主题和卡片解读都引用本次可发布 fact IDs；正确引文不自动证明总结语义。卡片按 `prompts/04-character-card.md` 个性化，SSR 恒定，称号是有限印象而非人格测评。

```bash
python scripts/twinlight.py verify private/<run>/history.json private/<run>/analysis.json --all-errors --out private/<run>/audit.json
python scripts/twinlight.py review private/<run>/history.json private/<run>/analysis.json --out private/<run>/review.md
python scripts/twinlight.py compile private/<run>/history.json private/<run>/analysis.json --out private/<run>/compiled
```

给用户看资料范围、归属或状态争议及全部公开文字，取得本人对当前内容的确认。analysis 中 `accepted` 是分析者核对，不是本人发布许可。修订后重新校验，保持语义 IDs 稳定。

## 同一生图流程与构建

```bash
python scripts/twinlight.py art-brief private/<run>/history.json private/<run>/analysis.json --out private/<run>/art-brief.json
```

只把最少视觉 brief 交给实际授权的图像工具，先直接生成无字原型，再参考它直接生成同画布完整 background、原生透明 subject/effects/可选 spirit。禁止抠图、绿幕去底、棋盘转 alpha、裁剪重摆或重复整图。text/SSR 程序独立排版，lineart 同像素派生。详细尺寸、depth 和验收见 `references/art-direction.md`。

```bash
python scripts/twinlight.py validate-art private/<run>/card/layers.json
python scripts/twinlight.py build private/<run>/history.json private/<run>/analysis.json --layers private/<run>/card/layers.json --out outputs/<run>
```

图层须绑定本次 persona。实际看正面、左右、透明边和被遮挡背景，视觉核对后才设 `art_status=approved`。像素校验器不会替人判断美感或身份准确。

只有原型如实标为静态插画；构建路径不支持静态时，单独交付原型，页面保留明确占位。没有生图工具就交付 brief 与占位，不假称完成分层或 Blender。读取 `references/preview.md`，在宿主可用预览中打开生成文件；检查浏览器载入与基本交互，未运行的检查标明。

## 本人决定发布

草稿和本人内容确认不等于公开许可。本人确实看过并同意当前文字与最终图层公开时，才记录：

```bash
python scripts/twinlight.py approve private/<run>/history.json private/<run>/analysis.json --by <本人昵称> --scope share --layers private/<run>/card/layers.json --ack-reviewed --out private/<run>/approval.json
python scripts/twinlight.py build private/<run>/history.json private/<run>/analysis.json --layers private/<run>/card/layers.json --approval private/<run>/approval.json --out outputs/<run>-release
```

该收据绑定文本与图片字节，是本地记录，不是身份认证或法律证明。改动需重审；发布站点、仓库或文件仍需要明确指令。

## 工件和增量

| 工件 | 内容与边界 |
|---|---|
| history / chunks / chunk-results | 私人原文与局部判断，不放公开包 |
| analysis / review / approval | 事实、引用、本人确认；留在私人目录 |
| compiled profile / layout / HTML | 所选公开摘要与图像，仍可能识别个人 |
| card-spec / prototype / layers | 当前人的视觉 brief、原型与独立素材 |
| audit / browser / report | 实际检查记录，按需给本人，默认不发布 |

`private/`、`runs/`、`outputs/` 默认不入 Git；整包发给本人不等于允许公开推送。CLI 无网络也不代表宿主 AI 全流程离线。

增量更新仅限同一确认 owner。新导出单独规范化，原生消息同 ID 内容变更需核查；重新锚定 ledger 引用与 hash，不能只替换 history_digest。更新事实与冲突，再按受影响内容重写叙事和卡图 brief。使用 `--layout-lock` 保留既有位置与语义 IDs，超限时显式合并而非截断。

冻结证据、分析、素材和 layout lock 后编译可复现；不同模型独立解释仍可能不同。效果实验比较支持性、错误归属、状态、遗漏与可用性，而不是要求措辞完全相同。
