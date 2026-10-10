# 任务 B：V10 星系制作、已验收闪卡集成与交付

先读 [AGENT.md](AGENT.md) 与 [交接契约](references/card-handoff.md)。本任务不生图、不编辑图片、不改变 A 的卡面文字、深度、材质或版式，也不调用 `prepare_card_layers.py` 重新排版。

## 输入与能力

需要当前 `WORK/person.json`、A 完整私人工作区中的 `card-handoff.json`、固定 V10 资源，以及真实浏览器/独立视觉审查能力。只有可分享 `card-pack.json` 不足以证明 A 已验收；不能凭 `art_status=approved` 放行。

```sh
PY ROOT/scripts/preflight.py check --capabilities WORK/host-B.json --mode integrate
PY ROOT/scripts/twinlight.py check-handoff A/card-handoff.json --input WORK/person.json
PY ROOT/scripts/twinlight.py task-site WORK/person.json --workspace B --card-handoff A/card-handoff.json --host-capabilities WORK/host-B.json
```

`execution.py doctor/host --mode integrate` 允许仅配置 reviewer。没有生图服务不是 B 的失败理由；没有合格 A、真实浏览器或独立集成审查才是相应阻断。B 启动及续跑永远不能把 `--card-handoff` 换回任意 `--layers`。

## 组装与两种观看路径

原 V10 核心和锁不变；额外的 `assets/navigation` 独立版本化。主文件内嵌同版原生图层、共享 holo renderer、脚本/样式/音乐，不用 iframe、不 runtime fetch 旁边文件。

- 完整观看：星系 → 连续 14 秒终章 → 按实际总结模型提问 → 原 V10 揭卡 → 返回星系。
- 快捷观看：“我的闪卡”（手机端短标签“闪卡”） → 同一个卡片 DOM/renderer；返回恢复此前星系。原星系导航复用，手机端不重复堆入口。

`#galaxy` / `#card` / `#finale` 由一处控制器负责。深链接等待实际 scene/纹理初始化；旧 1300ms 入口在装配时被前置适配器去重，不改旧 v10.js。后退/前进、Esc、中途退出、连续快速切换都要测试。只有同次页面会话的浏览状态恢复，不承诺跨刷新持久化。音频沿用原实例与用户动作，不绕过浏览器播放策略。

## 验证与独立放行

B 的 public task 自动执行原 `verify_browser.py`（含完整剧情与 WebGL）、内嵌字节/渲染器比对，并追加 `verify_navigation.py`。后者默认把唯一 index.html 复制到空目录、断网后 file:// 打开，检查导航和返回；它不代替 WebGL 或完整剧情。

```sh
PY ROOT/scripts/verify_navigation.py --html B/site-with-card/index.html --out B/manual-navigation
```

`--load-mode injected` 仅供工程诊断，在文件策略受限环境中检查 DOM；其 `delivery_eligible=false`，永远不能作为 B 放行证据。测试模式未跑、WebGL 回退、完整交融超时、文件访问被限制都如实保留，不降级伪装通过。

当前技术检查通过后，依据真实候选采集动态证据，由独立 Reviewer 做 release：

```sh
PY ROOT/scripts/reviewer.py packet --workspace B --stage release --evidence ACTUAL_EVIDENCE --out B/reviewer-input/release-1
```

用真实独立执行器 `execution.py review --root B ... --activate` 或宿主独立任务配合 import/activate 保存原始裁决。新增 navigation 检查也需要真实观察。然后沿同一 `task-site` 续跑；`activate` 本身不会把 complete 改为 true。A 通过不代表 B 自动通过。

## 统一交付

只在当前 B complete 后导出：

```sh
PY ROOT/scripts/deliver_artifacts.py --workspace B --out WORK/delivery
```

包内主入口为 `index.html`，附带 `card-preview.html`、`card-front.png`、`card-pack.json`、`README.txt` 与不含私人路径的 `delivery.json`。独立预览通过同包链接返回主文件，但主文件不依赖预览/卡包；移走附加文件不影响主页面资源。

导出前再次检查 A 的实际原件/审查、B 当前导航报告与独立 release。B 的生产错误不清除 A；艺术错误回 A 的具体环节。默认不发布，不含字体、原始聊天、凭证、审查日志或私人目录。

明确用户要求聊天内交互时首次带 `--require-in-chat-preview`；这是另一项实际入口验证。本地附件、下载链接或静态截图不证明聊天内可运行。
