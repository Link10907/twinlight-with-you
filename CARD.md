# Twinlight · 独立闪卡接口

先读 [references/quality-workflow.md](references/quality-workflow.md)。本模块只做当前人的绘画、原生分层、独立排字与卡片预览，不构建星系叙事。默认被 [AGENT.md](AGENT.md) 在一次请求内调用并自动接入 HTML；模块提示见 [prompts/card-generation.md](prompts/card-generation.md)。

## 输入

完整资源按 `scripts/bootstrap.py --root <目录>` 检查。只读 Lite / card-1 取得 name、summarizer 和 card 的 title、english_title、keywords、tagline、reflection；不为换画风修改人物绑定。实际美术用独立 `art-direction-1` JSON，记录当前偏好、具体场景与适配排字主题，传给 `--art-prompt-file`。旧 20–1500 字 plain brief 仍能做局部诊断，但不满足新版完整卡交付关口。

Strict 继续使用原本只读 analysis/compiled persona 与 [references/workflow.md](references/workflow.md) 审阅接口；不转换成虚构 Lite 身份。视觉规范相同，卡包绑定实际 Strict persona；不能把低层打包结果称作 public run 已验证。

## 原生素材到独立预览

`PY` / `TL` 是实际 Python 和 `scripts/twinlight.py` 路径。以下全是 AI 的内部动作。先完成原型评审，再生成层；具体证据字段见 [references/art-evidence-format.md](references/art-evidence-format.md)。

```bash
PY TL card-spec <只读输入.json> --art-prompt-file <卡片目录>/art-direction.json --out <卡片目录>/card-spec.json
PY <项目>/scripts/art_quality.py check --layers <卡片目录>/layers.json --persona-digest <当前digest> --stage prototype
PY <项目>/scripts/prepare_card_layers.py --data <只读输入.json> --art-prompt-file <卡片目录>/art-direction.json --prototype <卡片目录>/prototype.png --background <卡片目录>/background.png --subject <卡片目录>/subject.png --effects <卡片目录>/effects.png --out <卡片目录>
PY TL validate-art <卡片目录>/layers.json
PY <项目>/scripts/art_quality.py composite --layers <卡片目录>/layers.json --persona-digest <当前digest> --out <卡片目录>/composite.png
PY TL render-card <只读输入.json> --layers <卡片目录>/layers.json --out <卡片目录>/front.png
PY <项目>/scripts/preview_card.py --layers <卡片目录>/layers.json --data <只读输入.json> --out <卡片目录>/preview.html
PY <项目>/scripts/package_card.py --layers <卡片目录>/layers.json --data <只读输入.json> --out <卡片目录>/card.json
```

已生成有内容的 spirit 时，装层传 `--spirit <真实路径>`。没有同伴才用空透明层；脚本拒绝静默覆盖已有非空 spirit。`--font` 可选实际中文字体。文字保持原句，主题控制颜色、边框与底部遮罩；放不下时修构图，不删字。

各层采用工具返回的同一合法 3:4 全画布；背景完全不透明，主体/前景原生透明。不得抠图、裁切、缩放、重摆或重复海报。lineart 从最终 subject alpha 同像素派生，不能自己画一张灰色蒙版代替。SSR 固定不代表能力排名。

## 评审与续跑

依次真实审查无字原型、无字分层合成和最终卡面；`review-template` 只计算当前 targets，默认 pending，不自动批准。左右视角、关 foil 的景深、depth=0 的对照、移动闪光、固定文字与手机可读性均需实际看图/操作，参见 [references/art-direction.md](references/art-direction.md)。

把真实调用与评审登记进邻接的 `art-evidence.json`，回到同一 public `run --layers`。控制器会生成自己的 front/preview；最终 review 的 targets 必须与实际控制器输出一致。不一致就对当前输出重新看图，不能只改哈希继承旧意见。

每层首次后最多再生成两次，保留失败记录与合格层；必要时一次明确构图修订。达到上限保留原型/候选预览并如实说明未完成，不交几何占位、不复用被否决旧图凑成功。无浏览器时仍可完成文件，但不能声称完整动态验收。作品审查不等于本人授权公开。
