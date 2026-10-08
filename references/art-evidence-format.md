# 实际美术记录：art-evidence-1

`art-evidence-1` 是记录容器版本，当前设计仍使用 `art-direction-2`。这些本地记录用来避免串图、漏参考和继承过期观察；不认证提供商、不自动判断美感、不代本人许可。生产命令集中在 [CARD.md](../CARD.md)。

## 文件和设计引用

文件引用统一为 `{ "file": "目录内相对路径", "sha256": "实际字节摘要" }`。记录使用 layers 所在目录及子目录内的真实文件；不写 URL、越界绝对路径或父目录跳转。人物 digest 从当前 run-state / card-spec 读取。

设计保存 `art-direction-2`，字段与参考用途见 [视觉契约](visual-contract.md)。不要在此另写旧 `art-direction-1` 场景格式；历史格式只用于读旧记录。

## 实际图像调用

由 `visual_plan.py record` 从真实输出登记 `image-call-1`，保存工具名、实际 call/artifact 标识、原图 hash、实际响应引用、请求 prompt、设计 hash 和 style binding。request 包含当前请求画布、透明开关、`reference_sha256` 和 `reference_images`；response 记录实际返回画布与原图字节。

`reference_images` 每项说明文件、sha256、purpose。原型任务的品牌图标 `style_only`，图层编辑任务仅以当前已通过原型作 `composition`；所有应传图都必须在实际工具调用中附带。图层沿用已核验原型的品牌来源链，不伪报再次传入品牌图。缺实际传图不能用“提示词说了参考某图”补证。原生透明请求使用工具实际开关，不构造不存在的参数。工具只接受文字尺寸时如实记录 prompt_only 能力，返回后才确认尺寸。

受控 `repair` 只更新下一次任务的具体反馈与逐项归属，保留同一设计/原型、原始输出及三次尝试预算。若旧输出仅因尺寸相差 1 像素而拒绝，可按现有 `native-rounding-1` 规则明确重新评定；保存原拒绝与复核原因，不删除尝试、不伪称重新生图。

实际返回文本与工件标识必须一致。宿主看不见提供商内部的 seed、payload 或模型版本就留未知；不为了通过检查伪造 raw_response。记录失败输出与尝试次数，不只保存最好一张。

## art-evidence.json

```text
version: art-evidence-1
persona_digest: 当前人物绑定
run_id: 本次记录标识
design: art-direction.json 的引用
images:
  prototype/background/subject/effects: 当前原图引用、mode 与实际 call
  spirit: 仅非空时需要真实调用
composite: 当前无字合成图引用
reviews:
  prototype/composite/final: 相应实际观察记录引用
```

`mode=generated` 对应本次设计和真实调用。确实复用同主人已授权素材时用 `mode=reused`、保留原调用并记录 declared/persona_digest/reason，再过本次观察；不能将复用声称为新生图。style_only 品牌参考不是当前层复用许可，被当前偏好否决的图不得被选择。

## 三阶段观察

`art_quality.py review-template` 只输出 pending 模板，不自动接受。实际打开当前文件后保留其 stage/targets，填写 observer、带时区 observed_at、decision，以及每项 `checks={criterion:{passed,observation}}`。记录真正看到的细节与缺陷，capture 指向实际观察/检查记录。

默认品牌会检查 `visual_hierarchy`、`material_finish`、`spatial_depth` 与 `reference_quality_parity`，含义见 [质量工作流](quality-workflow.md)。逐项说明当前焦点、材料、纵深及相对参考的完成度，不能全部填写“精美通过”。

final 同时绑定当前 front 和 preview，views 包含真实 left/right/mobile 截图；左右不是相同像素。原型变动会影响其后图层，图层变动会影响合成与 final，文字/预览变动会使 final 过期。只改 targets/hash 不是重新观察。

`check --stage ...` 的通过表示记录完整且一致，不是整件作品完成。完整交付仍需 public run 验证模板、内嵌、浏览器和实际成品。`quality_verified` / `generation_provenance_verified` 不得当外部认证自填 true。

## 报告与边界

`outputs` 是通过当前关口的文件，`candidate_outputs` 是待验素材；只以本次 `complete` 判断请求是否完成。不能以文件数、art_status、ok 或旧报告替代。导出收据绑定实际文件，不携带原始聊天或凭证。技术记录、视觉观察、本人确认与公开授权始终分别记录。

## 独立审查升级

三个 stage review 现在均要求 `handoff`、`blockers`，绑定实际独立调用及原始裁决；规范见 [REVIEWER.md](../REVIEWER.md)。旧的 observer 字符串与自写 capture 不再单独构成通过。
最终产物另需 `RUN/release-review.json`；pending、rejected、能力阻断或文件过期均不得完整导出。原型与独立卡审查不能替代最终内嵌页面审查。`reviewer_identity_authenticated=false` 始终保留：本地记录不是宿主权限隔离或提供商认证。

本版 art-direction-2 的每份 image-call request 还须带真实调用前 `dispatch:{file,sha256}`。生成记录和最终美术证据都会检查同一 RUN 的消耗记录、原 prompt、参考和原始响应；仅提供文件/手写 call_id 不再满足结构要求。它依然不是服务商身份认证。
