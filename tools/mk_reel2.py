# -*- coding: utf-8 -*-
"""표지 한 장의 이야기를 움직이는 영상으로 — 제29호 「코르크의 내력」 릴스.

  python3 mk_reel2.py <출력.mp4> <음악.wav>
  1080×1920 · 30fps · 18초. 장면: 제호 → 제목 → 나무가 자라고 껍질을 벗긴다(25살, 9년마다)
  → 세 번째 껍질에서 마개가 나온다(43살) → 「마개 하나에 마흔 해」 → 계정.
"""
import os, sys, subprocess, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vino as V
from playwright.sync_api import sync_playwright

FPS=30; SEC=18.0
AC='#2F4A3A'; CREAM=V.CREAM; GOLD=V.GOLD; RED=V.RED

HTML = f'''<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8"><style>{V.CSS}
html,body{{margin:0;background:{AC}}}
#fr{{width:540px;height:960px;position:relative;overflow:hidden;background:{AC};color:{CREAM};font-family:'NM',serif;word-break:keep-all}}
.ab{{position:absolute;left:0;right:0;text-align:center}}
.sp{{letter-spacing:.42em;padding-left:.42em;font-size:12px;opacity:.85}}
.hd{{font-weight:800;font-size:50px;letter-spacing:.26em;padding-left:.26em}}
.eb2{{font-size:12px;letter-spacing:.36em;padding-left:.36em;color:{GOLD};font-weight:700}}
.tt{{font-weight:800;font-size:52px;line-height:1.2}}
.ln{{font-size:17px;line-height:1.6}}
.big{{font-weight:800;font-size:34px;line-height:1.3}}
.sm{{font-size:13px;line-height:1.7;opacity:.85}}
.gold{{color:{GOLD};letter-spacing:.22em;font-weight:700;font-size:15px}}
.dig{{font-family:'Bod',serif;font-style:italic;font-size:64px;line-height:1}}
.lat{{font-family:'Bod',serif;font-style:italic}}
.el{{opacity:0;will-change:transform,opacity}}
</style></head><body>{V.DEFS}
<div id="fr">
 <div id="mast1" class="ab sp el" style="top:118px">비 노 에 뱅 통 신</div>
 <div id="mast2" class="ab hd el" style="top:136px">와인호외</div>
 <div id="rule1" class="el" style="position:absolute;left:270px;top:206px;height:2.4px;width:0;background:{CREAM};transform-origin:center"></div>
 <div id="rule2" class="el" style="position:absolute;left:270px;top:211px;height:.8px;width:0;background:{CREAM};opacity:.6"></div>
 <div id="eyeb" class="ab eb2 el" style="top:238px">나 무 껍 질 의 일</div>
 <div id="title" class="ab tt el" style="top:262px">코르크의 내력</div>
 <div id="latin" class="ab sm el" style="top:336px"><span class="lat">Quercus suber</span>(쿠에르쿠스 수베르)</div>

 <svg id="scene" viewBox="0 0 420 300" style="position:absolute;left:0;top:372px;width:540px;height:386px;overflow:visible">
  <line id="ground" x1="40" y1="232" x2="380" y2="232" stroke="{CREAM}" stroke-width="2.4" stroke-linecap="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1" opacity=".7"/>
  <g id="tree" transform="translate(150,232)">
    <g id="trunk" style="transform-origin:0 0">
      <rect x="-17" y="-92" width="34" height="92" fill="{CREAM}"/>
    </g>
    <g id="canopy" style="transform-origin:0 -110px">
      <circle cx="-32" cy="-128" r="27" fill="{CREAM}" opacity=".92"/>
      <circle cx="32" cy="-128" r="27" fill="{CREAM}" opacity=".92"/>
      <circle cx="0" cy="-146" r="32" fill="{CREAM}"/>
      <path d="M-54 -122 q54 20 108 0 q-18 18 -54 18 q-36 0 -54 -18 Z" fill="{CREAM}"/>
    </g>
    <clipPath id="bandclip"><rect id="bandrect" x="-17" y="-62" width="34" height="0"/></clipPath>
    <g clip-path="url(#bandclip)">
      <rect x="-17" y="-62" width="34" height="44" fill="{AC}"/>
      <path d="M-17 -62 h34 M-17 -18 h34" stroke="{GOLD}" stroke-width="2.6"/>
      <path d="M-11 -52 h22 M-11 -42 h22 M-11 -32 h22" stroke="{GOLD}" stroke-width="1.3" opacity=".6"/>
    </g>
  </g>
  <g id="numg" opacity="0">
    <text id="num" x="300" y="118" text-anchor="middle" fill="{CREAM}" font-family="Bod" font-style="italic" font-size="84">0</text>
    <text id="numlab" x="300" y="148" text-anchor="middle" fill="{CREAM}" font-family="NM" font-size="13" letter-spacing="2">살에 처음 벗긴다</text>
  </g>
  <g id="nineg" opacity="0">
    <text x="300" y="118" text-anchor="middle" fill="{CREAM}" font-family="Bod" font-style="italic" font-size="84">9</text>
    <text x="300" y="148" text-anchor="middle" fill="{CREAM}" font-family="NM" font-size="13" letter-spacing="2">해마다 한 번</text>
  </g>
  <g id="tl" opacity="0">
    <line x1="60" y1="262" x2="360" y2="262" stroke="{CREAM}" stroke-width="1.2" opacity=".5"/>
    <g id="tk1" opacity="0"><line x1="90" y1="254" x2="90" y2="270" stroke="{CREAM}" stroke-width="2"/><text x="90" y="247" text-anchor="middle" fill="{CREAM}" font-family="Bod" font-style="italic" font-size="20">25</text><text x="90" y="286" text-anchor="middle" fill="{CREAM}" font-family="NM" font-size="11" opacity=".8">첫째</text></g>
    <g id="tk2" opacity="0"><line x1="210" y1="254" x2="210" y2="270" stroke="{CREAM}" stroke-width="2"/><text x="210" y="247" text-anchor="middle" fill="{CREAM}" font-family="Bod" font-style="italic" font-size="20">34</text><text x="210" y="286" text-anchor="middle" fill="{CREAM}" font-family="NM" font-size="11" opacity=".8">둘째</text></g>
    <g id="tk3" opacity="0"><line x1="330" y1="254" x2="330" y2="270" stroke="{GOLD}" stroke-width="2.6"/><text x="330" y="247" text-anchor="middle" fill="{GOLD}" font-family="Bod" font-style="italic" font-size="22">43</text><text x="330" y="286" text-anchor="middle" fill="{GOLD}" font-family="NM" font-size="11" font-weight="700">셋째 — 마개</text></g>
  </g>
  <g id="cork" opacity="0" style="transform-origin:300px 150px">
    <g transform="translate(300,140) scale(1.35)">
      <path d="M-15 -34 h30 v68 h-30 Z" fill="{CREAM}"/>
      <ellipse cx="0" cy="-34" rx="15" ry="5.6" fill="{CREAM}"/>
      <ellipse cx="0" cy="-34" rx="15" ry="5.6" fill="none" stroke="{AC}" stroke-width="1.4" opacity=".65"/>
      <ellipse cx="0" cy="34" rx="15" ry="5.6" fill="{CREAM}"/>
      <circle cx="-7" cy="-18" r="1.8" fill="{AC}" opacity=".6"/><circle cx="5" cy="-9" r="1.4" fill="{AC}" opacity=".6"/>
      <circle cx="-3" cy="2" r="2.0" fill="{AC}" opacity=".6"/><circle cx="8" cy="11" r="1.5" fill="{AC}" opacity=".6"/>
      <circle cx="-8" cy="20" r="1.6" fill="{AC}" opacity=".6"/><circle cx="3" cy="26" r="1.3" fill="{AC}" opacity=".6"/>
    </g>
  </g>
 </svg>

 <div id="l1" class="ab ln el" style="top:782px">스물다섯 해를 기다려 <b>처음 벗기고</b></div>
 <div id="l2" class="ab ln el" style="top:814px">그 뒤로는 <b>아홉 해마다 한 번</b></div>
 <div id="l3" class="ab ln el" style="top:782px">첫 껍질로는 마개를 못 만든다</div>
 <div id="l4" class="ab ln el" style="top:814px"><b>세 번째부터</b>가 마개가 된다</div>
 <div id="bigl" class="ab big el" style="top:772px">마개 하나에<br>마흔 해</div>
 <div id="sm1" class="ab sm el" style="top:868px">한 나무에서 열일곱 번 · 수명 이백 해 남짓</div>
 <div id="end1" class="ab sm el" style="top:800px">본지 제 二十九 호 · 전편 여덟 장은 피드에</div>
 <div id="end2" class="ab gold el" style="top:836px">@ vinoetvin</div>
 <div id="foot" class="ab el" style="top:905px;font-size:10.5px;letter-spacing:.3em;opacity:.55">비 노 에 뱅 통 신</div>
</div>
<script>
const $=id=>document.getElementById(id);
const cl=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const eo=x=>1-Math.pow(1-x,3), eio=x=>x<.5?4*x*x*x:1-Math.pow(-2*x+2,3)/2;
function seg(t,a,b){{return cl((t-a)/(b-a));}}
function show(id,t,a,b,dy=14,from=null){{const e=$(id);const x=eo(seg(t,a,b));e.style.opacity=x;e.style.transform=`translateY(${{(1-x)*dy}}px)`;}}
function hide(id,t,a,b){{const e=$(id);const x=seg(t,a,b);if(x>0){{e.style.opacity=(1-x)*parseFloat(e.style.opacity||1);}}}}
function fade(id,t,a,b,c,d){{const e=$(id);let o=eo(seg(t,a,b));if(c!==undefined)o*=1-eo(seg(t,c,d));e.style.opacity=o;}}
function setT(t){{
  // 제호
  show('mast1',t,0.1,0.9,8); show('mast2',t,0.3,1.3,18);
  const r=eo(seg(t,0.9,1.7)); $('rule1').style.opacity=1; $('rule1').style.width=(464*r)+'px'; $('rule1').style.left=(270-232*r)+'px';
  $('rule2').style.opacity=.6; $('rule2').style.width=(464*r)+'px'; $('rule2').style.left=(270-232*r)+'px';
  show('eyeb',t,1.5,2.2,8); show('title',t,1.8,2.9,22); show('latin',t,2.5,3.2,8);
  // 땅과 나무
  const g=eo(seg(t,3.0,3.9)); $('ground').setAttribute('stroke-dashoffset',1-g);
  const tr=eo(seg(t,3.4,4.6)); $('trunk').style.transform=`scaleY(${{tr}})`;
  const ca=eio(seg(t,4.2,5.2)); $('canopy').style.transform=`scale(${{ca}})`; $('canopy').style.opacity=ca;
  // 25 — 세는 숫자
  const n=seg(t,5.2,6.4); $('numg').setAttribute('opacity',eo(seg(t,5.1,5.6))*(1-eo(seg(t,7.3,7.8))));
  $('num').textContent=Math.round(eo(n)*25);
  show('l1',t,5.4,6.1,10); 
  // 껍질 벗기기 — 띠가 아래에서 위로
  const b=eo(seg(t,6.3,7.1)); $('bandrect').setAttribute('height',44*b); $('bandrect').setAttribute('y',-18-44*b);
  // 9
  $('nineg').setAttribute('opacity',eo(seg(t,7.6,8.1))*(1-eo(seg(t,9.6,10.1))));
  show('l2',t,7.7,8.4,10);
  // 시간선 25·34·43
  $('tl').setAttribute('opacity',eo(seg(t,8.3,8.8))*(1-eo(seg(t,13.6,14.2))));
  $('tk1').setAttribute('opacity',eo(seg(t,8.5,8.9))); $('tk2').setAttribute('opacity',eo(seg(t,9.1,9.5))); $('tk3').setAttribute('opacity',eo(seg(t,9.8,10.3)));
  // 문장 교체
  hide('l1',t,9.9,10.4); hide('l2',t,9.9,10.4);
  if(t>10.4){{show('l3',t,10.5,11.1,10); show('l4',t,10.8,11.4,10);}}
  // 마개가 나온다 — 띠 자리에서 올라와 오른쪽에 선다
  const ck=eio(seg(t,10.6,11.8)); $('cork').setAttribute('opacity',Math.min(1,ck*2));
  $('cork').style.transform=`translate(${{(1-ck)*-150}}px,${{(1-ck)*100}}px) scale(${{0.6+0.4*ck}}) rotate(${{(1-ck)*-25}}deg)`;
  // 큰 문장
  hide('l3',t,13.0,13.5); hide('l4',t,13.0,13.5);
  if(t>13.4){{show('bigl',t,13.5,14.3,16); show('sm1',t,14.3,14.9,8);}}
  hide('latin',t,13.4,13.9);
  // 마무리
  hide('bigl',t,16.0,16.5); hide('sm1',t,16.0,16.5);
  if(t>16.4){{show('end1',t,16.5,17.0,8); show('end2',t,16.7,17.2,8);}}
  show('foot',t,1.0,1.8,0);
}}
window.setT=setT; setT(0);
</script></body></html>'''

