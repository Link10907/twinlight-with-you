# 一次请求执行入口 · v10-quality-2

同一生产工作区内续跑，不要求用户发送第二条生成指令。`PY` 是宿主实际 Python 3.10+；`ROOT` 为完整包；`WORK` 为本次私人目录；`RUN=WORK/run`，`CARD=RUN/card`。命令由执行宿主完成，不让用户填写工具问卷。

## 0. 先决定这条路线能不能执行

运行 `PY ROOT/scripts/bootstrap.py --root ROOT` 检查资源、依赖、清单与模板锁。优先完整离线包，不混用另一个 main 版本。读 [宿主契约](references/host-contract.md)，创建 **pending** 能力表：

```sh
PY ROOT/scripts/preflight.py template --out WORK/host.json
PY ROOT/scripts/preflight.py check --capabilities WORK/host.json --mode both
```

两命令之间由宿主查真实工具说明、必要运行探针及实际会话信息，再填能力事实；模板不是现成通过记录。特别检查：图像 prompt 是否有效或可用真正隔离子任务、参考图片能否确实传入、原生编辑/透明/竖幅、图像返回后能否继续、真实独立 Reviewer 和 WebGL。共享自动上下文而没有隔离能力时，不调用生图碰运气。

缺项一次说明并保留独立可做模块；不要画完整套才发现没有审查 Agent。不自动开付费服务、上传个人信息或新建账号。当前工具接口优先于包内命令示意；不得往弃用参数中塞文本冒充任务传输。

## 1. 冻结当前资料，先构建页面候选

读 [Lite 内容](references/lite-content.md)，写当前人的 `WORK/person.json`。只用本次授权资料；默认未确认草稿。依据足够就完成，不为凑星编经历，不把他人宠物、职业或参考图角色套给用户。实际模型负责署名；未知具体版本留空。

```sh
PY ROOT/scripts/twinlight.py run WORK/person.json --workspace RUN --mode both --host-capabilities WORK/host.json
```

用户明确要站内可操作时首次加 `--require-in-chat-preview`；需求和能力表来源随续跑保留。保存 `persona_digest`、字体状态、`next_action`。后续沿真实 `next_action.resume` 执行。基础 `site/index.html` 是候选，不是 both 成品。

## 2. 独立图像任务与原型审查

按 [CARD.md](CARD.md) 写具体 `art-direction-2`。画风固定、身份冻结，只确定一个主体、一个可理解动作、至多一个接触道具；材料与环境保持精绘质量。

```sh
PY ROOT/scripts/visual_plan.py compile CARD/art-direction.json --out CARD --phase prototype --capabilities WORK/host.json
PY ROOT/scripts/visual_plan.py dispatch CARD/generation-plan.json --role prototype --workspace RUN --host-capabilities WORK/host.json --out CARD/dispatch/prototype-1.json
```

`dispatch` 冻结当前图像任务并消耗一个调用预留；**不会调用模型**。宿主实际只发送 dispatch 的 `prompt_text`、列出的真实图片和工具支持的图像参数，不发送完整 JSON、历史对话、网页需求或本手册。无法这样发送就停止图像环节。返回后保留原字节与真实响应：

```sh
PY ROOT/scripts/visual_plan.py record CARD/generation-plan.json --role prototype --dispatch CARD/dispatch/prototype-1.json --image RAW_IMAGE --raw-response RAW_RESPONSE --tool ACTUAL_TOOL --call-id ACTUAL_CALL --artifact-id ACTUAL_ARTIFACT
PY ROOT/scripts/reviewer.py packet --stage prototype --layers CARD/layers.json --out CARD/reviewer-input/prototype-1
```

宿主把 packet 的独立任务交给真实 Reviewer；实际读图，比较随包参考，不只看 JSON。原型错误类型、粗糙、偏画风、不可分层就 revise。按 REVIEWER 导入并 bind 裁决；accept 前禁止请求图层。相同模型可以，生产和审查会话必须不同。

## 3. 原生分层、排字与独立预览

原型通过后 `visual_plan.py compile ... --phase layers --capabilities WORK/host.json`。每个 background / subject / effects 单独 dispatch → 实际 image_edit → record；编辑唯一参考为当前原型，不再传不同角色的品牌参考。全部保留同画布、尺度、原位坐标；不以抠图、裁剪、去底、拉伸或复制海报替代。

按 CARD 用程序排字、生成空 spirit 与 lineart、合成，做 composite 审查。通过后：

```sh
PY ROOT/scripts/twinlight.py run WORK/person.json --workspace RUN --mode both --host-capabilities WORK/host.json --layers CARD/layers.json
```

首次写出真实 `RUN/card/front.png` 与 `preview.html` 候选。由独立 Reviewer 做 final；实际拖动、翻面、关闭 foil、depth=0、手机与减动效。程序截图证据不是审美裁决，截图变化也不自动证明正确景深。只修失败层或渲染问题，不重生合格原型。

## 4. 最终集成与独立放行

沿同一 `run` 续跑到 `needs_release_review`。both 只审最终 `site-with-card/index.html`；html 审实际基础星图；card 审独立卡。

```sh
PY ROOT/scripts/reviewer.py packet --workspace RUN --stage release --out RUN/reviewer-input/release-1
```

Reviewer 亲自检查同一 HTML，桌面/手机、星系/交融/提问/揭卡/返回与同张卡的受控 foil/depth 对照。原型/图层看过，不等于集成已通过。宿主原样保存实际 JSON 响应和真实调用 trace，在 RUN 内导入，再选择当前裁决：

```sh
PY ROOT/scripts/reviewer.py import --root RUN --response RUN/reviewer-results/raw-1.json --trace RUN/reviewer-results/trace-1.json --out RUN/review-history/imported-1.json
PY ROOT/scripts/reviewer.py activate --workspace RUN --response RUN/review-history/imported-1.json
PY ROOT/scripts/reviewer.py check --workspace RUN
```

pending/blocked/revise 都不放行；新裁决不覆盖旧原始响应。`activate` 不把 complete 改为 true；继续 public run 才重新核验全部依赖。Reviewer 的真实身份、权限由宿主实现，本地记录始终不是不可伪造认证。

## 5. 一次交付，精确说明完成范围

站内交互要求用真实最终文件接入当前入口，实测后记录 `host-preview-2`。下载按钮和本地浏览器不能证明站内交互。按 `next_action` 刷新报告后导出：

```sh
PY ROOT/scripts/deliver_artifacts.py --workspace RUN --out WORK/delivery
```

只有确实在 `/mnt/data` 提供附件的宿主才加 `--link-style sandbox`。读取真实 `handoff.json` 和 `delivery-reply.md`，同一回复展示卡图、主 HTML、独立预览和完整包。文件存在、动态通过、独立审查和站内入口分别说清；不自动公开或 push。

状态路线与返工边界只维护在 [返工规则](references/recovery-policy.md)。不要手填 `complete`，不要用低层命令绕过缺项，达到上限就交付明确标记的成功模块/候选，而不是坏卡凑成功。
