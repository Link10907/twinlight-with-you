# AI 眼中的你：SSR 角色 brief

你要把这个人已有证据的来路，化成一张属于他的原创角色卡，而不是把每个人夸成同一个“筑星者”。所有卡 rarity 固定 SSR；不生成战力、百分比或排名。

先给 card 填：简短中文名、英文副标题、一句具体但有温度的 tagline、有限范围的 reflection、1–3 关键词、最多2个视觉符号。每一项都引用已核对的 fact_ids。视觉风格遵从用户批准的幻想插画方向；没有照片则明确 original_character，不虚构本人长相。

署名取本次 summary_meta。例如 GPT 生成 JSON → “在 GPT 眼中，你是什么样的？”；若输入是 Claude 导出但本次由 GPT 总结，仍是 GPT。模型版本未知留 null。不要写“这个 AI”，不要把 GPT 和 Claude 同时放上去让用户选。

运行 art-brief 后使用获授权图像工具按同一画布生成真正独立图层。细节见 references/art-direction.md。主体图不带文字、SSR 徽章或边框；背景必须消除人物并补绘，不能留下第二个人影；lineart 从最终 subject 派生。

先看正面与左右两侧真实渲染，再调紧凑层距，保留示例中人物和背景相对移动的层次。关闭 foil 仍要有视差；不把多张不透明整图堆叠。没有可用生图工具时输出 brief 与 pending 状态，不假装已完成。
