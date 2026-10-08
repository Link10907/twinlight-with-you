#!/usr/bin/env python3
"""Probe an actual local Chromium WebGL context/shader. Not a foil/merger approval."""
from __future__ import annotations
import argparse,json,os
from pathlib import Path
from twinlight_core.provider_runtime import save_new
from twinlight_core.browser_runtime import launch_flags

PROBE = '''()=>{const c=document.createElement('canvas');c.width=c.height=8;const g=c.getContext('webgl',{preserveDrawingBuffer:true});
if(!g)return {webgl:false,reason:'context_unavailable',shader_verified:false};
const p=g.createProgram();const src=[['VERTEX_SHADER','attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}'],['FRAGMENT_SHADER','precision mediump float;void main(){gl_FragColor=vec4(1.,0.,0.,1.);}']];
for(const [t,s] of src){const h=g.createShader(g[t]);g.shaderSource(h,s);g.compileShader(h);if(!g.getShaderParameter(h,g.COMPILE_STATUS))return {webgl:false,reason:'shader_compile',shader_verified:false};g.attachShader(p,h);}
g.linkProgram(p);if(!g.getProgramParameter(p,g.LINK_STATUS))return {webgl:false,reason:'shader_link',shader_verified:false};g.useProgram(p);
const b=g.createBuffer();g.bindBuffer(g.ARRAY_BUFFER,b);g.bufferData(g.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),g.STATIC_DRAW);
const a=g.getAttribLocation(p,'p');g.enableVertexAttribArray(a);g.vertexAttribPointer(a,2,g.FLOAT,false,0,0);g.viewport(0,0,8,8);g.drawArrays(g.TRIANGLES,0,3);
const pixel=new Uint8Array(4);g.readPixels(4,4,1,1,g.RGBA,g.UNSIGNED_BYTE,pixel);const ok=pixel[0]>240&&pixel[1]<10&&g.getError()===g.NO_ERROR;
const d=g.getExtension('WEBGL_debug_renderer_info');return {webgl:ok,shader_verified:ok,pixel:Array.from(pixel),reason:ok?'draw_verified':'draw_failed',
version:g.getParameter(g.VERSION),renderer:d?g.getParameter(d.UNMASKED_RENDERER_WEBGL):g.getParameter(g.RENDERER)};}'''


def probe(*,browser=None,channel=None,headed=False,gpu_mode='auto'):
    from playwright.sync_api import sync_playwright
    result={'version':'browser-probe-1','browser_started':False,'webgl':False,'shader_verified':False,
            'requested':{'browser':browser,'channel':channel,'headed':headed,'gpu_mode':gpu_mode},
            'foil_verified':False,'merge_verified':False,'release_authorized':False}
    if browser and channel:raise ValueError('Choose --browser or --channel, not both.')
    try:
        with sync_playwright() as p:
            b=p.chromium.launch(executable_path=browser,channel=channel,headless=not headed,args=launch_flags(gpu_mode),timeout=20000)
            result.update(browser_started=True,browser_version=b.version)
            page=b.new_page(viewport={'width':800,'height':600},reduced_motion='no-preference')
            page.set_content('<!doctype html><title>Twinlight WebGL probe</title>')
            result.update(page.evaluate(PROBE));b.close()
    except Exception as exc:result['error']=type(exc).__name__+': '+str(exc)[:1000]
    result['ok']=result['browser_started'] and result['webgl']
    return result


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',type=Path,required=True);a.add_argument('--browser');a.add_argument('--channel');a.add_argument('--headed',action='store_true');a.add_argument('--gpu-mode',choices=('auto','swiftshader'),default='auto')
    args=a.parse_args();r=probe(browser=args.browser,channel=args.channel,headed=args.headed,gpu_mode=args.gpu_mode)
    save_new(args.out,r);print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['ok'] else 2
if __name__=='__main__':raise SystemExit(main())
