from flask import Flask, request, jsonify, render_template_string
import requests, re, json, os
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, unquote

app = Flask(__name__)
S = requests.Session()
S.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36","Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8","Accept-Language":"en-US,en;q=0.9,hi;q=0.8"})
PAGE = r"""<!doctype html><html lang="hi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Meesho Images to Gemini Share</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f5fa;color:#202124;font-family:Arial,sans-serif;padding:16px}main{max-width:1000px;margin:auto;background:white;padding:23px;border-radius:18px;border:1px solid #e1e4ed}
h1{font-size:clamp(24px,4vw,32px);margin:0 0 8px}.muted{color:#626779;line-height:1.5}label{display:block;font-weight:bold;margin:18px 0 8px}
input,textarea{width:100%;padding:13px;border:1px solid #cfd3df;border-radius:10px;font:inherit}textarea{min-height:230px;line-height:1.45;resize:vertical}
button{border:0;border-radius:10px;padding:12px 15px;font-weight:bold;cursor:pointer;background:#6c3ce7;color:white}.secondary{background:#ece8fb;color:#4d2ab2}.green{background:#137a4b}.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:12px}
#status{white-space:pre-wrap;line-height:1.5;margin:16px 0}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:12px;margin-top:18px}.card{border:1px solid #e1e4ed;border-radius:12px;padding:9px;min-width:0}.card img{width:100%;height:170px;object-fit:contain;background:#f8f8fb}.card .url{font-size:11px;overflow-wrap:anywhere;color:#646b7a;margin:8px 0}.card button{width:100%;padding:9px}.note{background:#fff6df;color:#694d08;padding:13px;border-radius:10px;margin-top:18px;font-size:13px;line-height:1.5}.small{font-size:12px;color:#73798a;line-height:1.5}
</style></head><body><main><h1>Meesho Images → Gemini Share</h1>
<p class="muted">Product images, editable Gemini prompt, custom default prompt, and share/copy controls.</p>
<label for="url">1. Meesho Product Link</label><input id="url" type="url" placeholder="https://www.meesho.com/...">
<div class="actions"><button id="extract">इमेज खोजें</button><button id="clear" class="secondary">Clear</button></div><div id="status">लिंक डालकर इमेज खोजें। HTTP 403 आए तो नीचे image address paste करें।</div>
<label for="manual">2. Image address (एक URL प्रति लाइन)</label><textarea id="manual" style="min-height:90px" placeholder="Chrome में image पर right-click → Copy image address"></textarea>
<div class="actions"><button id="showManual" class="secondary">URL से preview बनाएँ</button></div><div id="results" class="grid"></div>
<hr style="border:0;border-top:1px solid #e8eaf0;margin:24px 0">
<label for="prompt">3. Gemini Prompt (बदल सकते हैं)</label><textarea id="prompt"></textarea>
<div class="actions"><button id="savePrompt" class="secondary">इसे Default Prompt बनाएँ</button><button id="resetPrompt" class="secondary">Original Prompt वापस लाएँ</button></div>
<p class="small">Custom default इसी browser/device में save होगा। दूसरे फोन/कंप्यूटर पर अलग से set करना होगा।</p>
<div class="actions"><button id="copyPrompt">Prompt Copy करें</button><button id="openGemini" class="secondary">Google Gemini खोलें</button><button id="share" class="green">Images + Prompt Share करें</button></div>
<p class="small">Native sharing तभी image files share करेगी जब browser, image host और device इसकी अनुमति दें।</p>
<div class="note"><b>महत्वपूर्ण:</b> वेबसाइट Gemini में अपने-आप image attach या prompt submit नहीं कर सकती। अगर share sheet में Gemini नहीं दिखता, तो Gemini खोलें, images attach करें और prompt paste करें। Meesho की HTTP 403 रोक को यह tool bypass नहीं करता।</div></main>
<script>
const DEFAULT_PROMPT = "Using the attached image as the exact and ONLY product reference, create a vertical 9:16, 10-second Instagram Reel style product video.\n\nShow ONLY this exact saree. It must look 100% identical to the attached image in color, fabric, embroidery, border and pallu design. Do not change or redesign anything.\n\nScene 1 (0-3s): A woman's hands hold the saree inside a sealed transparent polybag against a plain cream wall with warm fairy lights and green ivy. Slight camera push-in.\n\nScene 2 (3-6s): The hands take the saree out and spread it wide, showing the full fabric, embroidery and border. The fabric flows softly.\n\nScene 3 (6-10s): A young woman with long wavy hair wears this exact saree and takes a mirror selfie with a phone covering her face. Frame only from head to knees, so her feet and the floor are not visible. Cozy bedroom with warm lamp light. She slowly turns to show the pallu and the drape.\n\nDo NOT show any shoes, heels, sandals, footwear, jewellery, bag, accessories, blouse close-up, or any other item. No text, no logo, no watermark, no music, no voice.\n\nStyle: realistic, bright, handheld phone-camera feel, soft natural lighting, smooth gentle camera movement.";
const $=id=>document.getElementById(id);let images=[];
try{$('prompt').value=localStorage.getItem('geminiDefaultPrompt')||DEFAULT_PROMPT}catch{$('prompt').value=DEFAULT_PROMPT}
function show(list){images=[...new Map((list||[]).filter(x=>x&&x.url).map(x=>[x.url,x])).values()];$('results').innerHTML='';images.forEach((x,i)=>{let c=document.createElement('div');c.className='card';let im=document.createElement('img');im.src=x.url;im.loading='lazy';im.alt='Product image '+(i+1);im.onerror=()=>{im.style.opacity='.3';im.alt='Preview नहीं खुली'};let u=document.createElement('div');u.className='url';u.textContent=x.url;let b=document.createElement('button');b.textContent='Image खोलें';b.onclick=()=>window.open(x.url,'_blank','noopener');c.append(im,u,b);$('results').append(c)})}
$('extract').onclick=async()=>{let url=$('url').value.trim();if(!/^https?:\/\/(www\.)?meesho\.com\//i.test(url)){$('status').textContent='सही Meesho link डालें।';return}$('extract').disabled=true;$('status').textContent='इमेज खोजी जा रही हैं…';try{let r=await fetch('/api/extract',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});let d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');show(d.images);$('status').textContent=d.message||d.images.length+' images मिलीं।'}catch(e){$('status').textContent='इमेज नहीं निकल सकीं: '+e.message+'\nChrome में image पर right-click → Copy image address करके नीचे paste करें।'}finally{$('extract').disabled=false}};
$('showManual').onclick=()=>{let list=$('manual').value.split(/\s+/).filter(x=>/^https?:\/\//i.test(x)).map(url=>({url}));show(list);$('status').textContent=list.length+' image URL जोड़े गए।'};
$('savePrompt').onclick=()=>{try{localStorage.setItem('geminiDefaultPrompt',$('prompt').value);$('status').textContent='Custom default prompt इस browser में save हो गया।'}catch{$('status').textContent='Browser ने save की अनुमति नहीं दी।'}};
$('resetPrompt').onclick=()=>{$('prompt').value=DEFAULT_PROMPT;try{localStorage.removeItem('geminiDefaultPrompt')}catch{}$('status').textContent='Original prompt वापस आ गया।'};
$('copyPrompt').onclick=async()=>{try{await navigator.clipboard.writeText($('prompt').value);$('status').textContent='Prompt copy हो गया। Gemini में paste करें।'}catch{$('prompt').select();document.execCommand('copy');$('status').textContent='Prompt copy करने की कोशिश हुई।'}};
$('openGemini').onclick=()=>window.open('https://gemini.google.com/app','_blank','noopener');
async function getFile(x,i){let r=await fetch(x.url);if(!r.ok)throw Error('Image fetch blocked');let blob=await r.blob();if(!blob.type.startsWith('image/'))throw Error('URL image नहीं है');let ext=(blob.type.split('/')[1]||'jpeg').replace('jpeg','jpg');return new File([blob],'product-image-'+(i+1)+'.'+ext,{type:blob.type})}
$('share').onclick=async()=>{try{if(images.length&&navigator.share&&navigator.canShare){let files=[];for(let i=0;i<images.length;i++)files.push(await getFile(images[i],i));let data={title:'Product images and Gemini prompt',text:$('prompt').value,files};if(navigator.canShare(data)){await navigator.share(data);$('status').textContent='Share menu खुल गया। Gemini उपलब्ध हो तो चुनें।';return}}try{await navigator.clipboard.writeText($('prompt').value)}catch{}$('status').textContent=images.length?'Prompt copy करने की कोशिश हुई। Browser सीधे image files share नहीं कर पाया; Gemini में images attach करके prompt paste करें।':'पहले image URLs जोड़ें। Prompt copy करने की कोशिश हुई।';window.open('https://gemini.google.com/app','_blank','noopener')}catch(e){try{await navigator.clipboard.writeText($('prompt').value)}catch{}$('status').textContent='Direct image share संभव नहीं हुआ। Gemini खोलकर images attach करें और prompt paste करें।';window.open('https://gemini.google.com/app','_blank','noopener')}};
$('clear').onclick=()=>{$('url').value='';$('manual').value='';show([]);$('status').textContent='फॉर्म साफ कर दिया गया।'};
</script></body></html>"""
def valid(url):
    p=urlparse(url)
    return p.scheme in ("http","https") and (p.hostname or "").lower().endswith("meesho.com")
