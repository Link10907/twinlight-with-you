# 形象与风格 V2 契约

## 四部分，不再混为一段

固定 style 模板负责线条、造型、材质、配色和光感；subject 负责具体主体；scene 负责一个简洁画面及留白；role 负责当前图片层。风格库与 schema 是程序实际读取的资源，不只是说明文档里的风格名称。

四个 ID 为 real-life-cinematic、eastern-fantasy-scroll、futuristic-clean、paper-craft-story，版本见各文件。分别是现实质感、东方幻想、未来极简、纸绘手作，固定的是视觉语言而不是男生、鹿、服装、月夜或蓝金场景。没有全局默认风格或角色；用户最近明确要求优先。请求换风格时必须真正换 style_id 并重新创作，不仅改标题。

## 形象是可画的整句，不是人格标签

schema：`schemas/art-direction-v2.schema.json`。subject 明确 kind、species、gender_presentation、age_impression、appearance（2–5 个不同部位及其可见描述）、clothing、expression、pose、main_prop、representation、selection_basis。

“年轻成年女性，齐耳黑发，素色短外套，眉眼放松，双手捧着一只纸鹤”是具体形象；“成长、共创、创造力”不是。动物需“赤狐、灰猫、梅花鹿”等实际物种，不填笼统“动物”；物件可用一只陶碗或小灯，没有性别、没有额外道具。全部是设计选项，不默认绑定任何真实用户。

main_prop 是 null 或一个已经选定的道具，不接受“电脑/吉他/背包三选一”。与手、服装接触的物件整体留在 subject 层；不多次拆开导致拖动断裂。scene.foreground 是一两项少量具体近景，不能用一大团特效掩盖主体。

`selection_basis` / `selection_reason` 记录从授权资料到可见设计的依据，**不发送给生图模型**。`visual_keywords` 由具体字段派生，不能自行塞一列抽象人格词。`card.keywords` 仍属于文案，不改变 persona_digest。

程序拒绝已知抽象纯标签、未解占位、无物种、重复部位、多道具和未知字段，但这不是自然语言理解证明。主体是否真简洁、画风是否真正符合，需要实际看图与具体观察。

## 风格与来源绑定

每次生成 plan/call 记录 style_id、style版本和实际风格文件 hash；风格资源更新时旧调用与旧 review 不能继承。角色与画风改变时保留旧尝试，新设计独立存储；不能删除失败记录绕过每层三次上限。

reference_basis=text_only 不得声称看过参考图。visible_images 必须有实际可读图片及 hash。user_reference 本人肖像需实际图片与同意；否则原创概念，不推断脸、性别或族裔真实性。

## 能力记录

宿主自行检查实际当前图像接口，并记录：

```json
{
  "version": "image-capabilities-1",
  "image_generation": true,
  "reference_images": true,
  "native_transparency": true,
  "native_canvases": [[1080, 1440]],
  "source": "填写本轮真实接口说明或实际能力检查依据，不照抄示例"
}
```

这只是字段示例，不是能力证明。true/尺寸必须来自实际工具；不存在时不使用此示例伪装。现有原生卡 renderer 使用 3:4，优先采用工具实际支持且返回的合法全画布，不为固定名义 1080×1440 去重采样。原型返回另一合法 native3:4 时记录请求与返回尺寸，后续层锁定实际尺寸；层返回错尺寸必须修该层。

## 原图登记不是外部认证

compile 仅写实际 per-layer prompt 和待办；不调用图像服务。宿主调用可用工具并记录真实输出标识，record 按原字节保留原图、返回文本、提示记录与失败尝试。调用记录说明计划/请求传输边界，不能证明提供商内部收到逐字相同提示；不虚构不可见的 provider payload、seed 或模型版本。

原生层：background 完整不透明；subject/唯一道具原生透明；effects 少量原生透明；spirit 同尺寸空层；text 程序排版且 depth=0；lineart 为 subject alpha 的同像素轮廓。角色完整性、光照和材质一致仍需实际审查。

## 手册优先级与兼容

生产执行顺序以 SKILL → AGENT → CARD → 本契约为准。旧 art-direction-1、strict visual_style 和历史例子可用于读取旧资料或诊断，不能替代本次 v2 public 成品关口。Strict 保留其来源审核与本人审阅，不转换输入来绕过隐私与授权。

代码单元测试可以使用明确标为 SYNTHETIC 的几何与虚拟调用夹具检验拒绝条件，但它们绝不是用户成品、审美验证或真实生图成功率证据。
