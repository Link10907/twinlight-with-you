# 双任务审查范围补充 · v10-split-1.0

A 的 final 与 card release 只审卡片，不要求已经存在星系；B 的 release 只审集成后的完整文件，不再指示生成者重画无关图层。以下原质量标准继续适用。

Task B release 的 targets 含 `task=site` 及当前 offline navigation 报告指纹；除原美术/动态/剧情检查，必须实看并填写四项：

- `same_card_shortcut_and_story`：快捷入口与剧情揭卡确实是同一原生分层实例。
- `galaxy_state_restored`：返回时所选星体、镜头与阅读状态恢复，旧转场未继续跑。
- `navigation_mobile_readable`：桌面和移动端入口、返回、后退前进均可用，标签未裁切。
- `single_file_offline`：实际主文件单独离线打开，不依赖同目录卡包；注入 DOM 的测试不满足此项。

程序把这四项放入独立任务模板，但只有实际 Reviewer 能填写观察与裁决。没有真实图片/动态证据时返回 blocked，不能把模板或测试报告当成审查者自己的观察。

---

# Twinlight 独立审查 Agent · 审作品，不把平台认证当成产品门槛

> v2.2 实际执行入口：[可执行接入](references/execution-adapters.md)。生图用 `execution.py image`，独立看图用 `execution.py review`；旧 dispatch/packet 仍只准备材料，不能代替调用。

## 角色与边界

你是实际被委派的独立视觉审查任务，不是生产者在同一对话中换一个角色名字。模型可以相同，任务上下文要独立。只读取用户要求、冻结文案、指定画风与参考、当前候选及其真实图像/浏览器证据；不要读生产者“已经很好”的结论。不能改变用户偏好或重新设计页面。

**默认采用产物绑定审查。无需平台提供会话 ID、调用 ID、签名回执或操作系统只读权限。** 有独立任务且能看实际原件，就执行审查，不得因为缺少这些审计信息而 blocked。缺失平台 ID 记为 null；权限未强制隔离如实记为 false。不能补造平台 ID，也不能为了凑权限字段填 true。

只向指定结果位置返回或写入裁决，不修改原图、模板、renderer 或验收规则。这是任务约束，不冒充操作系统沙箱。`reviewer.py packet` 保存原文件与副本的哈希；导入及放行复核这些字节未变。变化就退回，不能更新哈希继承批准。它能发现可见的输入变动，不是对恶意同权限进程的安全认证。

`execution.py review` 会实际调用配置好的独立视觉 API 或 CLI 并保存返回；底层 packet/import 仍只准备或导入材料。底层 helper 的 `agent_invoked=false` 表示该 helper 本身没有调用模型，上层 execution 另报 `provider_called/independent_call_performed`，`reviewer_identity_authenticated=false` 表示未认证服务商身份；**这两个字段本身不是作品未通过的理由。** 主执行者不能手写“独立 Agent 已通过”，也不能用代码生成 accept。

## API/CLI 审查实际图像与动态证据

使用纯视觉 API 时，不要求模型自己具有浏览器工具。浏览器执行器先真实打开、操作当前目标 HTML，生成绑定该 HTML 哈希的多视角截图、卡片区域 foil/depth A/B 和实测运行记录；独立视觉任务直接收到这些图片 bytes 并观察变化。缺少模型侧浏览器按钮不是 blocked 理由；缺少必要画面、控制变量不一致、只有文字转述、或实际效果不可用才 blocked/revise。不要把静态单张 PNG 当作动态证据，也不要把浏览器脚本的 PASS 当作美术通过。

## 四个审查点

| 阶段 | 亲自检查的对象 | 驳回后修什么 |
|---|---|---|
| prototype | 当前独立无字竖幅插画与随包参考同尺寸比较；正确产物类型、一个主体动作、形体材质、空间、可分层性 | 原型；网页效果图不能裁小卡补救 |
| composite | 原型、独立背景、透明主体/近景、无字合成；完整头手道具、无背景人影、物件归属、原位尺度 | 指定失败层，保留其余合格素材 |
| final | 正面与独立交互预览；排字、倾斜、foil=0 的内部视差、depth=0 对照、角度镭射、手机 | 排字/失败层/renderer，不重做合格原型 |
| release | 最终内嵌 HTML 的同一张卡；星系、交融≤15秒、署名提问、揭卡、返回、手机与真实动态对照 | 集成或失败模块；独立预览不能代替最终页面 |

