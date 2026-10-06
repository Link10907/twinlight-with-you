# 具体画面契约：art-direction-2

生产顺序见 [AGENT](../AGENT.md) 与 [CARD](../CARD.md)。这个文件只说明字段、参考用途和接口，不引入另一套流程。

## 画风与主体分开

`assets/art-styles/catalog.json` 记录已安装风格及默认值。默认 `twinlight-collector` 保留用户认可的 V10 精细幻想收藏卡完成度；森系选 `forest-fantasy`，国风/工笔青绿选 `eastern-fantasy-scroll`，另有 `real-life-cinematic`、`futuristic-clean`、`paper-craft-story`。这些是用户明确换画风时的选项，不是每轮随机选择菜单。小鹿等具体主体单独写入 subject，不能把选择森系等同于选择鹿。版本以实际文件为准。

`style` 管线条、材质、光线、细节组织和排字默认值；`subject` 管当前的具体角色；`scene` 管当前空间与动作构图；任务 role 管本次实际图层。清楚的一位主角仍可以处在有组织的丰富环境中。

明确选定画风后，scene 可以说明场景、时间和光源，preferences 可以保留本次偏好；不要在这些字段里再写一套与所选 style 冲突的画法。验收换画风是否生效，要同时看主体与环境的笔触、材质、配色和光照，不以换服装、换物种或背景变绿作为依据。森系参考只提供视觉标准，出现鹿不意味着当前主体也要选鹿。

## 设计字段

schema 为 `schemas/art-direction-v2.schema.json`，写好后先用 `visual_plan.py check` 验证。

- `subject`：kind、具体 species、gender_presentation、age_impression、两到五个不同部位的 appearance、clothing、expression、pose、main_prop、representation、selection_basis。动物写具体物种；物件用 `not_applicable`。`main_prop` 为 null 或一个已选定的道具，接触的手、衣服和道具保留同层。
- `scene`：setting、lighting、composition、foreground。写可画的环境、光源、主体大小与焦点、文字留白；foreground 是一到两类少量具体近景，不是第二主角。
- `preferences`：保留当前用户偏好、否决方向、依据与被否决图 hash。不能把旧例子的角色细节当成新用户偏好。
- `selection_reason` 与 `selection_basis`：记录当前资料到画面设计的理由，不发给图像模型。程序从可见形象字段派生 `visual_keywords`；`card.keywords` 仍只是卡面文案。
- `typography`：从所选风格的 `typography_default` 开始，必要时调整文字/点缀/渐变底衬颜色、opacity、frame 与 footer_top；支持的 `layout` 以当前 schema 为准。默认 collector 版式保留大标题、SSR 与精致双线框，不能随意换成网页信息面板。

无照片用 `representation=original_concept`，不声称还原本人。`user_reference` 本人肖像必须有当前实际图像引用与 consent。具体形象字段描述绘画方案，不推断用户真实外貌、性别或族裔。

## 两种参考不能混用

**品牌审美参考**由所选 style 的 `reference_manifest` 提供，标记 `style_only`。普通 skill 包就包含它们，不需要导入 demo 人格。参考用来对齐完成度、材料、焦点和空间，不复制主角、场景、姿势或参考像素。新的人物示范图与自然生物示范图都属于这一用途；人物示范图的近景脸部比例不是所有卡片的构图模板。

**当前设计参考**用 design 的 `references` 和 `reference_basis` 记录。`text_only` 表示当前人没有额外图像参考，不否认程序会附带品牌参考；`visible_images` 必须有实际读取过的本地图像与 hash。

compile 会把实际需要的图像放进 CARD 目录，jobs 的 `reference_images` 记录相对文件、sha256 与 purpose，`referenced_image_paths` 提供工具可用的绝对路径。宿主必须实际传图；只把路径或 hash 写进 prompt 不算使用参考。prototype 阶段实际传入品牌 `style_only` 图；layers 阶段只使用本次已通过原型作 `composition` 编辑画布，它已经承载通过审查的画风。原生编辑保留完整视野、尺度、形态和坐标，删除/补全非当前层内容；不再次附带其他主体的品牌图让工具重新创作。

图层 job 用 `operation=image_edit`、`edit_base` 和 `coordinate_policy=preserve_full_canvas` 表明编辑对象与坐标约束。宿主按实际图像接口把 edit_base 对应图片作为编辑参考传入，不把这些元数据误当成工具支持的同名参数。

style 版本、文件 hash 和审美参考 hash 都绑定当前计划与观察。原型调用证明实际用了品牌参考；每层调用证明实际编辑当前原型，依赖该原型的有效品牌来源链。任一变化都要重新审查受影响部分，不能改哈希继承旧批准。

## 实际图像能力与画布

记录真实接口能力，不复制示例当证明。工具有明确尺寸参数时，`native_canvases` 写实际已知支持的画布。工具只接受文字请求尺寸时可使用：

```json
{
  "version": "image-capabilities-1",
  "image_generation": true,
  "reference_images": true,
  "native_transparency": true,
  "canvas_selection": "prompt_only",
  "native_canvases": [],
  "source": "替换为本轮实际可调用接口及其参考图、透明开关的观察依据"
}
```

`prompt_only` 承认尺寸由文字请求，不能假称有未暴露的 API 参数。工具实际返回后才记录真实宽高。renderer 使用约 3:4 竖幅，后续层锁定已通过原型的逻辑画布。原生 `image_edit` 输出仅宽/高各相差最多 1 像素、且实际画面未变尺度或取景时，允许显式 `canvas_mapping.version=native-rounding-1`，记录逻辑 canvas、`sampling=full_uv_bilinear` 与允许的 native_edit_roles。保留源图原字节和真实尺寸；只有显示/合成采样映射到共同画布。旧独立重画、超过此容差或可见构图漂移仍需修复，不能改原图尺寸或伪写返回参数。

## 图层和真实记录

background 通过图像工具移除人物、道具及指定近景并补全中远景，完整不透明；subject 和 effects 在同一原型坐标内原生编辑、输出真实透明；spirit 默认同尺寸空层；text 独立排字且 depth=0；lineart 从最终 subject alpha 同原生像素派生，text 使用逻辑画布；显示映射不改这些源文件。编译器按层写编辑任务，背景不接收需要新画的人物外貌，前景只保留指定内容。工具原生编辑可以使用；程序抠图、去背景、裁剪和像素重摆不能冒充原生图层。

`compile` 不调用图像服务；`record` 保存真实原图、实际返回记录、提示和参考绑定。`bind-review` 绑定看过的真实文件；它们不是外部服务认证或本人公开授权。详情见 [美术记录](art-evidence-format.md)。旧 v1 brief 仅用于历史兼容与诊断，不替代当前 public 成品关口。
