> 双任务版：A 使用 `doctor/host --mode card`；B 使用 `doctor/host --mode integrate`，配置允许不含 image。B 只允许 review，不允许 image。以下原接口与手动接入方式继续兼容，出现旧 both 示例时以当前 AGENT/HTML 的独立工作区为准。

# 可执行接入 · 不是再写一份能力声明

本版将 v2.1 的产物绑定审查、运行诊断热修和实际执行器合并。`visual_plan.py dispatch` 与 `reviewer.py packet` 仍只准备材料；新增 **`execution.py image` 真正调用图像服务并登记原字节**，**`execution.py review` 真正发起独立视觉调用、原样导入裁决并可绑定**。不需要主会话拥有 `spawn_agent`。

## 1. 选已有授权路线，一次配置

复制一个示例到私人工作区 `WORK/execution.json`，不要把凭证写进 JSON 或交给聊天。环境变量由用户现有授权环境提供；不读取 `.env`、Keychain、浏览器数据库或第三方凭证文件。诊断不调用模型，安装不调用模型。实际调用需明确 `--allow-provider-calls`，可能消耗订阅额度或 API 费用；它不授予新账户、付费或私人信息外传权限。

| 配置 | 图像 | 独立 Reviewer |
|---|---|---|
| [execution-codex.example.json](execution-codex.example.json) | 明确提示和图片的 Images API | 已安装、已登录的 Codex CLI 全新视觉任务 |
| [execution-openai.example.json](execution-openai.example.json) | Images API | 全新 Responses 视觉请求，`store:false`，不传历史/previous_response_id/tools |
| [execution-anthropic.example.json](execution-anthropic.example.json) | Images API | 全新 Messages 视觉请求，实际 base64 图片，无历史与工具 |

图像示例模型为 `gpt-image-2.5-sunburst`，原生画布 1152×1536；可用 `TWINLIGHT_IMAGE_MODEL` 换成账户支持的原生 3:4、编辑和 alpha 模型，不暗示你的账户必有权限。API Reviewer 通过 `TWINLIGHT_REVIEW_MODEL` 指定已可用视觉模型；Codex 省略时使用其正常已配置模型。不要选择只能输出 2:3 再裁成 3:4 的模型。模型缺失/鉴权/限流/不支持参数会明确报错，不自动买服务或换模型。

Codex 路线在系统临时目录启动新进程，**不共享项目工作目录或生产会话，不使用 resume**。先检测本机 `exec --help` 的真实选项，再附实际图片和独立提示；请求 read-only，支持时加 ephemeral/ignore-user-config。只是平台未暴露会话 ID 不会失败。平台本身的全局策略和账户权限仍由 CLI 管理；不是密码学身份认证。API 路线没有文件写工具，同样核对审查前后原件与输入副本。

已有自建/其他提供商可配置 `kind: command` 和**确实存在**的 `argv` 数组。实际启动该命令，新任务 JSON 经 stdin，stdout 返回 JSON。不是把任意 shell 字符串当命令，也不假称未安装的服务存在。协议在本文末尾。普通宿主已经有真实窄上下文工具时仍可沿 CARD 的 dispatch/record 与 packet/import 执行，不必额外购买 API。

## 2. 本地诊断与实际连通性

下文 `ROOT` 是完整 Skill；`WORK` 是原私人任务目录。Python 3.10+，依赖沿用 requirements.txt。变量由执行 Agent 根据已有路径设置，不让用户重复填写。

```sh
PY ROOT/scripts/execution.py doctor --config WORK/execution.json --out WORK/doctor.json
PY ROOT/scripts/browser_probe.py --channel chrome --headed --out WORK/browser-probe.json
PY ROOT/scripts/execution.py probe-reviewer --config WORK/execution.json --image ROOT/assets/art-references/twinlight-collector/human-prototype.png --out WORK/reviewer-probe-1 --allow-provider-calls
PY ROOT/scripts/execution.py host --config WORK/execution.json --probe WORK/reviewer-probe-1/probe.json --browser-probe WORK/browser-probe.json --out WORK/host-execution.json
```

`--channel chrome --headed` 是本机已安装 Chrome 的示例；无桌面时不要强开 headed。可换 `--browser` 为真实浏览器路径，或省略使用已安装 Playwright Chromium。不会自动下载。默认 `gpu-mode auto`；`--gpu-mode swiftshader` 只做显式软件诊断。`browser_probe` 实际建 WebGL、编译 shader、绘制读回一个像素；**这不代表卡片 foil 或交融已验证**。

Reviewer 探针发起一次真实看图，只能证明输入传达和返回可读取，**不批准新卡**。它不花生图费用，但可能有视觉推理费用。`host` 依据探针写新能力来源，不改旧记录；source 明示图像服务权限和原生输出仍待逐次调用验证。能力表中的可执行协议不是艺术通过证明。已知 WebGL 不可用不填 true；诊断、页面候选及已完成部分可保留，完整效果不能放行。

## 3. 一幅原型先走完实际调用和否决

保留 `WORK/person.json`、`RUN/run-state.json` 和原资产。用新 host 路径续跑，读真实 next_action，不手改 complete。具体艺术设计沿 CARD。

```sh
PY ROOT/scripts/visual_plan.py compile CARD/art-direction.json --out CARD --phase prototype --capabilities WORK/host-execution.json
PY ROOT/scripts/execution.py image --config WORK/execution.json --plan CARD/generation-plan.json --role prototype --workspace RUN --host-capabilities WORK/host-execution.json --out CARD/calls/prototype-1 --allow-provider-calls
PY ROOT/scripts/reviewer.py packet --stage prototype --layers CARD/layers.json --out CARD/reviewer-input/prototype-1
PY ROOT/scripts/execution.py review --config WORK/execution.json --packet CARD/reviewer-input/prototype-1 --root CARD --host-capabilities WORK/host-execution.json --out CARD/reviewer-results/prototype-1 --layers CARD/layers.json --allow-provider-calls
```

