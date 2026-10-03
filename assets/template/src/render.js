// V4: one inexpensive dust pass, batched sharp stars, then bounded photospheres.
// No full-screen multi-octave solar shading. No per-frame texture regeneration.
const VERTEX=`attribute vec2 a_pos;varying vec2 v_uv;void main(){v_uv=a_pos*.5+.5;gl_Position=vec4(a_pos,0.,1.);}`;
const FRAGMENT=`precision highp float;
varying vec2 v_uv;uniform sampler2D u_texture;uniform vec3 u_cam,u_right,u_up,u_forward;uniform float u_tan,u_aspect,u_active,u_merge;uniform vec3 u_origin0,u_origin1;uniform mat3 u_matrix0,u_matrix1;uniform float u_scale1,u_aiVisible,u_personVisible,u_flow;
vec3 localV(vec3 p,mat3 m){return vec3(dot(p,m[0]),dot(p,m[1]),dot(p,m[2]));}
vec3 galaxy(vec3 ro,vec3 rd,vec3 origin,mat3 m,float sz,vec3 tint,float flow){vec3 lro=localV(ro-origin,m)/sz,lrd=localV(rd,m)/sz;float t=-lro.y/lrd.y;if(t<0.||abs(lrd.y)<.00001)return vec3(0.);vec2 p=(lro+lrd*t).xz;float rr=length(p),a=atan(p.y,p.x),merger=smoothstep(.08,.93,u_merge),outward=smoothstep(15.,140.,rr);a-=merger*outward*.38;if(sz>.99)a-=.026*sin(flow*.27+rr*.035);vec2 uv=vec2(cos(a),sin(a))*rr/310.+.5;if(any(lessThan(uv,vec2(0.)))||any(greaterThan(uv,vec2(1.))))return vec3(0.);vec3 g=texture2D(u_texture,uv).rgb;return g*tint*mix(1.72,1.08,u_active)*(1.-smoothstep(.32,.95,u_merge)*.62);}
void main(){vec2 s=v_uv*2.-1.;vec3 rd=normalize(u_forward+u_right*s.x*u_aspect*u_tan+u_up*s.y*u_tan);vec3 col=vec3(.010,.014,.024);col+=u_personVisible*galaxy(u_cam,rd,u_origin0,u_matrix0,1.,vec3(1.06,.91,.78),u_flow);col+=u_aiVisible*galaxy(u_cam,rd,u_origin1,u_matrix1,u_scale1,vec3(.63,.80,1.16),0.);gl_FragColor=vec4(col,1.);}`;
const POINT_VERTEX=`precision highp float;
attribute vec3 a_pos,a_color;attribute float a_size;
uniform vec3 u_cam,u_right,u_up,u_forward;uniform float u_tan,u_aspect,u_height,u_pixel,u_gain,u_scale,u_merge,u_galaxy,u_time,u_stream,u_flow;
uniform mat3 u_matrix;uniform vec3 u_origin,u_other;
varying vec3 v_color;varying float v_vis,v_size;
float ease(float x){return x*x*x*(x*(x*6.-15.)+10.);}
void main(){vec3 p=a_pos;float opacity=1.;
 if(u_stream>.5){float t=fract(a_pos.x+u_time*.007*(a_pos.y<3.5?1.:-1.));float lane=a_pos.y;vec3 axis=normalize(u_other-u_origin),side=normalize(cross(axis,vec3(0.,1.,0.)));float h=sin(t*3.14159265);p=mix(u_origin,u_other,t);float ang=t*6.2831853+lane*.89;float breadth=(12.+lane*3.)*h;
 p+=side*(sin(ang)*breadth)+vec3(0.,cos(ang)*breadth*.45+11.*h,0.);p+=side*((a_pos.z-.5)*10.*h);p.y+=(a_pos.z-.5)*6.;opacity=smoothstep(.12,.50,u_merge)*(.4+.6*h)*(1.-smoothstep(.78,1.,u_merge)*.25);
 }else{if(u_galaxy>=0.){float m=ease(clamp((u_merge-.08)/.85,0.,1.)),rad=length(p.xz),outer=smoothstep(15.,140.,rad),ang=atan(p.z,p.x);float a=ang+(u_galaxy>.5?-.58:.68)*m*outer;float rr=rad*(1.+.17*m*outer*cos(ang*2.+.6+u_galaxy));p=vec3(cos(a)*rr,p.y+m*outer*7.*sin(a*2.+u_galaxy),sin(a)*rr);}if(u_galaxy>-.5&&u_galaxy<.5){float a=.026*sin(u_flow*.27+length(p.xz)*.035),c=cos(a),s=sin(a);p.xz=vec2(p.x*c-p.z*s,p.x*s+p.z*c);}p=u_matrix*p*u_scale+u_origin;}
 vec3 d=p-u_cam;float z=dot(d,u_forward);gl_Position=vec4(dot(d,u_right)/(u_tan*u_aspect),dot(d,u_up)/u_tan,z*1.0001-.20001,z);
 float apparent=a_size*u_height/(max(z,.2)*u_tan*2.);gl_PointSize=clamp(apparent,.85*u_pixel,3.7*u_pixel);v_size=gl_PointSize;float pulse=.91+.09*sin(u_time*(.63+fract(a_pos.x*.01)*.38)+a_pos.x*.11+a_pos.z*.075);v_color=a_color*u_gain*opacity*pulse;v_vis=smoothstep(.3,3.,z);
}`;
const POINT_FRAGMENT=`precision mediump float;varying vec3 v_color;varying float v_vis,v_size;
void main(){vec2 p=gl_PointCoord*2.-1.;float r=length(p);if(r>1.)discard;
 float core=1.-smoothstep(.16,.82,r);float halo=exp(-r*r*7.)*.10;
 gl_FragColor=vec4(v_color*(core+halo)*v_vis,1.);}`;
