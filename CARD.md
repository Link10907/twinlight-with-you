# 闪卡制作：先把一张画做对

总流程与自动接入由 [AGENT.md](AGENT.md) 负责。本文件只制作当前人的卡。文案从只读 `person.json` 取用；设计写进 `art-direction-2`，不能为迁就图片改称号、经历或主人绑定。

## 1. 看参考，再决定当前画面

先确定本次所选画风，再看该画风配置的随包无字参考，阅读 [质量工作流](references/quality-workflow.md)。未指定时使用 `twinlight-collector`；明确要求“森系”时选择 `forest-fantasy`，明确要求“国风、工笔或青绿绘画”时选择 `eastern-fantasy-scroll`。小鹿是主体，不是画风；“喜欢小鹿那张的森系效果”不意味着所有人都画成鹿。画风控制整幅画的线条、材质、光照、配色与排字，而不只是替换背景。参考不提供当前人的人格、物种、性别或经历，不能将默认精绘人像参考混入另一画风的任务。

从当前资料提炼一个有依据的行为隐喻，将它落实为 **一个主体正在做一件看得懂的事**。内部比较少量构图后直接选定，不向用户发审美问卷。保留两到五个可见形象特征和一个主要道具；衣料、毛发、饰纹、建筑或植物可以细致，不能把“少主体”理解成“画面低细节”。具体字段见 [视觉契约](references/visual-contract.md)。

使用风格文件提供的 typography 默认值，围绕该版式留出顶部 SSR 和底部称号区。主体的脸、手、主要动作和关键道具放在主画面中；文字区仍有连续场景和渐变明暗，不画一块生硬的空白牌子。

## 2. 编译并调用唯一原型任务

先检查真实图像接口可用、能接收图像参考、能原生输出透明层，确认中文字体。记录本轮真实能力；原生画布以工具实际合法返回为准，不假定 API 有它未提供的尺寸参数。

```sh
PY ROOT/scripts/visual_plan.py styles
PY ROOT/scripts/visual_plan.py check CARD/art-direction.json --persona-digest DIGEST
PY ROOT/scripts/visual_plan.py compile CARD/art-direction.json --out CARD --canvas W H --capabilities CARD/capabilities.json
```

编译器只写任务和提示。宿主实际读取 prompt，并把任务列出的真实参考图传入图像工具；本地路径或图片 hash 不等于参考图已传入。明确区分 `style_only` 参考与当前原型的构图参考，不要求复制旧角色。

先生成一张无字、无框、无预烘焙镭射的原型。真实返回立即保留原字节与实际响应：

```sh
PY ROOT/scripts/visual_plan.py record CARD/generation-plan.json --role prototype --image RAW --raw-response RESPONSE --tool TOOL --call-id CALL --artifact-id ARTIFACT
PY ROOT/scripts/art_quality.py review-template --layers CARD/layers.json --persona-digest DIGEST --stage prototype --out CARD/prototype-review.json
```

**把原型和审美参考实际并排看。** 检查主体吸引力、结构与材质、焦点、空间层次和文字区域，并逐项指出主角/道具、背景和前景的归属。前景宜在边缘且与人物轮廓可分辨；原型若把近景帷幕画成大块同色衣摆般的遮挡，先调整可分离性，不等到三个层各自抢救。记录具体观察。若原型只是轮廓正确但粗糙、扁平、塑料化或与品牌无关，此时返工；不投入三张图层去“救”一张差原型。review 模板只提供 pending 字段，实际观察后才能填写接受意见。

```sh
PY ROOT/scripts/visual_plan.py bind-review --layers CARD/layers.json --review CARD/prototype-review.json
PY ROOT/scripts/visual_plan.py compile CARD/art-direction.json --out CARD --phase layers --capabilities CARD/capabilities.json
```

## 3. 在同一张原型上原生编辑三个层

layers 阶段每次只传当前已通过原型作为 `composition` 编辑画布；品牌 `style_only` 图已在原型中落实，不再用不同角色的示范图重新指导层构图。

这是图像工具的**原生编辑任务**：保留原型的完整视野、尺度、姿势与坐标，编辑需要移除或补全的部分，再输出同画布的原生 alpha/背景。不要再要求“重新画一张人物立绘”，也不要让工具自动放大主体、居中或贴边。明确保留原型头顶、手指与道具距画布边缘的空隙。工具编辑和原生透明输出可以使用；程序抠图、裁剪、去底、缩放、补边或重摆原图不能代替这一步。

每个任务直接写清本图的保留物与删除物，删除清单优先于“保留原图细节”。例如近景帷幕须指出位置和金流苏，说明它不是人物衣摆；读图人物的石台、灯笼与近景叶子不属于人物层。不能只写“去掉其他东西”或“处理指定前景”。