`execution.py image` 内部已做 dispatch/record，**不要先手动 dispatch 同一次调用，避免重复预算预留**。只发当前 prompt、实际参考和当前画布，不传完整网页请求。原型比较 style_only，分层仅当前原型。原图 bytes 原样留存；背景须完整不透明，subject/effects 须原生 alpha、非空、画布配准；不程序裁图补救。每角色三次预算沿原 RUN 保留；超时不自动重试，先检查服务是否已经计费/返回。

review 返回 `accept/revise/blocked`；原样保存、不自动润色 JSON。accept 才续跑；revise 的具体位置与修复动作交回生产者，只修失败层；blocked 处理真实缺口。仅将配置里的 kind 改掉或用同会话写出“审核通过”不构成调用。每次输出目录全新，原始失败保留。

原型通过后编译 `--phase layers`，依次对 `background/subject/effects` 使用同一 image 命令；排字、合成、composite packet/review 按 CARD。程序不重新作画。final/release 的步骤如下。

## 4. 实际动态证据进入同一次视觉请求

```sh
PY ROOT/scripts/verify_browser.py --html RUN/site-with-card/index.html --out RUN/browser/site --channel chrome --headed
PY ROOT/scripts/verify_card_browser.py --html RUN/card/preview.html --out RUN/browser/card --channel chrome --headed
PY ROOT/scripts/capture_review.py --html RUN/card/preview.html --root CARD --out CARD/evidence/final-1 --mode card --channel chrome --headed
PY ROOT/scripts/reviewer.py packet --stage final --layers CARD/layers.json --front CARD/front.png --preview CARD/preview.html --evidence CARD/evidence/final-1/review-evidence.json --out CARD/reviewer-input/final-1
PY ROOT/scripts/execution.py review --config WORK/execution.json --packet CARD/reviewer-input/final-1 --root CARD --host-capabilities WORK/host-execution.json --out CARD/reviewer-results/final-1 --layers CARD/layers.json --front CARD/front.png --preview CARD/preview.html --allow-provider-calls
```

首次 final 时集成候选可能还没有，先验独立预览，public run 集成后再跑 verify_browser；不要先等一个尚未生成的文件。证据工具对真实页面采集正面、左右、手机及 foil/depth 卡片区域 A/B，冻结时间/角度/视口，仅改被测参数。不修改原 HTML，不把 PNG 当作用户可互动的成品；视觉 Reviewer 必须读取实际多视角画面并结合运行数据，而非凭像素有变化批准。没有原生 WebGL/foil 对照时不得 accept。

```sh
PY ROOT/scripts/capture_review.py --html RUN/site-with-card/index.html --root RUN --out RUN/evidence/release-1 --mode both --site-report RUN/browser/site/report.json --channel chrome --headed
PY ROOT/scripts/reviewer.py packet --workspace RUN --stage release --evidence RUN/evidence/release-1/review-evidence.json --out RUN/reviewer-input/release-1
PY ROOT/scripts/execution.py review --config WORK/execution.json --packet RUN/reviewer-input/release-1 --root RUN --host-capabilities WORK/host-execution.json --out RUN/reviewer-results/release-1 --activate --allow-provider-calls
```

release 通过仍要沿原 public run 的 next_action.resume 重新核验，最后 `deliver_artifacts.py` 导出。纯 html 对应 `--mode html`，不要求卡片 foil。动态阶段 runtime/frames 的哈希、角度、时间、尺寸是工具事实，Reviewer 不能改成可用；接受一张静态图不等于整页交付。

## 5. 超时修复的边界

V10 WebGL 失败时会进入 reduced 并在 11.7 秒提问页等待手动揭卡。新测试不再等待该模式不可能发生的自动 merge；检查回退揭卡及返回，同时保留 `continuous_verified=false/full_effects_verified=false/release_authorized=false`。默认不强制 SwiftShader，不强改 reduced，不用延长超时掩盖状态错误。真正的 GPU/浏览器不可用需要换已具备能力的运行环境，补丁不是显卡驱动。

## 6. 已有命令提供商协议

配置 `argv` 例如 `["/absolute/path/to/your-existing-bridge"]`（这是协议示例，不是已安装服务）。每次全新进程，stdin 是 `twinlight-provider-task-1` 对象，含 task=image/review、prompt、images（实际 data_url、哈希、名称）、output_directory；image 另含 canvas/transparent。图像 stdout 返回 `{ "image_file": "在 output_directory 内的原生 PNG 绝对路径" }`；审查 stdout 返回 packet 模板完整 JSON。必须保持图片原生坐标/alpha。图像配置额外声明 declared_capabilities 的 native_image_editing/native_transparency/reference_images，结果仍逐次核对。不要传自动执行任意不可信命令的工具。

## 接口依据与验证边界（核查日：2026-10-08）

- OpenAI Images edits： https://developers.openai.com/api/reference/resources/images/methods/edit
- OpenAI 视觉输入： https://developers.openai.com/api/docs/guides/images-vision
- Codex CLI： https://developers.openai.com/codex/cli/reference
- Anthropic 视觉输入： https://platform.claude.com/docs/en/build-with-claude/vision
- Playwright 浏览器： https://playwright.dev/python/docs/browsers

代码按上述接口实现，具体模型权限、CLI 版本和网络由目标环境探针确认。随包测试有 SYNTHETIC 标记，只验证路由/原字节/否决/失败保留及本地 HTTP/独立进程调用，不声称真实模型审美已通过。不包含 API 密钥、字体文件或本次私人样稿。