const STAR_VERTEX=`attribute vec2 a_pos;uniform vec4 u_rect;varying vec2 v_uv;
void main(){vec2 p=mix(u_rect.xy,u_rect.zw,a_pos*.5+.5);v_uv=p*.5+.5;gl_Position=vec4(p,0.,1.);}`;
const STAR_FRAGMENT=`precision highp float;
varying vec2 v_uv;uniform sampler2D u_surface;
uniform vec3 u_cam,u_right,u_up,u_forward,u_center,u_color,u_light;uniform float u_tan,u_aspect,u_radius,u_time,u_kind,u_opacity,u_glow;
const float PI=3.14159265359;
void main(){vec2 s=v_uv*2.-1.;vec3 rd=normalize(u_forward+u_right*s.x*u_aspect*u_tan+u_up*s.y*u_tan);
 vec3 to=u_center-u_cam;float d=length(to);float b=dot(rd,to);if(b<=0.)discard;
 float ang=length(cross(rd,to))/u_radius;
 vec2 off=vec2(dot(rd-to/d,u_right),dot(rd-to/d,u_up))*d/u_radius;
 float theta=atan(off.y,off.x),front=0.;vec3 col;float alpha;
 float det=b*b-dot(to,to)+u_radius*u_radius;
 // V8 planets: opaque, sun-lit bodies, not emissive points or UI rings.
 if(u_kind>4.5){
  float sphereT=det>=0.?b-sqrt(max(det,0.)):1.e10;
  vec3 lit=normalize(u_light-u_center);vec3 pc=vec3(0.);float pa=0.;
  if(det>=0.){
   vec3 n=normalize(u_cam+rd*sphereT-u_center);float rot=u_time*.04+u_kind*1.2;
   vec3 q=vec3(n.x*cos(rot)+n.z*sin(rot),n.y,-n.x*sin(rot)+n.z*cos(rot));
   vec2 uv=vec2(atan(q.z,q.x)/(2.*PI)+.5,asin(clamp(q.y,-1.,1.))/PI+.5);
   vec3 tx=texture2D(u_surface,uv+vec2(u_kind*.139,0.)).rgb;
   float noise=tx.r*.5+tx.g*.3+tx.b*.2;
   vec3 base=u_color*(.65+noise*.60);
   if(u_kind>5.5&&u_kind<6.5){float land=smoothstep(.46,.58,noise);base=mix(u_color*.68,vec3(.35,.51,.36),land);base=mix(base,vec3(.75,.85,.87),smoothstep(.58,.71,tx.r)*.55);}
   if((u_kind>6.5&&u_kind<7.5)||u_kind>8.5){float band=.5+.5*sin(uv.y*87.+noise*7.+sin(uv.x*12.)*2.);base=mix(u_color*.49,u_color*1.25,band*.65+noise*.32);}
   if(u_kind>7.5&&u_kind<8.5)base=mix(u_color*.5,u_color*1.15,smoothstep(.28,.68,noise));
   float diffuse=max(0.,dot(n,lit)),facing=max(0.,dot(n,-rd));
   pc=base*(.13+.87*pow(diffuse,.8));
   float highlight=pow(max(0.,dot(n,normalize(lit-rd))),42.);
   pc+=vec3(.7,.85,.94)*highlight*(u_kind<6.5?.11:.025);
   pc+=u_color*pow(1.-facing,3.)*(.06+.16*max(0.,dot(n,lit)));
   pc*=1.+u_glow*.32;pa=1.;
  }else{
   float edge=max(ang-1.,0.);float atmosphere=exp(-edge*13.)*.16;
   pc=u_color;pa=atmosphere;
  }
  // A physical ring belongs only to gas giants, never a hover affordance.
  if(u_kind>8.5){vec3 rn=normalize(vec3(.20,.87,.30));float denom=dot(rd,rn);
   if(abs(denom)>.0001){float rt=dot(to,rn)/denom;vec3 hit=u_cam+rd*rt-u_center;float r=length(hit)/u_radius;
    if(rt>0.&&rt<sphereT&&r>1.36&&r<2.28){float lines=.64+.36*sin(r*180.);float gap=1.-smoothstep(.0,.045,abs(r-1.91));float ra=(.42+.30*lines)*(1.-gap*.8)*(1.-smoothstep(2.14,2.28,r))*smoothstep(1.36,1.45,r);
     vec3 rc=mix(u_color,vec3(.91,.82,.67),.5)*(.45+.35*abs(dot(rn,lit)));pc=mix(pc,rc,ra);pa=max(pa,ra);
    }
   }
  }
  if(pa<.002)discard;gl_FragColor=vec4(pc,pa*u_opacity);return;
 }
 if(det>=0.){
  float t=b-sqrt(det);vec3 n=normalize(u_cam+rd*t-u_center);
  float rot=u_time*(.061+u_kind*.009);float cs=cos(rot),sn=sin(rot);
  vec3 q=vec3(n.x*cs+n.z*sn,n.y,-n.x*sn+n.z*cs);
  vec2 uv=vec2(atan(q.z,q.x)/(2.*PI)+.5,asin(clamp(q.y,-1.,1.))/PI+.5);
  vec3 tex=texture2D(u_surface,uv+vec2(u_kind*.117+sin(uv.y*9.+u_time*.07)*.003,0.)).rgb;
  float gran=tex.r,field=tex.g,conv=tex.b;
  float facing=max(0.,dot(n,-rd));float limb=.45+.55*pow(facing,.53);
  float heat=clamp(.34+gran*.43+conv*.22+field*.08,0.,1.);
  vec3 cool=vec3(.68,.32,.055),warm=vec3(1.,.69,.23),hot=vec3(1.,.97,.80);
  if(u_kind>.5&&u_kind<1.5){cool=vec3(.12,.32,.64);warm=vec3(.42,.71,1.);hot=vec3(.93,.99,1.);heat=.34+gran*.46+field*.19;}
  if(u_kind>1.5&&u_kind<2.5){cool=vec3(.52,.11,.02);warm=vec3(1.,.42,.065);hot=vec3(1.,.89,.47);heat=.30+gran*.28+conv*.40;}
  if(u_kind>2.5&&u_kind<3.5){cool=vec3(.06,.34,.45);warm=vec3(.39,.82,.89);hot=vec3(.92,1.,1.);heat=.34+field*.39+gran*.26;}
  if(u_kind>3.5){cool=vec3(.20,.10,.46);warm=vec3(.51,.43,.95);hot=vec3(.87,.94,1.);heat=.34+gran*.27+field*.33;}
  col=mix(cool,warm,smoothstep(.1,.62,heat));col=mix(col,hot,smoothstep(.56,.97,heat));
  col*=limb*(.91+gran*.20);col+=u_color*pow(1.-facing,7.)*.12;
  alpha=1.;
 }else{
  float flare=pow(.5+.5*sin(theta*19.+sin(theta*7.+u_time*.12)*2.4),5.);
  float fine=pow(.5+.5*sin(theta*47.+u_time*.2),7.);
  float edge=max(ang-1.,0.);
  float crown=exp(-edge*9.)*(.33+flare*.27)+exp(-edge*3.5)*(.035+flare*.055+fine*.022);
  if(u_kind>2.5&&u_kind<3.5){float ray=pow(abs(sin(theta+.26)),48.);crown+=ray*exp(-edge*.78)*.16;}
  col=u_color*(.74+flare*.22);alpha=min(.70,crown);
  if(alpha<.002)discard;
 }
 gl_FragColor=vec4(col*(1.+u_glow*.22),alpha*u_opacity);}`;