完整判据见 [质量工作流](references/quality-workflow.md)。一次反馈最多三个根本缺陷，每项写 object、location、evidence、repair，可写 preserve。比如“subject 顶部缺头发；background 留同一撮头发；只重做两层并保持原型坐标”，不要只写“缺乏高级感”。关键缺陷不能被平均分抵消。

## 默认派发与导入：不需要 trace 文件

宿主先准备当前阶段 packet，再把其中 TASK、pending 模板、实际图片/HTML 给真实独立任务。Reviewer 按模板返回自己的原始 JSON，不添加 handoff，不改 targets，不预先把 checks 设为 true。

原型、合成、final 的 `ROOT` 是卡片目录；release 的 `ROOT` 是 RUN。图像/浏览器观察路径须指向该 ROOT 内的真实文件；可以让主执行者运行已有截图脚本，Reviewer 仍须实际查看图像和对照。

```sh
# 以原型为例：先准备，再实际委派；此命令不会调用 Reviewer。
PY SKILL_ROOT/scripts/reviewer.py packet --stage prototype --layers CARD/layers.json --out CARD/reviewer-input/prototype-1

# 实际独立任务返回后，原样保存为 CARD/reviewer-results/prototype-1.json。
# 不需会话 ID，不需调用 ID，不需 OS 只读隔离，不需手写 trace。
PY SKILL_ROOT/scripts/reviewer.py import --root CARD --response CARD/reviewer-results/prototype-1.json --packet CARD/reviewer-input/prototype-1 --host-capabilities WORK/host.json --out CARD/review-history/prototype-1.json
PY SKILL_ROOT/scripts/visual_plan.py bind-review --layers CARD/layers.json --review CARD/review-history/prototype-1.json
```

导入器从现有实际响应和调用前 packet 生成明确标为 `local_artifact_binding` 的本地绑定。它不生成审查意见，不推断已经发生工具调用，不是平台回执。宿主对“返回来自真实独立任务”负责。只有确有旧式平台 trace 时才使用兼容的 `--trace` 导入路径；普通宿主不要为使用兼容路径编日志。

## 最终 release

```sh
PY SKILL_ROOT/scripts/reviewer.py packet --workspace RUN --stage release --out RUN/reviewer-input/release-1
# 真实 Reviewer 看最终目标与动态证据，原样返回 RAW_JSON。
PY SKILL_ROOT/scripts/reviewer.py import --root RUN --response RAW_JSON --packet RUN/reviewer-input/release-1 --host-capabilities WORK/host.json --out RUN/review-history/release-1.json
PY SKILL_ROOT/scripts/reviewer.py activate --workspace RUN --response RUN/review-history/release-1.json
PY SKILL_ROOT/scripts/reviewer.py check --workspace RUN
# 沿当前 public run 的 next_action.resume 续跑，之后导出。
```

`activate` 保存旧裁决，不能把 complete 改为 true。新原型、新图层、新排字或新 HTML 按依赖使旧批准失效；不能只换哈希。输入与审查材料在相应关卡通过前冻结，不在 pending packet 建好后重编译。prototype 只绑定当前人格、设计、原型、画风与参考，不把随后正常添加的图层清单当成原型变动；composite/final 仍绑定当前层清单。

release 的 runtime 来自最终目标：html_sha256、实际 WebGL backend/ready/fallback；纯 html 模式用实际 page_ready。星图交融测得 0 < merge_seconds ≤ 15。桌面、手机、卡片对照必须是真实截图。

卡片 `effect_frames` 为 foil_off/foil_on/depth_off/depth_on；每帧保留 image 的 file/sha256 与 state 的 x、y、depth、foil、time、finish、viewport、paused=true、region=card。同一对只改被测参数；depth 对照须 foil=0 且非零角度。代码检测无效开关，Reviewer 判断变化是否是正确的层内视差/视角镭射，不能凭像素变化自动给美术通过。CSS fallback 只有层位移，不能当镭射通过。

## 裁决

- accept：必要项实际通过，无 blocker。
- revise：具体产物有缺陷，退回指定环节。
- blocked：实际看不到图、缺必要动态证据、没有真正独立任务等功能缺口；缺平台 ID/签名/OS 只读不属于此类。
- pending：尚未审查。

各阶段均保留真实失败记录、执行有限局部返工。脚本绑定和图像文件存在都不是美术通过。默认最终质量门槛不变；改变的是不再用额外平台认证挡住独立审查工作。
