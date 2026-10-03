"""Compile audited semantic content into the stable V10-derived page contract."""
from __future__ import annotations
from collections import defaultdict
from .common import ROOT, check, digest, load, privacy_findings, schema_check
from .evidence import verify
from .layout import make_layout


def compile_profile(history: dict, analysis: dict, previous: dict | None = None) -> tuple[dict, dict, dict]:
    audit = verify(history, analysis)
    layout = make_layout(analysis, history, previous)
    facts = {f["id"]:f for f in analysis["facts"]}
    messages = {m["id"]:m for m in history["messages"]}
    chapters = []
    for theme in sorted(analysis["themes"], key=lambda t:t["id"]):
        dates = sorted({messages[r["message_id"]]["timestamp"][:10] for fid in theme["fact_ids"]
                        for r in facts[fid]["evidence"] if messages[r["message_id"]]["timestamp"]})
        period = (dates[0]+(" — "+dates[-1] if dates[0]!=dates[-1] else "")+" · 记录日期") if dates else "记录日期未确认"
        topics = []
        for topic in sorted(theme["topics"], key=lambda t:t["id"]):
            kinds = {facts[fid]["kind"] for fid in topic["fact_ids"]}
            status = "计划中" if kinds <= {"plan"} else "探索中" if kinds <= {"question","plan"} else "已有记录"
            topics.append({"id":topic["id"],"name":topic["label"],"title":topic["summary"]["text"],
                           "body":[topic["summary"]["text"]],"quote":None,"status":status,
                           "provenance":"来自已核对的用户陈述；原始片段保存在本地审查文件中。"})
        chapters.append({"id":theme["id"],"label":theme["label"],"english":theme["english"],"period":period,
            "headline":theme["headline"]["text"],"story":[s["text"] for s in theme["paragraphs"]],
            "reflection":theme["reflection"]["text"],"changes":[],"tags":[t["name"] for t in topics[:5]],
            "transition":"循着微光，走向下一段记录。","signature":theme["headline"]["text"],"quotes":[],
            "topics":topics,"letterClosing":"这些记录，是来路，不是定论。","collaboration":"先核对你留下的话，再写下理解。",
            "companion_year":int(dates[-1][:4]) if dates else None,"ai_context_ids":[],
            "ai_trace":{"product":"未确认","model_id":None,"reported_name":None,"status":"unknown",
                        "source":"本章未绑定消息级模型证据","note":"不由日期、词语或总结者反推历史模型。"}})
    meta=analysis["summary_meta"]
    source_card=analysis["card"]
    evidence=[]
    if source_card:
        for item in source_card["keywords"]:
            evidence.append({"title":item["label"],"text":"；".join(facts[fid]["statement"] for fid in item["fact_ids"][:2])[:160]})
    persona={"version":"1.0","name":analysis["owner"]["display_name"],"rarity":"SSR",
             "title":source_card["title"] if source_card else "星旅者",
             "english_title":source_card["english_title"] if source_card else "A JOURNEY IN LIGHT",
             "edition":meta["generated_at"][:7].replace("-","."),
             "keywords":[k["label"] for k in source_card["keywords"]] if source_card else ["记录"],
             "line":source_card["tagline"]["text"] if source_card else "每一段来路，都值得被认真看见。",
             "reflection":source_card["reflection"]["text"] if source_card else "资料有限，暂不生成稳定的人格判断。",
             "evidence":evidence,"art_type":"等待独立分层图；没有真人参考时仅为原创角色概念。",
             "disclaimer":"本卡是本次材料范围内的创作性理解，不是人格诊断或能力排名。每张卡都是 SSR。",
             "summarizer":meta,"persona_digest":digest({"owner":analysis["owner"],"card":source_card,"author":meta}),
             "content_ready":bool(source_card),"art_status":"placeholder"}
    profile={"version":"1.0","name":analysis["owner"]["display_name"],"owner_id":analysis["owner"]["id"],
             "intro":"每一颗微光，都有来处。","chapters":chapters,
             "summary_meta":meta,"ai_history":load(ROOT/"assets/ai-history.json")["events"],"ai_usage":[],
             "layout":layout,"persona":persona,
             "coverage":{"scope":history["coverage"]["scope"],"start":history["coverage"]["start"],"end":history["coverage"]["end"],
                         "account_history_complete":False,"description":"仅基于本次可见材料，不代表全部历史。"},
             "release":{"draft":True,"share_allowed":False}}
    # Raw export content, native IDs and private evidence hashes are deliberately absent.
    check(not privacy_findings(profile), "Public copy contains potential secrets/contact details; redact and review, do not print the value")
    profile["content_digest"]=digest({"owner_id":profile["owner_id"],"chapters":chapters,"summary_meta":meta,"persona_digest":persona["persona_digest"]})
    return profile,layout,audit


