"""Deterministic semantic-ID layout. Particle counts NEVER stand for achievements."""
from __future__ import annotations
import math
from .common import check, digest, schema_check

COLORS = [[1,.55,.18],[.40,.70,1],[1,.28,.07],[.40,.86,1],[.65,.43,1]]
PLANET_COLORS = [[.68,.51,.38],[.29,.58,.73],[.69,.43,.27],[.69,.72,.59],[.79,.67,.49],[.46,.72,.79],[.59,.64,.79],[.72,.61,.82]]

def unit(seed: str, key: str) -> float:
    return int(digest([seed,key])[:13],16)/float(16**13)

def make_layout(analysis: dict, history: dict, previous: dict | None = None) -> dict:
    owner = analysis["owner"]["id"]
    seed = digest(["twinlight-layout-v1", owner])
    themes = sorted(analysis["themes"], key=lambda t:t["id"])
    check(1 <= len(themes) <= 8, "Need 1–8 evidence-backed themes; merge explicitly rather than invent or silently discard")
    old_stars, old_topics = {}, {}
    if previous:
        schema_check(previous, "layout.schema.json")
        check(previous["owner_id"] == owner and previous["seed"] == seed, "Layout lock belongs to another owner/version")
        check(previous["layout_digest"] == digest({k:v for k,v in previous.items() if k!="layout_digest"}), "Layout lock was altered")
        old_stars = {s["id"]:s for s in previous["stars"]}
        old_topics = {(s["parent_id"],s["id"]):s for s in previous["topics"]}
    taken = [old_stars[t["id"]]["position"] for t in themes if t["id"] in old_stars]
    stars = []
    for t in themes:
        tid = t["id"]
        if tid in old_stars:
            stars.append(old_stars[tid]); continue
        candidates = []
        for j in range(64):
            radius = 38+(j%3)*29+unit(seed,tid+f":r:{j}")*7
            angle = j*2.399963229728653+unit(seed,tid+":angle")*.7
            p = [round(radius*math.cos(angle),4),round(4+unit(seed,tid+":height")*5,4),round(radius*math.sin(angle),4)]
            candidates.append((unit(seed,tid+f":candidate:{j}"),p))
        candidates.sort(key=lambda c:c[0])
        chosen = next((p for _,p in candidates if all(math.dist(p,q)>=34 for q in taken)),None)
        check(chosen is not None, "Layout packing failed; reduce density rather than overlap main stars")
        material=int(unit(seed,tid+":material")*5)%5
        stars.append({"id":tid,"position":chosen,"material":material,"color":COLORS[material]})
        taken.append(chosen)
    facts={f["id"]:f for f in analysis["facts"]}
    messages={m["id"]:m for m in history["messages"]}
    topics=[]
    for t in themes:
        max_old=max([p["orbitRadius"]+p["radius"] for key,p in old_topics.items() if key[0]==t["id"]],default=9)
        inner=max_old+3
        items=sorted(t["topics"],key=lambda p:p["id"])
        for j, topic in enumerate(items):
            key=(t["id"],topic["id"])
            if key in old_topics:
                topics.append(old_topics[key]); continue
            k="/".join(key)
            conversations={messages[r["message_id"]]["conversation_id"] for fid in topic["fact_ids"] for r in facts[fid]["evidence"]}
            radius=round(min(2.7,1.2+.36*math.log2(1+len(conversations)))+.22*unit(seed,k+":size"),4)
            orbit_radius=round(inner+radius,4)
            inner=orbit_radius+radius+2.7
            check(orbit_radius <= 80, "Retained orbit slots exhausted; explicitly reset layout lock after review")
            topics.append({"id":topic["id"],"parent_id":t["id"],"radius":radius,"orbitRadius":orbit_radius,
                "eccentricity":round(.03+.08*unit(seed,k+":ecc"),4),"inclination":round(-.12+.42*unit(seed,k+":inc"),4),
                "nodeAngle":round(unit(seed,t["id"]+":node")*math.tau+(unit(seed,k+":node")-.5)*.25,5),
                "phase":round(unit(seed,k+":phase")*math.tau,5),"material":int(unit(seed,k+":mat")*5)%5,
                "color":PLANET_COLORS[int(unit(seed,k+":color")*8)%8]})
    value={"version":"1.0","owner_id":owner,"seed":seed,"stars":stars,"topics":topics}
    value["layout_digest"]=digest(value)
    schema_check(value,"layout.schema.json")
    return value
