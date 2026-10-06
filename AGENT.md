# 一次请求执行入口

宿主做三件事：理解当前资料、调用真实图像工具、实际看成品。程序完成模板组装、提示编译、原图记录、排字、验证与导出。不要把整个手册发送给图像模型。

下文 `PY` 指当前可用 Python 3.10+，`ROOT` 指完整 skill 目录，`RUN` / `CARD` 指当前人的私人输出目录。命令以 `both` 为例；用户只要页面或卡片时分别用 `html` 或 `card`。命令由宿主执行。沿同一工作区的 `next_action.resume` 续跑，已成功模块不重做。

## 0. 确定本次实际交付入口

首次在当前宿主执行时读 [平台适配](references/platform-adapters.md)，检查解包执行、图像参考与透明输出、图片返回后继续执行、真实浏览器及聊天内 HTML 入口。先使用已暴露工具的实际说明；用户点名聊天内交互时，再用当前固定模板基础页面试开原生预览，不能用一个简单按钮通过来推定整个 V10 可运行。

用户明确要求聊天内直接渲染/操作时，首次 `run` 加 `--require-in-chat-preview`，该要求随工作区续跑保留。未能取得可用入口时及时说明具体限制，继续完成独立可做的工作，最终保留“文件完成、聊天内要求未满足”的状态。不要让用户用第二条“继续”来启动已授权步骤，也不承诺仅凭换模型就能获得渲染能力。

## 1. 固定资源和当前内容

运行 `PY ROOT/scripts/bootstrap.py --root ROOT`。只有 URL 时先取得 bootstrap，再用 `--out` 获取同一 commit 的完整资源。下载失败先用当前可用的完整离线包或已有完整仓库重查；缺模板、品牌参考或执行依赖就先修资源。无法取得完整资源时保留资料和真实已有成品，不手写一个“候选 HTML”绕过模板，也不以代码绘画替代图像工具。完整基准见 [V10 品质标准](references/quality-workflow.md)。

读取 `references/lite-content.md`，仅从当前授权资料写 `person.json`。资料足够就做私人草稿；不为了填满页面补经历。记录实际总结者，未知型号留空。明确要求来源追溯的材料使用 `references/workflow.md`，不转换成 Lite 绕过来源审核。

```sh
PY ROOT/scripts/twinlight.py run person.json --workspace RUN --mode both
```

保存真实 `persona_digest`、字体状态、输出路径与 `next_action`。同一工作区内不改已冻结的文案、主人或模式。基础 `site/index.html` 可以先成功，它只是中间产物；both 的目标仍是已接入卡片的页面。

## 2. 用品牌参考完成当前人的卡

按 [CARD.md](CARD.md) 执行。没有明确换画风请求时，使用 `twinlight-collector` 和其随包 `style_only` 参考；不随机从四个无关美术方向中挑一个。画面题材由当前资料决定，参考只提供绘画完成度和视觉语言。

图像工具只接收当前编译任务及对应参考，不接收用户的整条“做闪卡和网站”请求。每次返回后先核对产物类型，再登记与看图；网页效果图或多卡陈列不是卡片原型。图片在聊天中自动出现也不表示本次任务结束：主执行者须取回真实文件并继续本表；有可用子任务时可把生图隔离为内部任务，由主执行者保留组装与最终回复责任。

| public 状态 | 下一步 |
|---|---|
| `needs_card` / `needs_art_direction` | 写一个具体画面，编译 `art-direction-2`；不要改人物文案 |
| `needs_art_evidence` | 执行缺失的真实图像任务，登记实际返回 |
| `needs_art_review` | 打开指定的当前图像或预览，填写实际观察 |
| `art_rejected` | 按具体缺陷修失败原型或失败层，保留其余合格素材 |
| `dynamic_unverified` | 检查浏览器和 renderer；文件存在不等于动态通过 |
| `partial_success` / `failed` | 处理报告指出的模块，继续其他独立待办 |

原型先通过审美关，再投入分层；分层只参考当前原型作图像工具原生编辑，保留画布与尺度，不再同时传入其他人物的品牌示范图重新创作主角。主角简单是指视觉主线清楚，不是把画面改成平面图标、稀疏剪纸或廉价模型。每角色最多三次真实返回，失败记录保留；达到上限仍不合格，就准确报告未完成，不用坏图占位凑成功。

## 3. 同一次运行接入成品卡

```sh
PY ROOT/scripts/twinlight.py run person.json --workspace RUN --mode both --layers CARD/layers.json
```

优先执行报告实际给出的 `next_action.resume`，保留字体、brief、浏览器参数。首次续跑会写当前 `RUN/card/front.png` 与 `preview.html` 候选；按 CARD 的 final review 实际检查这两个文件并绑定，再续跑。不能拿另一预览的观察换哈希继承批准。

public run 验证原生层、当前美术观察、模板来源、真实卡片和整页浏览器，再比较最终 HTML 内嵌的六层字节、平面预览与 persona。both 的主文件必须来自 `html_with_card`。禁止手工替换旧 HTML 的 data URI 或更新模板锁来绕过差异。

除脚本检查外，实际看最终页面的首页、进入行星、双星系交融、提问、揭卡和返回。揭卡要看到同一张通过审美的卡，不能只证明页面能加载。视觉观察要点见 `references/quality-workflow.md`。

## 4. 导出并展示同一份文件

先按 [平台适配](references/platform-adapters.md) 把最终 `primary_output` 交给宿主真实可用的 HTML 预览入口，并实际操作。在 `RUN/host-preview.json` 记录同一文件的哈希、入口和交互观察，按 [交付协议](references/delivery-v2.md) 续跑刷新报告；预览失败只处理预览，不重生卡图。

```sh
PY ROOT/scripts/deliver_artifacts.py --workspace RUN --out DELIVERY
```

导出到独立空目录，只接受当前 `complete=true` 的 public 报告。ChatGPT 的文件工具实际支持 `/mnt/data` 附件时，使用该目录内的真实 DELIVERY 并加 `--link-style sandbox`；本地宿主保持默认 `local`，不虚构沙箱路径。导出器生成 `handoff.json` 与 `delivery-reply.md`，从实际复制的文件生成附件路径、大小和哈希。

读取这两份交付材料，确认链接指向真实文件，再在同一最终回复中展示正面卡图、主 HTML 的真实预览/入口、独立卡片互动入口和完整下载包。便携卡包放在完整包中即可。不要只发图片、预告“稍后交付”或只列路径；也不要把生成的网页效果图冒充实际运行截图。原生预览引用按当前工具的输出规范返回，不能用普通附件链接代替。

完成消息区分构建完成与 `request_satisfied`，只陈述本次实测状态。宿主不能执行附件时仍可给已完成文件，但用户要求的聊天内体验保持未完成。若附件或图片没显示，检查实际文件与引用后修复；没有证据时不解释为“只是显示异常”。详情见 `references/delivery-v2.md`。

默认 `draft=true / share_allowed=false`。内容核对、美术观察和公开授权是不同状态；不自动 push、部署、公开个人资料。未完成结果可明确交付成功模块和真实候选预览，不能使用 complete 导出器伪装完成。
