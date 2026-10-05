# 美术记录格式（art-evidence-1）

用于默认 Lite/card-1 public `run` 的本地可追溯检查，不是签名、外部模型认证或自动审美。所有记录均由真实调用或实际观察而来；此文不是要求模型编造一次成功调用。

## 文件引用

统一 `{ "file": "相对文件名", "sha256": "实际文件SHA256" }`。文件在 `layers.json` 所在目录及子目录内；不得使用 URL、绝对路径、父目录跳转或越界符号链接。JSON 记录最多 2 MiB；每个图像最多 24 MiB、1600 万像素。人物 digest 从当前 run-state / card-spec 读取，不自行编造。

## 独立设计 art-direction.json

`version="art-direction-1"`、`persona_digest`，及：

- `preferences={keep:[], avoid:[], basis:"偏好依据", rejected_asset_sha256:[]}`。keep/avoid 来自当前用户，不把例子复制为所有人的风格。
- `scene={style, subject, action, setting, materials, palette, lighting, composition}`，每项为具体画面说明，不用“高级、精美”替代设计。
- `decision={considered:[{name,rationale},...], selected, rationale}`，比较 2–3 个方向，选其中一个；比较记录不发给图像模型。
- `reference_basis="text_only"` 配 `references=[]`；确实看过视觉参考才用 `visible_images` 并登记本地图片引用。
- `typography={text_color, accent_color, scrim_color, scrim_opacity, frame, footer_top}`。颜色为 `#RRGGBB`，遮罩 0–220，边框 `none/single/double`，footer_top 为 0.68–0.84。由设计决定，不强制金色。

结构化设计传给 `--art-prompt-file`。序列化内容最多 6000 字符；它不写回只读人物 JSON。程序编译八项 scene 和 keep/avoid 形成实际视觉 brief。

## 实际图像调用记录

每个使用的独立原生输出登记一次 `image-call-1` 记录：

```text
version: image-call-1
kind: image_tool
tool: 实际工具名
call_id: 实际调用标识
run_id: 本次记录的唯一运行标识
capabilities:
  image_generation: 实际是否具备
  native_transparency: 实际是否具备
  reference_images: 实际是否具备
request:
  canvas: [实际请求与返回保持一致的宽, 高]
  transparent: 实际请求的透明开关
  prompt: 本次发给工具的完整提示词文件引用
  design_sha256: 本次设计文件hash
  reference_sha256: [实际传入参考图hash]
response:
  artifact_id: 工具实际返回的工件标识
  sha256: 该原始输出文件的hash
raw_response: 实际工具返回记录的文件引用
```

透明主体/前景必须有真实 transparent 请求；背景必须不透明；独立层的 reference_sha256 包含所选原型。工具不支持某项就不要编造支持，不要发不存在的参数。适配器应把真实工具调用规范化为此记录；当前代码不代替宿主接通图像工具。

完整 prompt 必须包含程序 `compile_visual_brief()` 编译的当前视觉文本与当前层职责；不要把所有工作流说明放进 prompt。实际输出与记录的工件/hash 必须一致，不能把文件另存或程序绘图冒充模型输出。返回文字须确实含此工件标识；缺真实记录应停在来源未验证，而不是编一份 raw_response。

## art-evidence.json

```text
version: art-evidence-1
persona_digest: 当前人物绑定
run_id: 本次运行标识
design: art-direction.json 的文件引用
images:
  prototype: 图片引用 + mode + call
  background: 图片引用 + mode + call
  subject: 图片引用 + mode + call
  effects: 图片引用 + mode + call
  spirit: 仅非空时需要同样记录
composite: 真实无字合成图引用
reviews:
  prototype: 原型评审文件引用
  composite: 无字合成评审文件引用
  final: 最终卡面评审文件引用
```

`mode="generated"` 必须对应本次 run_id 与当前设计。`mode="reused"` 必须额外提供 `reuse={declared:true, persona_digest:当前绑定, reason:具体复用原因}`，保留原调用记录，并重新完成当前评审；不能把复用说成本次新生图。被当前偏好账本否决的资源不能被选择。

原型阶段允许未来图层/合成/评审尚未存在。manifest 可先采用当前 card-spec 的模板，其路径约定不构成生成事实。

## 三阶段评审

用实际文件先计算 targets：

```bash
PY scripts/art_quality.py review-template --layers CARD/layers.json --persona-digest DIGEST --stage prototype --out CARD/prototype-review.pending.json
PY scripts/art_quality.py review-template --layers CARD/layers.json --persona-digest DIGEST --stage composite --out CARD/composite-review.pending.json
PY scripts/art_quality.py review-template --layers CARD/layers.json --persona-digest DIGEST --stage final --front RUN/card/front.png --preview RUN/card/preview.html --out CARD/final-review.pending.json
```

命令不会覆盖已有文件，不会生成接受意见。真实看图之后保留 `stage`、`targets`，填写 `observer`、带时区的 `observed_at`、`decision=accept/revise/pending`，逐项 `checks={criterion:{passed,observation}}`，以及 `capture` 实际检查记录引用。观察写清楚具体发现；不是每项抄一句“精致、符合、通过”。

final 还需 `views={left:图片引用,right:图片引用,mobile:图片引用}`；左右必须不是相同像素。原型绑定当前设计与原型；合成绑定实际图层和叠加结果；最终绑定当前卡面/互动预览。修改 targets 不是自动继承先前观察的许可。

`check --stage ...` 会依次检查截至该阶段的记录，返回 0 为记录一致、2 为待补、1 为拒绝。公开完成仍需 public run 的模板、资产和浏览器关口；独立检查命令不返回完整作品认证。

## 完成状态

`run-report.json` 的 `outputs` 是通过当前关口的可交付文件；`candidate_outputs` 是待验卡片。`complete` 才是所请求作品的完成状态，不能用 `ok`、文件数、art_status 或本地旧报告替代。`delivery-report.json` 绑定实际交付文件、输入和状态，不内嵌原始聊天或工具凭证。
