# 交互闪卡与稳定分层 · portable 1.1

## 成品不变，制作路径分开

成品是主 `index.html` 内嵌的同一张可交互卡，另附独立 `card-preview.html`。PNG/WebP 只作纹理或静态留图，不能把 PNG、GIF、视频、整张海报旋转，或几个重复裁片当作分层闪卡完成。

保留锁定 V10 renderer：按住拖转、正反面、自动轻摇/暂停/归位、独立背景/主体/前景视差、固定排字、随视角变化的 WebGL 镭射。手机可触摸，键盘可操作，减少动态设置关闭自动运动但保留手动操作。不要求人物肢体动画，不为本次修改引入视频生成或骨骼动画。

**不改** `assets/template`、template-lock、六层 manifest/depths、原有 strict 门禁、星系和揭卡。背景、主体、前景效果、排字、轮廓、可选伴生层继续使用同一接口。原画无字，排字仍由程序完成；伴生层在无角色设计时可以为空，不为凑图层再画一个人。

## 最小能力检查与有限重试

文生图、引用同图编辑、透明输出、本地分层处理是不同能力。保留 capabilities.json 现有字段，按实际观察可增加：

```json
{
  "image_edit": {
    "status": "unknown",
    "reference_binding": "unknown",
    "transparent_output": "unknown"
  },
  "layer_processing": {"status": "unknown", "reason": "尚未检查真实分割和背景处理能力"}
}
```

上述状态为 available / unavailable / unknown / temporarily_blocked；未知不等于不可用。宿主调用 `portable.py layers-plan --capabilities WORK/capabilities.json --workspace WORK`。不要因为看见生图按钮，就假定三个编辑能力都成立。严格遵守实际接口，不填弃用引用字段，不编造文件 ID。

先冻结一张已实际看过且通过的原型，保留文件与 SHA-256。编辑任务只传可见形象、一个画风、当前图层要求和真实参考，不传星系、履历、整份 Skill、审查表。不修改已通过的其他层。

每个真实编辑调用后，用 `portable.py record-image-attempt --workspace WORK --role subject --outcome success|failure|reference_mismatch --reason "实际观察" --prototype WORK/prototype.png [--output WORK/真实返回.png]` 记录；success 必须有实际文件。每角色最多三次；**首次出现换人/换场景就停止此引用链路**，不继续用相同方式反复碰运气。记录不是工具调用本身或供应商认证。

## 两条实际可执行的路径

**native_layers**：原生编辑输出同画布完整背景、透明主体、透明前景。沿用 `prepare_card_layers.py`。旧 generation.json 不写 layer_method 时仍按此路径解释。

**assisted_layers**：原型必须仍是真实原生生图。允许用实际分割工具获得主体/前景蒙版，并修复或生成完整无主体背景；已合格的原生层可直接复用。`prepare_assisted_layers.py` 只把原型像素按灰度 alpha 蒙版提取，并复用原装配器；它不会自动理解人物、伪造蒙版、下载模型或生成缺失背景。不要求用户提供外部 API。

```sh
python ROOT/scripts/prepare_assisted_layers.py \
  --data WORK/person.json --prototype WORK/prototype.png \
  --background WORK/clean-background.png \
  --subject-mask WORK/subject-mask.png \
  --effects WORK/accepted-effects.png \
  --out WORK/card-task/layers-r1
```

`--subject` 与 `--subject-mask` 二选一；`--effects` 与 `--effects-mask` 二选一，至少一层使用真实蒙版。输入完整同画布，不裁切、不缩放、不重摆。透明棋盘格、整图贴层、缺失背景、矩形切海报、重新绘制的错误人物都不能通过视觉验收。补背景尤其检查拖转时露出重复人影、涂抹和空洞；有问题只返工相关层。

脚本保存私人 `layer-process.json`，绑定原型、蒙版、输入与输出。宿主在实际看过后补充 WORK/generation.json：`layer_method=assisted_layers`、`assembly_record_file=card-task/layers-r1/layer-process.json`、实际 `layers_sha256` 与观察。其他原型字段沿用原契约。不能将辅助提取标成原生透明生成；该路径仅 portable 允许，strict 不因此放宽。

缺少真实蒙版/修复工具时如实指出；不要把分层工具链受限写成“没有生图”，也不改成静态或无卡成品。此路径提高兼容性，不保证所有宿主都具有这些能力。

## 动态与同卡校验

宿主可运行时，在 A 预览生成后执行：

```sh
python ROOT/scripts/verify_portable_card_browser.py \
  --html WORK/card-task/card/preview.html --out WORK/card-motion \
  --report WORK/card-runtime.json
```

默认真实 file:// 打开；浏览器策略禁止时 `--load-mode injected` 仅作有限诊断。`--force-css` 专用于无 WebGL 回退测试，不冒充 GPU 成功。软件 GPU 可显式使用 `--gpu-mode swiftshader`，报告不得写成物理显卡测试。

检查的不是“存在 canvas”：关闭镭射验证内部视差，景深归零检查移动消失，关闭景深单独验证镭射随角度变化，再实测拖转/触摸/翻面/归位/自动轻摇/减少动态和固定文字。当前 CSS 回退保留分层运动，但**不等同 WebGL 镭射**，只能 limited，需披露。

当前卡片任一已执行功能断言失败均阻止交付；变更预览后旧报告失效。缺少浏览器可保留已构建交互 HTML，但必须标明动态未实测，不称动态验收通过。静态图和源码审查不能代替运行报告。B 不重新生成卡：继续对六层字节、persona、深度及 renderer 做一致性校验，并在主 HTML 检查星系与卡片往返。旧 `verify_card_browser.py` 与严格 GPU/独立审查逻辑不变。
