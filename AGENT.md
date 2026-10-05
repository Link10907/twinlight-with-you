# 一次请求编排 · V2

宿主负责内容理解、真实图像工具、实际看图与展示。程序负责输入冻结、版本化提示词、原图登记、构建、字节比对、浏览器与导出。程序不生图、不看懂人物、不授予公开许可。

以下 `PY` 是可用 Python 3.10+；`ROOT` 是本次完整项目，所有命令由宿主执行。默认是一个人的一个私人 workspace；不要复制示例人格。

## 1. 开始

按 `PROMPT.md` 检查完整资源与模板锁。读取 `references/lite-content.md`，从当前授权资料写 `person.json`；美术不写入此文件。资料充分时直接生成私人未确认草稿，不编造经历或肖像。明确只要卡片可用 card-1。

```sh
PY ROOT/scripts/twinlight.py run person.json --workspace RUN --mode both
```

未生成卡片时基础 HTML 可以先完成，但不是 both 的最终交付。保存 public 返回的真实路径、persona_digest、字体状态和 `next_action.resume`。输入冻结后不在相同 workspace 改人物、文案或模式。

## 2. 独立完成美术

`needs_card` / `needs_art_direction`：按 `CARD.md` 写 `art-direction-2`，选择明确的 style.id/version，并把一个具体形象说明编译成真正的 per-layer prompt。保留当前人的偏好与否决项，不固化作者形象。

`needs_art_evidence`：执行缺失的真实图片工具任务或登记已有真实返回，不能手写不存在的调用。`needs_art_review`：打开当前指定原型/合成/最终图，做具名观察；pending 模板不能自动批准。`art_rejected`：只重生失败层，保留合格原图。每层最多三次返回尝试，不能换目录假装重新获得次数。

所有当前文件、工具返回、文字和评审属于同一 persona。由 `visual_plan.py` 编译、登记和绑定记录；旧图复用必须明确同主人与范围。完成合成后用原排字脚本输出固定文字和同像素轮廓。

## 3. 自动续跑接入

```sh
PY ROOT/scripts/twinlight.py run person.json --workspace RUN --mode both --layers CARD/layers.json
```

优先使用实际 `next_action.resume`，保留输入、模式、字体、brief 和浏览器参数。第一次会生成最终候选 `RUN/card/front.png` / `preview.html`；最终美术 review 必须绑定这两个真实文件。观察并绑定后续跑；不要把另一份预览的哈希改掉继承旧意见。

public run 检查版本化形象、原生层、三阶段观察、固定模板、卡片浏览器和 HTML 浏览器，并重新比较最终 HTML 中六层原始字节与所选素材，含两份 persona 与平面预览。任何一处不一致，都不能选择旧基础 HTML 凑成品。

`partial_success` / `failed`：按失败模块修复，继续独立待办；不要重画成功卡或丢失成功 HTML。`dynamic_unverified`：文件可保留，但动态未验不能完整交付；CSS 降级不能证明镭射通过。

## 4. 交付同一份实际成品

```sh
PY ROOT/scripts/deliver_artifacts.py --workspace RUN --out DELIVERY
```

导出器只接收当前 complete=true 的 public 报告，逐个核对输出哈希；both 模式主文件必须来自 `html_with_card`。导出目录必须独立且空。交付 HTML、front、独立 preview、便携卡包，必要限制保持简短；内部来源与字体文件不打包给用户。

未完成时直接保留 public outputs / 标注清楚的 candidate_outputs，明确缺口，不使用 complete 导出器伪装成功。

## 5. 预览与权限

分别报告文件完成、本地浏览器验证、聊天内预览。`host-preview.json` 只记录本次宿主对相同文件的实际观察与 hash；默认 not_tested，不凭浏览器截图、账号品牌、下载成功推定 available。无法内嵌执行时交付本地可开的单文件及真实静态预览，不能再生成一个伪网页图片替代。

私人草稿、本人文本确认、宿主美术观察、来源认证是不同状态。保持 draft=true / share_allowed=false；发布必须另外获得明确授权。不得为解决预览问题把个人内容自动部署到公共仓库。