const RING_VERTEX=`precision highp float;attribute vec3 a_pos;attribute vec3 a_color;attribute float a_size;
uniform vec3 u_cam,u_right,u_up,u_forward,u_center;uniform float u_tan,u_aspect,u_height,u_time,u_pixel,u_fade;
varying vec3 v_color;varying float v_vis,v_size;
void main(){float c=cos(u_time*.024),s=sin(u_time*.024);vec3 p=vec3(a_pos.x*c+a_pos.z*s,a_pos.y,-a_pos.x*s+a_pos.z*c)+u_center;
 vec3 d=p-u_cam;float z=dot(d,u_forward);gl_Position=vec4(dot(d,u_right)/(u_tan*u_aspect),dot(d,u_up)/u_tan,z*1.0001-.20001,z);
 gl_PointSize=clamp(a_size*u_height/(max(z,.2)*u_tan*2.),.85*u_pixel,2.1*u_pixel);v_size=gl_PointSize;v_color=a_color*u_fade;v_vis=smoothstep(.3,3.,z);}`;
const DISK_FRAGMENT=`precision highp float;
varying vec2 v_uv;uniform vec3 u_cam,u_right,u_up,u_forward,u_center;uniform float u_tan,u_aspect,u_time,u_fade;uniform sampler2D u_surface;
void main(){vec2 s=v_uv*2.-1.;vec3 rd=normalize(u_forward+u_right*s.x*u_aspect*u_tan+u_up*s.y*u_tan);vec3 normal=normalize(vec3(0.,1.,-.17));float den=dot(rd,normal);if(abs(den)<.0001)discard;
 float t=dot(u_center-u_cam,normal)/den;if(t<0.)discard;vec3 hit=u_cam+rd*t-u_center;float r=length(hit.xz);if(r<7.1||r>14.)discard;
 float a=atan(hit.z,hit.x);float grain=texture2D(u_surface,vec2(a/6.2831853+.5+u_time*.004,r*.071)).r;
 float filaments=.54+.20*sin(r*13.8+a*.15)+.13*sin(r*37.2)+.08*sin(r*72.);
 float edge=smoothstep(7.1,7.45,r)*(1.-smoothstep(13.4,14.,r));
 vec3 col=mix(vec3(.75,.52,.32),vec3(.42,.42,.77),smoothstep(7.,12.,r));
 gl_FragColor=vec4(col*(.55+grain*.8),edge*filaments*.28*u_fade);}`;
