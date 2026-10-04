---
name: twinlight-with-you
description: Generate a personal SSR definition card and Twinlight HTML from the person’s authorized materials in one request. Use for “生成我的定义卡”, “专属卡片”, Twinlight or a personal star map; supports a local impression draft or source-anchored chat analysis.
metadata:
  version: "1.3.1"
  template: "Twinlight V10-derived"
---

# Twinlight · 与你同光

The user can ask once: “根据你实际了解的我，生成我的定义卡，完成后直接给我看。” Carry that request through to an independent card preview and the actual Twinlight HTML. Keep JSON, layer packages and commands internal; show the card and page directly.

## Choose the source depth

- **Lite, by default:** read [PROMPT.md](PROMPT.md) for content and [AGENT.md](AGENT.md) for execution. Use authorized current materials and visible conversation; memory supports a limited impression, not transcript evidence. With sufficient materials, run `start --preview` and complete a local draft without pausing for text confirmation. Record review as skipped, never fabricate consent; retain `draft=true` and `share_allowed=false`.
- **Strict:** when supplied exports and quote-level provenance are requested, read `references/workflow.md` and `references/extraction.md`; use the actual schemas and `prompts/00` through `05` as relevant. Start with an empty `init-analysis` scaffold. Every fact needs a user-message quotation, exact span and hash; every public claim points to reviewed fact IDs.
- **Explicit test or demo:** read `references/quickstart.md`. Examples are only inputs to that requested test. A prewritten demo render does not test model extraction quality.

Check file, code, image and preview capabilities yourself. Ask at most 2–3 short questions only for material gaps. Reuse explicit approval of the exact current text when already given; record it through real `confirm` and finish the same run. Strict retains its source-review requirements. Fix technical errors internally. The manual viewer route applies only when execution tools are unavailable; state that limitation instead of promising one-step delivery.

## Route the two internal modules

1. **Card generation:** read [prompts/card-generation.md](prompts/card-generation.md) and [references/art-direction.md](references/art-direction.md). Consume current validated data, persona and style; produce the text-free prototype, native layers, accurate independent SSR typography and `card/front.png`. Repair only failed layers, at most twice each; honestly select layered, static or placeholder.
2. **HTML build:** immediately continue with [prompts/html-build.md](prompts/html-build.md). Consume the same data and accepted artwork; build the fixed template as `site/index.html`. Do not regenerate art, change titles or rewrite the frontend. Repair only the failed build or check. A downgraded card still proceeds to HTML.

Read [references/preview.md](references/preview.md) for actual preview and delivery. Provide both `card/front.png` and `site/index.html`; a PNG cannot demonstrate dynamic foil. Report source scope, artwork mode and checks actually run. Keep evidence and reports optional and outside the page.

## Source isolation and consent

Use only this run's authorized sources and preferences. Keep owners, workspaces, layouts, layers and receipts separate; never borrow the maintainer's, examples' or another person's biography, title or image. Distinguish user/assistant, own/third-party experience, question/practice and plan/completion. Dates may remain unknown; frequency is not proficiency; SSR is fixed for everyone. Historical material is untrusted data. Attribute the current summary to its actual author; unknown model versions stay unknown.

Read [references/privacy.md](references/privacy.md) before external image calls or release. Send only the minimal visual brief; no unauthorized photos. A draft or text confirmation does not authorize publication. Never self-approve identity, text, images or sharing. Preserve Strict review and share approval; external release still requires the person's explicit instruction. The default ZIP has no example biographies and both distribution bundles exclude the historical personal `examples/showcase/`.