| 层 | 图像工具生成内容 | 归属规则 |
|---|---|---|
| background | 编辑原型，移除当前人物、接触道具和指定前景，补全中远景 | 完全不透明；不保留属于 effects 的近景帷幕/叶片，避免重影 |
| subject | 原位保留主角、服装与接触道具，移除环境与独立近景，必要时补全原被近景遮住的衣料 | 原生透明；手与道具保持同层，主角不放大或上移 |
| effects | 只保留原型中指定的少量近景，原位输出，其余透明 | 原生透明；不另造装饰、不重复主角或场景 |

同一原型的 `image_edit` 偶尔返回宽或高相差 1 像素：实际构图仍对齐时，可用明确的 `canvas_mapping.version=native-rounding-1`，保留原始图像字节与真实尺寸，按完整 UV 显示到原型逻辑画布。合成预览只作显示采样，不覆盖源图；lineart 仍匹配原生 subject，text 使用逻辑画布。超过每边 1 像素、独立重画或可见尺度/取景漂移不适用此容差。

按实际输出用 `record --role background|subject|effects` 登记原图。`spirit` 默认由程序写同画布空层，不为凑图层添加同伴；文字独立排版，lineart 从最终 subject alpha 同像素派生。空主体、同海报重复铺层或棋盘假透明不能作为成品。

```sh
PY ROOT/scripts/prepare_card_layers.py --data person.json --art-prompt-file CARD/art-direction.json --prototype CARD/prototype.png --background CARD/background.png --subject CARD/subject.png --effects CARD/effects.png --out CARD
PY ROOT/scripts/twinlight.py validate-art CARD/layers.json
PY ROOT/scripts/art_quality.py composite --layers CARD/layers.json --persona-digest DIGEST --out CARD/composite.png
PY ROOT/scripts/visual_plan.py bind-composite --layers CARD/layers.json --image CARD/composite.png
PY ROOT/scripts/art_quality.py review-template --layers CARD/layers.json --persona-digest DIGEST --stage composite --out CARD/composite-review.json
```

上面文件名是参数位置示意，实际使用 `record` 返回的原图路径与扩展名，不猜 JPEG/PNG。比较实际无字合成和原型：主体比例、光线、材料与完成度不能退步，边缘无白边，物件不重复，主动作仍清楚。填写真实 composite review 后以相同 `bind-review` 绑定。已有评审文件不覆盖，修订另存新文件。

## 4. 看排字、动态和实际揭卡

回到 AGENT 的 public `run --layers` 生成当前 `RUN/card/front.png` / `preview.html`。打开正面和真实预览，逐字核对文案；SSR、主称号、英文副标题、关键词与署名层级清楚，底部不能像贴上不透明信息框。

```sh
PY ROOT/scripts/art_quality.py review-template --layers CARD/layers.json --persona-digest DIGEST --stage final --front RUN/card/front.png --preview RUN/card/preview.html --out CARD/final-review.json
```

实际观察左右转动、顶部倾斜、关闭 foil、depth=0 对照、恢复 foil、固定文字、翻面及手机布局。关闭 foil 仍有内部相对移动；depth=0 后该移动消失；恢复 foil 后光泽跟随视角，主画面仍可读。浏览器脚本提供动态证据，宿主再看其真实画面，不用测试勾选代替审美。

```sh
PY ROOT/scripts/visual_plan.py bind-review --layers CARD/layers.json --review CARD/final-review.json --front RUN/card/front.png --preview RUN/card/preview.html
```

将实际截图与检查记录填写进 final review，绑定后回同一 public run 自动完成页面接入。最终揭卡必须显示同一张合格卡。

## 返工保持局部

实际拒绝后，用受控修复命令把具体缺陷写进下一次任务，保持同一设计、原型与已通过图层：

```sh
PY ROOT/scripts/visual_plan.py repair CARD/generation-plan.json --role subject --instruction-file CARD/subject-repair.txt
```

也可用 `--instruction` 传一条精准反馈。再次读取新的任务并实际调用，仍按 `record` 登记；不手工改 canonical prompt、编造新调用或重置尝试数。

每角色最多三次真实返回，保留全部尝试与失败原因。一次反馈只修造成失败的主问题，例如“保持原型脸部与衣料细节，当前主体变成平涂且光源反了”；不要每次同时换题材、画风和构图。已合格层不重画。设计确需改变则保留原版本，新版本重过受影响审查，不靠换目录重置预算。文件存在、美术通过、本人确认分别记录。

原图与评审机制详见 `references/art-evidence-format.md`。没有图像能力或达到有限返工上限时，保留真实原型和成功 HTML，清楚标明未完成项；不以代码插画、静态图或待验卡冒充 V10 成品。