def make_grain(path):
    import numpy as np
    from PIL import Image
    rng = np.random.default_rng(3)
    g = rng.normal(118, 26, (1920, 1080)).clip(0, 255).astype('uint8')
    Image.fromarray(g, 'L').convert('RGB').save(path)

def main():
    out_mp4, music = sys.argv[1], sys.argv[2]
    work = tempfile.mkdtemp(prefix='reel2_')
    hp = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_reel2.html')
    open(hp,'w',encoding='utf-8').write(HTML)
    n = int(SEC*FPS)
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width':540,'height':960}, device_scale_factor=2)
        pg.goto('file://'+hp); pg.wait_for_timeout(400)
        for i in range(n):
            pg.evaluate(f'setT({i/FPS:.4f})')
            pg.screenshot(path=os.path.join(work, f'f_{i:04d}.png'), clip={'x':0,'y':0,'width':540,'height':960}, animations='disabled')
        b.close()
    grain = os.path.join(work,'grain.png'); make_grain(grain)
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',os.path.join(work,'f_%04d.png'),
                    '-loop','1','-i',grain,'-i',music,
                    '-filter_complex','[0:v]format=gbrp[a];[1:v]format=gbrp[b];[a][b]blend=all_mode=screen:all_opacity=0.18,format=yuv420p[v]','-map','[v]','-map','2:a',
                    '-c:v','libx264','-profile:v','high','-level','4.1','-pix_fmt','yuv420p','-r',str(FPS),
                    '-g',str(FPS*2),'-keyint_min',str(FPS*2),'-sc_threshold','0','-b:v','7M','-maxrate','9M','-bufsize','14M',
                    '-c:a','aac','-b:a','128k','-ar','48000','-ac','2','-movflags','+faststart','-shortest',out_mp4], check=True)
    # 표지: 마지막 장면 직전(완성된 그림) 프레임
    from PIL import Image
    Image.open(os.path.join(work, f'f_{int(15.2*FPS):04d}.png')).convert('RGB').save(os.path.splitext(out_mp4)[0]+'_cover.jpg','JPEG',quality=90,subsampling=0)
    # 검토용 샘플
    for k,tt in enumerate([0.8,2.6,4.8,6.0,7.0,9.0,11.6,14.5,17.2]):
        shutil.copy(os.path.join(work, f'f_{int(tt*FPS):04d}.png'), f'/tmp/r2_{k}.png')
    shutil.rmtree(work, ignore_errors=True)
    print(f'{out_mp4}  {SEC:.0f}초  {n}프레임')

if __name__=='__main__':
    main()