def art_brief(analysis: dict, persona_digest: str) -> dict:
    card=analysis["card"]
    check(card is not None,"Not enough reviewed persona content for an art brief")
    return {"schema_version":"1.0","persona_digest":persona_digest,"rarity":"SSR","portrait_mode":card["portrait_mode"],
            "reference_consent":card["reference_consent"],"visual_style":card["visual_style"],
            "symbols":[s["description"] for s in card["symbols"]],
            "canvas":{"width":1080,"height":1440,"same_coordinates_for_all_layers":True},
            "layer_order":["background","spirit","subject","effects","text"],
            "depths":{"background":-.25,"subject":.4,"effects":.5,"text":0},
            "typography":{"title":card["title"],"english_title":card["english_title"],"rarity":"SSR",
                          "signature":(analysis["summary_meta"]["display_name"] or "总结来源未标注")+" 眼中的你",
                          "keywords":[k["label"] for k in card["keywords"]]},
            "rules":["Preserve the approved original illustration style and character composition.",
                     "Subject/effects/text must have real alpha; background must be opaque and repaired behind the removed subject.",
                     "Do not leave the character in the background: that causes ghost faces during parallax.",
                     "Do not bake rainbow foil, typography or SSR badges into the subject image.",
                     "Derive lineart from the actual subject, never redraw it separately.",
                     "Use available authorized image tools; if unavailable, deliver this brief and mark artwork pending, never invent a completed render."]}


def check_approval(analysis: dict, receipt: dict) -> None:
    schema_check(receipt,"approval.schema.json")
    check(receipt["analysis_digest"]==digest(analysis),"Approval is stale; content changed after review")


def review_markdown(history: dict, analysis: dict) -> str:
    report=verify(history,analysis)
    lines=["# Twinlight 本地审查稿", "", "> 含原话，只保存在本地；不要提交到公开仓库。", "",
           f"材料范围：{history['coverage']['scope']}；{report['accounted_user_messages']}/{report['user_messages']} 条用户消息已有处置记录。",
           "这不是对全部账户历史的完整性声明。程序核对引用，不能代替语义审查。", "",
           f"总结署名：{analysis['summary_meta']['display_name'] or '来源未标注'}", "", "## 事实逐条核对", ""]
    for fact in analysis["facts"]:
        lines.extend([f"### {fact['id']} · {fact['review']} · {fact['kind']} / {fact['status']}",fact["statement"],""])
        for ref in fact["evidence"]:
            lines += [f"原文位置：`{ref['message_id']}`，字符 {ref['start']}–{ref['end']}（左闭右开）", "", *["> "+q for q in ref["quote"].splitlines()], ""]
        lines += ["请核对：这说的是本人吗？是否只是计划/提问/例子？是否仍然有效？是否允许对外展示？", ""]
    lines += ["## 将出现在网页上的文案", ""]
    for theme in analysis["themes"]:
        lines += [f"### {theme['label']}",theme["headline"]["text"],"",*[p["text"] for p in theme["paragraphs"]],"",theme["reflection"]["text"],""]
        for topic in theme["topics"]: lines += [f"- {topic['label']}：{topic['summary']['text']}"]
    if analysis["card"]:
        c=analysis["card"];lines += ["",f"## SSR · {c['title']}",c["tagline"]["text"],c["reflection"]["text"],""]
    lines += ["## 许可检查", "", "确认前不得记录 approved。CLI 收据只是确认记录，不是数字身份认证。",
              f"分析快照 SHA-256：`{digest(analysis)}`", ""]
    return "\n".join(lines)
