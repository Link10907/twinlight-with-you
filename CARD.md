# 原生定义闪卡 · V2 接口

主规则是 `references/visual-contract.md`。只使用当前只读 person.json 的卡片文案与 persona_digest；它的称号和 identity keywords 不充当绘画词。具体形象在独立 `art-direction-2` 中，风格从四套版本化模板中明确选一套。

## 1. 具体设计与能力

一个主体（具体人类/动物/拟人动物/物件），2–5 个可见特征，一个动作、一个简洁场景、零或一个主要道具，少量近景；没有默认宠物/第二角色。物件无需性别；动物明确物种；人类可 male/female/androgynous/unspecified，不推断用户真实身份。

```sh
PY ROOT/scripts/visual_plan.py styles
PY ROOT/scripts/visual_plan.py check CARD/art-direction.json --persona-digest DIGEST
PY ROOT/scripts/visual_plan.py compile CARD/art-direction.json --out CARD --canvas W H --capabilities CARD/capabilities.json
```

`capabilities.json` 记录实际当前工具的生图、参考图片、原生 alpha 和合法 native_canvases，格式见 visual-contract。不知道就 unknown，不写 true。现有渲染器使用原生 3:4；不支持时明确能力缺口，不补边、缩放或裁剪冒充。

编译仅产生 prompt/任务，不生图。先执行唯一 prototype 任务：实际读 prompt 文本、把实际参考图片传入支持的工具，不把本地路径当已传入。保存工具返回原图字节、工件 ID、调用 ID 和脱敏后的真实响应。

## 2. 原型登记与审查

```sh
PY ROOT/scripts/visual_plan.py record CARD/generation-plan.json --role prototype --image RAW --raw-response RESPONSE --tool TOOL --call-id CALL --artifact-id ARTIFACT
PY ROOT/scripts/art_quality.py review-template --layers CARD/layers.json --persona-digest DIGEST --stage prototype --out CARD/prototype-review.json
```

实际打开无字原型，看主体轮廓、具体特征、风格、动作、简洁度和排字空间，再由宿主填写真实 observer/time/checks/capture。不合格则修原型，不进入分层。

```sh
PY ROOT/scripts/visual_plan.py bind-review --layers CARD/layers.json --review CARD/prototype-review.json
PY ROOT/scripts/visual_plan.py compile CARD/art-direction.json --out CARD --phase layers --capabilities CARD/capabilities.json
```

layers 阶段采用原型实际返回的合法尺寸，只有当前 prototype review 通过才输出背景、主体、前景任务。每层传同一参考图、同一构图；background 不接收完整人物描述，subject 不接收整幅场景，effects 只描述少量近景。

## 3. 原生层与合成

分别真实调用并以 `record --role background|subject|effects` 登记。背景不透明且无重复主体；主体含服装、接触物和唯一道具；effects 少而轻且透明。默认不加 spirit 角色，由装层程序生成同画布空 spirit；空 subject/effects/text 不合格。

```sh
PY ROOT/scripts/prepare_card_layers.py --data person.json --art-prompt-file CARD/art-direction.json --prototype CARD/prototype.png --background CARD/background.png --subject CARD/subject.png --effects CARD/effects.png --out CARD
PY ROOT/scripts/twinlight.py validate-art CARD/layers.json
PY ROOT/scripts/art_quality.py composite --layers CARD/layers.json --persona-digest DIGEST --out CARD/composite.png
PY ROOT/scripts/visual_plan.py bind-composite --layers CARD/layers.json --image CARD/composite.png
PY ROOT/scripts/art_quality.py review-template --layers CARD/layers.json --persona-digest DIGEST --stage composite --out CARD/composite-review.json
```

路径按真实返回使用，PNG/JPEG/WebP 扩展名不猜。先完成无字合成实际看图，确认无变形、重复物件、白边、错误遮挡和画风漂移，再绑定 composite review。已有同名输出不覆盖：返工时保留旧版本/观察记录，用新文件名重新绑定。

文字由程序准确排版，不调用图像模型画字；称号、署名保持当前文案；lineart 从最终 subject alpha 同像素派生。不要为了排字删掉已确定文字或改动人物绑定。

## 4. 最终效果与 HTML

按 `AGENT.md` 回 public run 产生当前 front/preview 候选。在真实独立预览中观察左右视角、关闭 foil 的层内位移、depth=0 对照、视角驱动 foil、固定文字、手机可读性、拖动/触摸/键盘/减少动态。浏览器脚本不代替实际美术观察。

```sh
PY ROOT/scripts/art_quality.py review-template --layers CARD/layers.json --persona-digest DIGEST --stage final --front RUN/card/front.png --preview RUN/card/preview.html --out CARD/final-review.json
PY ROOT/scripts/visual_plan.py bind-review --layers CARD/layers.json --review CARD/final-review.json --front RUN/card/front.png --preview RUN/card/preview.html
```

填写的是当前真实观察；final views/capture 引用实际截图和检查记录。再回相同 public run 完成接入，最终交付 `html_with_card`。不单独 patch 几 MB HTML，不拿 static 原型、伪空层、整页效果图裁卡或多份相同海报交差。

每角色至多三次真实返回；失败记录保留，必要的一次明确构图修订依旧不移动、裁剪或重采样原生层。未成功时保留已成功模块和准确未完成状态，不复用被否决图凑通过。