def norm(v,base):
    if not isinstance(v,str): return None
    v=unquote(v.strip().replace("\\\\/","/"))
    if v.startswith("//"): v="https:"+v
    v=urljoin(base,v); p=urlparse(v); low=v.lower()
    if p.scheme not in ("http","https") or any(t in low for t in ("data:image","base64,","favicon","sprite","logo","avatar")): return None
    if not any(t in low for t in (".jpg",".jpeg",".png",".webp",".avif","image")) and "meesho" not in (p.hostname or "").lower(): return None
    return v
@app.get("/")
def home(): return render_template_string(PAGE)
@app.post("/api/extract")
def extract():
    url=((request.get_json(silent=True) or {}).get("url") or "").strip()
    if not valid(url): return jsonify(error="कृपया सही Meesho product link दें।"),400
    try:
        r=S.get(url,timeout=25,allow_redirects=True)
        if r.status_code==403: return jsonify(error="Meesho ने HTTP 403 लौटाया। Chrome से image address कॉपी करके नीचे paste करें।"),502
        r.raise_for_status(); soup=BeautifulSoup(r.text,"html.parser"); found=set()
        for t in soup.find_all("meta"):
            if (t.get("property") or t.get("name") or "").lower() in ("og:image","twitter:image","twitter:image:src"):
                u=norm(t.get("content",""),r.url)
                if u: found.add(u)
        for t in soup.find_all("img"):
            for a in ("src","data-src","data-original","data-lazy-src","srcset"):
                v=t.get(a)
                if v:
                    if a=="srcset": v=v.split(",")[0].strip().split(" ")[0]
                    u=norm(v,r.url)
                    if u: found.add(u)
        return jsonify(images=[{"url":u} for u in sorted(found)[:80]],message=f"{len(found)} संभावित image URL मिले।")
    except requests.RequestException: return jsonify(error="Meesho से कनेक्ट नहीं हो पाया।"),502
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")))
