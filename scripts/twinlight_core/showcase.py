"""Optional private legacy showcase. Never a default demo or a skill-package asset."""
from __future__ import annotations
import copy
import hashlib
from pathlib import Path
from .common import ROOT, VERSION, check, load, save, digest
from .site import uri, write_site

SHOWCASE=ROOT/'examples/showcase'
NODES=[[-68,5,-12],[-31,6,-73],[29,7,-1],[67,5,56],[-20,7,90]]
COLORS=[[1,.55,.18],[.40,.70,1],[1,.28,.07],[.40,.86,1],[.65,.43,1]]
PALETTE=[[.68,.51,.38],[.29,.58,.73],[.69,.43,.27],[.69,.72,.59],[.79,.67,.49],[.46,.72,.79],[.59,.64,.79],[.72,.61,.82]]
RADIUS=[1.00,1.24,1.12,1.54,2.16,1.92,1.62,2.36]
MATERIALS=[0,1,0,0,4,2,3,4]
LAYER_FILES={'background':'background.jpg','subject':'subject.webp','spirit':'spirit.webp',
             'effects':'effects.webp','text':'text.webp','lineart':'lineart.png'}
DEPTHS={'background':-.25,'subject':.4,'effects':.5,'text':0}

def orbit(i: int, j: int) -> dict:
    """The exact v10 satellite formula, frozen into layout data."""
    return {'radius':RADIUS[j%8],'orbitRadius':round(11.8+j*4.3+(1.1 if j>3 else 0),6),
            'eccentricity':round(.06+(j%3)*.035,6),'inclination':round(.12+(i%3)*.12+(j%3-1)*.065,6),
            'nodeAngle':round(i*.71+j*.12,6),'phase':round(-1.35+j*2.399963+i*.6,6),
            'material':MATERIALS[j%8],'color':PALETTE[(j+i*2)%8]}

def showcase_profile(src: Path=SHOWCASE) -> dict:
    p=copy.deepcopy(load(src/'profile.json'));card=load(src/'persona-card.json')
    check(len(p['chapters'])==len(NODES),'展示示例需要 5 颗主星')
    stars=[];topics=[]
    for i,c in enumerate(p['chapters']):
        stars.append({'id':c['id'],'position':NODES[i],'color':COLORS[i],'material':i})
        for j,t in enumerate(c['topics']):
            t['id']=f"{c['id']}-{j+1}"
            topics.append({'id':t['id'],'parent_id':c['id'],**orbit(i,j)})
    p.update(version='1.0',mode='showcase',owner_id='private-showcase',layout={'version':'1.0','stars':stars,'topics':topics})
    p['persona']={**card,'content_ready':True,'art_status':'approved','persona_digest':digest(card)}
    p['release']={'draft':True,'share_allowed':False}
    p['content_digest']=digest({'chapters':p['chapters'],'persona':p['persona']})
    return p

def build_showcase(out: Path, src: Path=SHOWCASE) -> dict:
    check((src/'profile.json').is_file(),'本机没有旧版私人展示资料；它不随源码或演示包分发。请使用 demo 运行虚构示例。')
    profile=showcase_profile(src)
    layers={k:uri(src/'card'/f) for k,f in LAYER_FILES.items()}
    html=write_site(out,profile,layers,uri(src/'card/flat.jpg'),DEPTHS)
    save(out/'profile.json',profile)
    report={'ok':True,'version':VERSION,'mode':'showcase','stars':len(profile['chapters']),'planets':len(profile['layout']['topics']),
            'art_status':'approved','share_allowed':True,'html_sha256':hashlib.sha256(html.encode()).hexdigest(),
            'html_bytes':len(html.encode()),'out':str(out/'index.html')}
    save(out/'build-report.json',report)
    return report