let diskProgram,diskLoc;
let starProgram,starLoc={},ringProgram,ringLoc={},ringBuffer,ringCount=0,discTexture,surfaceTexture;
let streamBuffer,streamCount=0;
let galaxyStart=0,galaxyCount=0,aiStart=0,aiCount=0,backCount=0,autoLevel=0,pixelScale=1;
const radii=nodes.map((_,i)=>[5.8,4.5,6.2,4.8,5.15][DEFAULT_PROFILE.layout.stars[i].material]);
const starTypes=nodes.map(()=> '恒星 · 艺术化表面');
const planetCaption=nodes.map(()=> 'STELLAR LIGHT');
function compile(type,source){const s=gl.createShader(type);gl.shaderSource(s,source);gl.compileShader(s);if(!gl.getShaderParameter(s,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(s));return s;}
function makeProgram(v,f){const p=gl.createProgram(),vs=compile(gl.VERTEX_SHADER,v),fs=compile(gl.FRAGMENT_SHADER,f);gl.attachShader(p,vs);gl.attachShader(p,fs);gl.bindAttribLocation(p,0,'a_pos');gl.linkProgram(p);gl.deleteShader(vs);gl.deleteShader(fs);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(p));return p;}
function locs(p,names){const o={};for(const n of names)o[n]=gl.getUniformLocation(p,n);return o;}
function loadTexture(src,unit){return new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>{const tex=gl.createTexture();gl.activeTexture(gl.TEXTURE0+unit);gl.bindTexture(gl.TEXTURE_2D,tex);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image);gl.generateMipmap(gl.TEXTURE_2D);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,unit===1?gl.REPEAT:gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,unit===1?gl.REPEAT:gl.CLAMP_TO_EDGE);resolve(tex);};image.onerror=()=>reject(Error('Embedded texture could not load'));image.src=src;});}
async function initWebGL(){
 gl=canvas.getContext('webgl',{alpha:false,antialias:false,depth:false,powerPreference:'high-performance',preserveDrawingBuffer:false});if(!gl)throw Error('WebGL unavailable');
 program=makeProgram(VERTEX,FRAGMENT);pointsProgram=makeProgram(POINT_VERTEX,POINT_FRAGMENT);starProgram=makeProgram(STAR_VERTEX,STAR_FRAGMENT);ringProgram=makeProgram(RING_VERTEX,POINT_FRAGMENT);diskProgram=makeProgram(STAR_VERTEX,DISK_FRAGMENT);
 const names=['u_cam','u_right','u_up','u_forward','u_tan','u_aspect'];
 locations=locs(program,[...names,'u_texture','u_active','u_origin0','u_origin1','u_matrix0','u_matrix1','u_scale1','u_merge','u_aiVisible','u_personVisible','u_flow']);pointLoc=locs(pointsProgram,[...names,'u_height','u_pixel','u_gain','u_scale','u_origin','u_matrix','u_merge','u_galaxy','u_time','u_stream','u_other','u_flow']);
 diskLoc=locs(diskProgram,[...names,'u_rect','u_center','u_time','u_surface','u_fade']);
 starLoc=locs(starProgram,[...names,'u_rect','u_surface','u_center','u_color','u_radius','u_time','u_kind','u_opacity','u_glow','u_light']);
 ringLoc=locs(ringProgram,[...names,'u_center','u_time','u_height','u_pixel','u_fade']);
 quad=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,quad);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]),gl.STATIC_DRAW);
 for(const p of [program,pointsProgram,starProgram,ringProgram,diskProgram])p.pos=gl.getAttribLocation(p,'a_pos');
 for(const p of [pointsProgram,ringProgram]){p.color=gl.getAttribLocation(p,'a_color');p.size=gl.getAttribLocation(p,'a_size');}
 const verts=[],r=seedRandom(24680),normal=()=>Math.sqrt(-2*Math.log(Math.max(1e-6,r())))*Math.cos(TAU*r());
 const put=(x,y,z,b,c,size)=>verts.push(x,y,z,b*c[0],b*c[1],b*c[2],size);
 for(let i=0;i<9000;i++){const a=r()*TAU,z=r()*2-1,s=Math.sqrt(1-z*z),d=850+r()*1500,b=.06+Math.pow(r(),5)*.72;put(s*Math.cos(a)*d,z*d,s*Math.sin(a)*d,b,r()<.2?[1,.77,.58]:[.79,.87,1],.50+r()*1.42);}
 for(let i=0;i<3800;i++)put((r()-.5)*970,15+r()*210,(r()-.5)*830,.07+Math.pow(r(),3)*.56,[.86,.93,1],.09+r()*.13);
 backCount=verts.length/7;galaxyStart=backCount;
 function addGalaxy(count,blue){for(let i=0;i<count;i++){let rad,a,h;if(r()<.21){rad=Math.pow(r(),1.4)*34;a=r()*TAU;h=normal()*(4.4*Math.exp(-rad/19)+.7);}else{rad=Math.pow(r(),.69)*147;a=(r()<.5?0:Math.PI)+2.30*Math.log(rad/155+.06)+normal()*(r()<.73?(.20+rad*.0013):.76);if(r()<.22)a+=Math.PI*.5;a+=.10*Math.sin(rad*.12);h=normal()*(.48+rad*.006);}
 const w=Math.exp(-rad/34),b=.12+Math.pow(r(),3)*.93;let c=blue?[.56+w*.30,.72+w*.17,1]:[.76+w*.24,.82-w*.12,.96-w*.52];if(r()<.08)c=blue?[.78,.55,1]:[1,.68,.39];put(Math.cos(a)*rad,h,Math.sin(a)*rad,b,c,.135+r()*.21);}}
 addGalaxy(98500,false);
 galaxyCount=verts.length/7-galaxyStart;aiStart=verts.length/7;addGalaxy(82500,true);aiCount=verts.length/7-aiStart;
 pointCount=verts.length/7;pointBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,pointBuffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(verts),gl.STATIC_DRAW);
 const ring=[];
 for(let i=0;i<6500;i++){const angle=r()*TAU,rr=7.5+Math.pow(r(),.9)*6.9,yy=normal()*.22;
  const bands=.35+.65*Math.pow(.5+.5*Math.sin(rr*8.5),2),b=(.15+r()*.42)*bands;
  ring.push(Math.cos(angle)*rr,Math.sin(angle)*rr*.17+yy,Math.sin(angle)*rr,b*.80,b*.77,b,.15+r()*.08);
 }
 ringCount=ring.length/7;ringBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,ringBuffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(ring),gl.STATIC_DRAW);
 const streams=[];for(let i=0;i<7200;i++){const t=r(),k=i%8,c=i%2?[.48,.72,1]:[1,.75,.43],b=.12+r()*.48;streams.push(t,k,r(),c[0]*b,c[1]*b,c[2]*b,.13+r()*.13);}streamCount=streams.length/7;streamBuffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,streamBuffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(streams),gl.STATIC_DRAW);
 [discTexture,surfaceTexture]=await Promise.all([loadTexture(TEX,0),loadTexture(SURFACE,1)]);
}
function basis(){F=norm(sub(state.target,state.cam));R=norm(cross(F,[0,1,0]));U=norm(cross(R,F));const c=Math.cos(state.bank),s=Math.sin(state.bank),rr=R;R=add(mul(rr,c),mul(U,s));U=add(mul(U,c),mul(rr,-s));}
function project(p){const d=sub(p,state.cam),z=dot(d,F),tan=Math.tan(state.fov*Math.PI/360);if(z<.5)return null;return {x:(dot(d,R)/(z*tan*state.w/state.h)*.5+.5)*state.w,y:(.5-dot(d,U)/(z*tan)*.5)*state.h,z};}
function setCameraUniforms(l){gl.uniform3fv(l.u_cam,state.cam);gl.uniform3fv(l.u_right,R);gl.uniform3fv(l.u_up,U);gl.uniform3fv(l.u_forward,F);gl.uniform1f(l.u_tan,Math.tan(state.fov*Math.PI/360));gl.uniform1f(l.u_aspect,state.w/state.h);}
function useQuad(p){gl.useProgram(p);gl.bindBuffer(gl.ARRAY_BUFFER,quad);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,2,gl.FLOAT,false,0,0);}
function usePoints(p,buf){gl.useProgram(p);gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.enableVertexAttribArray(0);gl.vertexAttribPointer(0,3,gl.FLOAT,false,28,0);gl.enableVertexAttribArray(p.color);gl.vertexAttribPointer(p.color,3,gl.FLOAT,false,28,12);gl.enableVertexAttribArray(p.size);gl.vertexAttribPointer(p.size,1,gl.FLOAT,false,28,24);}
function stopPoints(p){gl.disableVertexAttribArray(p.color);gl.disableVertexAttribArray(p.size);}
const renderObjects=[];
// Detail is distance-driven; surface geometry is never shown as giant planets in the map.
function starDetail(i){
 if(!state.flight&&state.active>=0&&state.active!==i)return 0;
 if(state.flight&&state.flight.index!==i&&state.from!==i)return 0;
 const d=smoother(clamp((177-len(sub(nodes[i],state.cam)))/98));
 return state.flight&&state.from===i?d*(1-smoother(clamp((state.flight.t-.68)/.32))):d;
}
const glintSprites=colors.map(c=>{const cv=document.createElement('canvas');cv.width=cv.height=128;const cc=cv.getContext('2d');const rgb=c.map(x=>Math.round(90+x*165)).join(',');const g=cc.createRadialGradient(64,64,0,64,64,63);g.addColorStop(0,'rgba(255,253,241,1)');g.addColorStop(.045,'rgba(255,251,227,.95)');g.addColorStop(.14,'rgba('+rgb+',.38)');g.addColorStop(.40,'rgba('+rgb+',.075)');g.addColorStop(1,'rgba('+rgb+',0)');cc.fillStyle=g;cc.fillRect(0,0,128,128);return cv;});
const hoverGlow=nodes.map(()=>0);
const mapClusters=nodes.map((n,i)=>{const rr=seedRandom(512+i);const points=[n];for(let j=0;j<11;j++){const a=rr()*TAU,rad=4+rr()*14;points.push(add(n,[Math.cos(a)*rad,rr()*3-4,Math.sin(a)*rad]));}const edges=[];for(let j=1;j<points.length;j++){const ds=points.map((p,k)=>({k,d:len(sub(p,points[j]))})).filter(a=>a.k!==j).sort((a,b)=>a.d-b.d);for(const q of ds.slice(0,2))if(q.k<j)edges.push([j,q.k]);}return {points,edges};});
function renderGL(){if(!state.gl)return;
 gl.viewport(0,0,canvas.width,canvas.height);gl.disable(gl.DEPTH_TEST);gl.disable(gl.BLEND);
 useQuad(program);setCameraUniforms(locations);gl.activeTexture(gl.TEXTURE0);gl.bindTexture(gl.TEXTURE_2D,discTexture);gl.uniform1i(locations.u_texture,0);
 const active=state.flight?mix(state.from<0?0:1,state.flight.index<0?0:1,smoother(state.flight.t)):(state.active<0?0:1);
 gl.uniform1f(locations.u_aiVisible,quietAIVisible()?1:0);gl.uniform1f(locations.u_personVisible,quietPersonVisible()?1:0);gl.uniform1f(locations.u_flow,v9.flow);gl.uniform1f(locations.u_merge,state.merge);gl.uniform1f(locations.u_active,active);gl.uniform3fv(locations.u_origin0,galaxyFrames[0].origin);gl.uniform3fv(locations.u_origin1,galaxyFrames[1].origin);gl.uniformMatrix3fv(locations.u_matrix0,false,galaxyFrames[0].matrix);gl.uniformMatrix3fv(locations.u_matrix1,false,galaxyFrames[1].matrix);gl.uniform1f(locations.u_scale1,galaxyFrames[1].scale);gl.drawArrays(gl.TRIANGLES,0,6);
 usePoints(pointsProgram,pointBuffer);setCameraUniforms(pointLoc);gl.uniform1f(pointLoc.u_height,canvas.height);gl.uniform1f(pointLoc.u_pixel,pixelScale);gl.uniform1f(pointLoc.u_gain,1.0);gl.uniform1f(pointLoc.u_merge,state.merge);gl.uniform1f(pointLoc.u_time,state.time);gl.uniform1f(pointLoc.u_flow,v9.flow);gl.uniform1f(pointLoc.u_stream,0);gl.uniform1f(pointLoc.u_galaxy,-1);
 gl.enable(gl.BLEND);gl.blendFunc(gl.ONE,gl.ONE);gl.uniformMatrix3fv(pointLoc.u_matrix,false,[1,0,0,0,1,0,0,0,1]);gl.uniform3fv(pointLoc.u_origin,[0,0,0]);gl.uniform1f(pointLoc.u_scale,1);gl.drawArrays(gl.POINTS,0,backCount);
 let fraction=state.quality==='balanced'?.48:state.quality==='high'?1:autoLevel>0?.64:.86;
 gl.uniform1f(pointLoc.u_gain,(1.0-active*.16)/Math.sqrt(fraction));for(let g=0;g<2;g++){if(g===1&&!quietAIVisible()||g===0&&!quietPersonVisible())continue;gl.uniform1f(pointLoc.u_galaxy,g);const f=galaxyFrames[g];gl.uniformMatrix3fv(pointLoc.u_matrix,false,f.matrix);gl.uniform3fv(pointLoc.u_origin,f.origin);gl.uniform1f(pointLoc.u_scale,f.scale);gl.drawArrays(gl.POINTS,g===0?galaxyStart:aiStart,Math.floor((g===0?galaxyCount:aiCount)*fraction));}stopPoints(pointsProgram);
 if(state.merge>.08){usePoints(pointsProgram,streamBuffer);gl.uniform1f(pointLoc.u_stream,1);gl.uniform3fv(pointLoc.u_origin,galaxyFrames[0].origin);gl.uniform3fv(pointLoc.u_other,galaxyFrames[1].origin);gl.uniform1f(pointLoc.u_gain,.91);gl.drawArrays(gl.POINTS,0,state.quality==='balanced'?3600:streamCount);stopPoints(pointsProgram);gl.uniform1f(pointLoc.u_stream,0);}
 // Sort only six objects, not every particle. Discs are opaque; corona is alpha.
 renderObjects.length=0;
 for(let i=0;i<nodes.length;i++){const detail=starDetail(i),appearance=v9BodyBlend(i);if(appearance>.001)renderObjects.push({p:nodes[i],r:mix(2.5,radii[i],detail),kind:profile.layout.stars[i].material,c:colors[i],opacity:appearance});}
 if(quietPersonVisible()&&!state.encounterCinematic&&!v8.cardOpen){
  for(const s of personalSatellites){const appearance=v9BodyBlend(s.i);if(appearance<.001)continue;
   const hot=state.hoverTopicIndex===s.k||quiet.selection===s.i&&quiet.topic===s.j||state.active===s.i&&state.topicHover===s.j;
   renderObjects.push({p:worldPoint(s.p),r:s.radius,kind:5+s.material,c:s.color,opacity:appearance,light:nodes[s.i],glow:hot?1:0});
  }
 }
 // The nearby AI companion is a distinct, rotating sphere. It never infers a model ID.
 // V8: AI remains a separate galaxy, not a hidden extra planet.
 const eventId=state.flight?state.flight.event:state.aiEvent;
 if(eventId>=0&&aiNodes[eventId]){const p=aiNodes[eventId],d=smoother(clamp((172-len(sub(p,state.cam)))/106)),pr=profile.ai_history[eventId].provider;renderObjects.push({p,r:4.2*mix(.1,1,d),kind:({OpenAI:3,Anthropic:0,Google:1,DeepSeek:1,Qwen:4})[pr]??1,c:providerColors[pr],opacity:d});}
 renderObjects.sort((a,b)=>dot(sub(b.p,state.cam),F)-dot(sub(a.p,state.cam),F));
 useQuad(starProgram);setCameraUniforms(starLoc);gl.activeTexture(gl.TEXTURE1);gl.bindTexture(gl.TEXTURE_2D,surfaceTexture);gl.uniform1i(starLoc.u_surface,1);gl.uniform1f(starLoc.u_time,state.time);
 gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
 const tan=Math.tan(state.fov*Math.PI/360);
 for(const o of renderObjects){const p=project(o.p);if(!p)continue;const radius=o.r*state.h/(2*p.z*tan);const k=o.kind===3?4.8:3.0;const s=radius*k;
 if(p.x+s<0||p.y+s<0||p.x-s>state.w||p.y-s>state.h)continue;
 gl.uniform4f(starLoc.u_rect,(p.x-s)/state.w*2-1,1-(p.y+s)/state.h*2,(p.x+s)/state.w*2-1,1-(p.y-s)/state.h*2);
 gl.uniform3fv(starLoc.u_center,o.p);gl.uniform3fv(starLoc.u_color,o.c);gl.uniform1f(starLoc.u_radius,o.r);gl.uniform1f(starLoc.u_kind,o.kind);gl.uniform3fv(starLoc.u_light,o.light||[0,90,80]);gl.uniform1f(starLoc.u_glow,o.glow||(nodes.indexOf(o.p)>=0&&(quiet.selection===nodes.indexOf(o.p)||state.hoveredStar===nodes.indexOf(o.p))?1:0));gl.uniform1f(starLoc.u_opacity,o.opacity);gl.drawArrays(gl.TRIANGLES,0,6);
 }
 gl.disable(gl.BLEND);
}
const routeLocal=[];for(let i=0;i<localNodes.length-1;i++)for(let j=0;j<=28;j++){const t=j/28,p=lerp(localNodes[i],localNodes[i+1],t);p[1]+=Math.sin(t*Math.PI)*9;routeLocal.push(p);}
const streaks=Array.from({length:48},()=>({a:rand()*TAU,r:rand(),p:rand(),l:.4+rand()}));
function strokeWorld(points,style,width=.6){ctx.strokeStyle=style;ctx.lineWidth=width;ctx.beginPath();let start=false;for(const point of points){const v=project(point);if(!v){start=false;continue;}if(start)ctx.lineTo(v.x,v.y);else{ctx.moveTo(v.x,v.y);start=true;}}ctx.stroke();}
function glint(p,colorIndex,size=30,alpha=1){const s=project(p);if(!s||s.x<-size||s.x>state.w+size||s.y<-size||s.y>state.h+size)return;ctx.globalAlpha=alpha;ctx.drawImage(glintSprites[colorIndex%glintSprites.length],s.x-size,s.y-size,size*2,size*2);ctx.globalAlpha=1;}
function drawOverlay(){ctx.clearRect(0,0,state.w,state.h);const isMap=['overview','personal','ai'].includes(state.mode)&&!state.flight&&!state.encounterCinematic;
 for(let i=0;i<nodes.length;i++){hoverGlow[i]=mix(hoverGlow[i],state.hoveredStar===i?1:0,1-Math.exp(-Math.max(state.delta,.016)*7));const detail=starDetail(i),a=1-smoother(clamp(detail*1.65));if(a>.01&&!state.encounterCinematic)glint(nodes[i],i,24+hoverGlow[i]*37,a);}
 if(isMap){strokeWorld(routeLocal.map(p=>worldPoint(p)),'rgba(226,195,143,.22)',.6);mapClusters.forEach((cl,i)=>{const hot=hoverGlow[i];for(const [a,b]of cl.edges)strokeWorld([worldPoint(cl.points[a]),worldPoint(cl.points[b])],'rgba(180,196,226,'+(.07+hot*.27)+')',.5);});
 // Each provider has its own star trail, ordered by documented release date.
 for(const provider of providerOrder){const selected=state.provider==='all'||state.provider===provider,items=profile.ai_history.map((e,i)=>({e,i})).filter(o=>o.e.provider===provider).sort((a,b)=>a.e.date.localeCompare(b.e.date));if(!selected)continue;const c=providerColors[provider].map(x=>Math.round(x*255)).join(',');strokeWorld(items.map(o=>aiNodes[o.i]),'rgba('+c+','+(state.mode==='ai'?.24:.105)+')',.6);}
 profile.ai_history.forEach((e,i)=>{if(state.provider!=='all'&&state.provider!==e.provider)return;const p=project(aiNodes[i]);if(!p)return;const hot=state.hoverAI===i;glint(aiNodes[i],providerOrder.indexOf(e.provider),hot?46:20,hot?1:.78);ctx.fillStyle='rgba('+providerColors[e.provider].map(v=>Math.round(v*255)).join(',')+','+(hot?1:.75)+')';ctx.beginPath();ctx.arc(p.x,p.y,hot?2.4:1.25,0,TAU);ctx.fill();});
 }
 if(state.mode==='chapter'&&state.active>=0&&!state.flight){const i=state.active,p=project(nodes[i]),cp=project(companionWorld()),fade=smoother(clamp(state.idle/1.1));if(p){const radius=radii[i]*state.h/(2*p.z*Math.tan(state.fov*Math.PI/360));ctx.save();ctx.translate(p.x,p.y);ctx.rotate(-.35+state.time*.007);ctx.strokeStyle='rgba(191,204,232,'+fade*.15+')';ctx.lineWidth=.6;for(let j=0;j<2;j++){ctx.beginPath();ctx.ellipse(0,0,radius*(1.7+j*.45),radius*(.65+j*.25),0,.2,5.9);ctx.stroke();}ctx.restore();
 const points=(profile.chapters[i].topics||[]).map((_,j)=>topicWorld(i,j));for(let j=0;j<points.length;j++){const q=project(points[j]);if(!q)continue;const hot=state.topic===j||state.topicHover===j,dx=q.x-p.x,dy=q.y-p.y,dl=Math.hypot(dx,dy)||1,edge=Math.min(radius*1.15,dl*.65);ctx.strokeStyle='rgba(175,198,227,'+fade*(hot?.5:.16)+')';ctx.lineWidth=hot?.85:.55;ctx.beginPath();ctx.moveTo(p.x+dx/dl*edge,p.y+dy/dl*edge);ctx.quadraticCurveTo((p.x+q.x)/2-dy*.06,(p.y+q.y)/2+dx*.06,q.x,q.y);ctx.stroke();glint(points[j],i,hot?30:16,fade*.8);}
 if(cp){ctx.setLineDash([2,7]);ctx.strokeStyle='rgba(135,193,245,'+(.30*fade)+')';ctx.beginPath();const dx=cp.x-p.x,dy=cp.y-p.y,dd=Math.hypot(dx,dy);ctx.moveTo(p.x+dx/dd*radius*1.3,p.y+dy/dd*radius*1.3);ctx.quadraticCurveTo((p.x+cp.x)/2,(p.y+cp.y)/2-24,cp.x,cp.y);ctx.stroke();ctx.setLineDash([]);}}
 }
 if(state.mode==='event'&&state.aiEvent>=0&&!state.flight){const p=project(aiNodes[state.aiEvent]);if(p){const rr=4.2*state.h/(2*p.z*Math.tan(state.fov*Math.PI/360));ctx.save();ctx.translate(p.x,p.y);ctx.rotate(-.6+state.time*.018);ctx.strokeStyle='rgba(144,195,246,.27)';ctx.lineWidth=.7;for(let i=0;i<3;i++){ctx.beginPath();ctx.ellipse(0,0,rr*(1.65+i*.30),rr*(.7+i*.15),i*.45,.4,5.95);ctx.stroke();}ctx.restore();}}
 const f=state.flight;if(!f||state.reduced)return;const env=16*f.t*f.t*(1-f.t)*(1-f.t),diag=Math.hypot(state.w,state.h),cx=state.w*.59,cy=state.h*.43;ctx.lineWidth=.6;
 for(const s of streaks){const t=(s.p+f.t*.86)%1,rr=(.09+t*t*.70)*diag,ll=(3+env*32*s.l)*t;ctx.strokeStyle='rgba(172,204,249,'+env*t*.20+')';ctx.beginPath();ctx.moveTo(cx+Math.cos(s.a)*rr,cy+Math.sin(s.a)*rr);ctx.lineTo(cx+Math.cos(s.a)*(rr+ll),cy+Math.sin(s.a)*(rr+ll));ctx.stroke();}
}
