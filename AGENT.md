# Twinlight · HTML 执行

目标是当前用户的实际单文件 HTML。此流程整理个人内容、构建和展示星系页面，不调用图像工具，也不等待独立闪卡流程。

## 准备与内容

找到实际项目目录；缺资源时在获准的工作目录取得完整仓库 https://github.com/Link10907/twinlight-with-you 。使用现有 Python 3.10+ 与 requirements，必要时在允许的虚拟环境安装。不要要求用户克隆、安装 skill 或逐条执行命令，也不修改全局 skill 配置。

每个人独立工作目录。依据本次授权资料和可见对话写 `twinlight.json`，字段见 `references/lite-content.md`；card 字段用于页内身份文字，不要求生图提示或图片。本人/他人、问题/能力、计划/成果分别核对；没有资料不借用 examples 补全。署名是当前实际总结者。

展示全部页面文字，由本人确认；已有对当前文字的明确确认继续沿用，不代确认。命令里的 `PY`、`TL` 分别代表实际 Python 与项目 `scripts/twinlight.py` 的绝对路径，供 AI 自己执行。

## 构建

```bash
PY TL lite-check <本次目录>/twinlight.json
PY TL lite-build <本次目录>/twinlight.json --out <本次目录>/site --confirmed
```

修复实际报错后重试。没有卡图也构建完整星系 HTML；页内艺术卡如实标为占位，HTML 已交付不等于闪卡已制作。`--confirmed` 仅在当前文字确已由本人确认后使用。

明确要求逐句原话出处时，按 `references/workflow.md` 的 strict 提取、核对与 build 接口；同样不把闪卡生图作为 HTML 前置任务。旧 `start/next/check` 是保留的串行兼容接口，两个独立流程不使用它。

## 仅消费完成的闪卡

用户要求导入现成闪卡时，只接受对应人物的已完成图层包；使用完整 layers.json 与图片，不在 HTML 流程内修图或重新生图：

```bash
PY TL lite-build <本次目录>/twinlight.json --layers <卡包目录>/layers.json --out <本次目录>/site-with-card --confirmed
```

导入失败只报告包/绑定错误，独立保留原 HTML。修改或重画卡片回到 `CARD.md`；更改个人内容也不自动重跑卡片。

## 交付

按 `references/preview.md` 检查真实 `site/index.html`、本人内容与内嵌资源，先提供有效文件链接/附件，再打开同一文件的可用预览。保留 V10 星系、双星交汇与揭卡；未做的交互检查明确记为未验证。检查已有卡图仅是消费验收，不接管生图。

最终只需 HTML 入口与实际验证情况；JSON、命令和报告为内部或可选工件。没有实际文件就不能宣布完成，纯截图不能代替交付。内容确认不等于公开发布，边界见 `references/privacy.md`。
