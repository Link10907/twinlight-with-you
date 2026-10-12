# 卡片窄输入契约

`card-image-input-1` 只定义画什么，不定义这个人是谁、网站如何交付。

```json
{
  "version": "card-image-input-1",
  "style": {"id": "twinlight-collector", "version": "1.0.0"},
  "subject": {
    "kind": "human", "species": "人类", "gender_presentation": "male",
    "age_impression": "青年成年人",
    "appearance": [
      {"part": "hair", "description": "黑色短发，略微自然卷"},
      {"part": "eyes", "description": "深棕眼睛，目光专注"}
    ],
    "clothing": "深蓝短外套，领口少量银线刺绣",
    "expression": "神情平静，嘴角微扬",
    "pose": "侧身站立，双手在胸前调校黄铜测量仪",
    "main_prop": "一件小型黄铜测量仪",
    "representation": "original_concept"
  },
  "scene": {
    "setting": "安静的石墙工作室，一扇高窗透入柔光",
    "lighting": "左上方暖光，右侧柔和冷色反射",
    "composition": "半身主角居中，脸和双手位于上方三分之二，顶部与底部保留低对比连续环境",
    "foreground": ["右下角一小段虚焦帷幕"]
  }
}
```

这是格式示例，不是默认画风、预设用户身份、固定角色或合格作品。本契约接收已确定的 style、subject、scene。主体也可选择具体动物、拟人动物或物件。

上层把可见偏好写入对应字段。未列字段报错；图像请求不携带姓名、称号、关键词、总结模型、persona_digest、selection_basis、selection_reason、preferences、排字配置或主页面数据。私有 art-direction-2 仍可保存绑定/排字信息，但编译器只白名单投影。

单条描述有限长，整体输入≤2800字符；原型提示≤2200字符，图层提示≤1200字符；超限要求简化，不静默截断。生成提示通常明显短于上限。返工句≤240字符；只发当前修复，不叠加审查历史。

含URL、代码、网页/首页/终章等任务文本的形象字段会拒绝；这是防常见误混的检查，不是识别所有语义污染的保证。实际图像仍须独立审查。

原型只附当前画风的随包 style_only 图片。`original_concept` 禁止任意外部参考。本人肖像路径需要本轮可用照片及授权：在私人 art-direction-2 内明确 `representation=user_reference`、`reference_consent=true`、真实 `references` 与 `reference_basis=visible_images`；宿主先确认附件仅为授权人物参考，不是网页拼贴。哈希只能确认相同图片，不能证明它的内容合格。

分层唯一参考为已通过原型。图层请求不重新投原型的角色描述/完整画风菜单，只说保留、移除、透明与坐标要求。主体/道具及前景按角色唯一归属。

`execution.py image` 在 dispatch 再重建并比对短提示；手写追加后即使更新普通文件哈希也会拒绝。实际provider请求保存于私人calls目录。命令路线在项目外临时目录运行，只复制当前输入；拒绝resume参数，但不声称这是OS沙箱，也不认证第三方命令内部无记忆。

卡片审查另外投影可见形象与画风；仅final/card release加冻结文字和真实动态证据。不把card-input.json整份丢给生图，不把整站手册丢给卡片审查。
