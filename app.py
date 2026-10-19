from flask import Flask, request, jsonify, render_template_string, send_file
import requests, re, json, io, zipfile, os, hashlib
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, unquote

app = Flask(__name__)
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
})

PAGE = r'''<!doctype html>
<html lang="hi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Meesho Product Image Extractor</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f5fa;color:#202124;font-family:Arial,sans-serif;padding:22px}
main{max-width:1050px;margin:auto;background:#fff;padding:25px;border-radius:18px;border:1px solid #e1e4ed;box-shadow:0 8px 28px #1820440b}
h1{margin:0 0 8px;font-size:30px}.muted{color:#626779;line-height:1.55}label{display:block;font-weight:700;margin:18px 0 8px}
input{width:100%;padding:14px;border:1px solid #cfd3df;border-radius:10px;font-size:15px}
button{border:0;border-radius:10px;padding:12px 17px;font-weight:700;cursor:pointer;background:#6c3ce7;color:white;font-size:14px}
button:disabled{opacity:.55;cursor:wait}.secondary{background:#ece8fb;color:#4d2ab2}.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
#status{white-space:pre-wrap;line-height:1.55;margin:17px 0;color:#444b5d}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:14px;margin-top:20px}
.card{border:1px solid #e1e4ed;border-radius:12px;padding:10px;min-width:0}.card img{width:100%;height:190px;object-fit:contain;background:#f8f8fb;border-radius:8px}.card .url{font-size:11px;overflow-wrap:anywhere;color:#646b7a;margin:8px 0}.card button{width:100%;padding:9px}
.note{background:#fff6df;color:#694d08;padding:13px;border-radius:10px;margin-top:20px;font-size:13px;line-height:1.5}.small{font-size:12px;color:#73798a;line-height:1.5}
</style></head><body><main>
<h1>Meesho Product Image Extractor</h1>
<p class="muted">Meesho product link पेस्ट करें। टूल पेज में उपलब्ध product images खोजेगा, preview दिखाएगा और ZIP डाउनलोड बनाने की कोशिश करेगा।</p>
<label for="url">Meesho Product Link</label>
<input id="url" type="url" placeholder="https://www.meesho.com/...">
<div class="actions"><button id="extract">इमेज खोजें</button><button id="clear" class="secondary">Clear</button></div>
<div id="status" role="status">तैयार। लिंक डालकर “इमेज खोजें” दबाएँ।</div>
<div class="actions" id="downloadrow" hidden><button id="zip">सभी इमेज ZIP में डाउनलोड करें</button></div>
<div id="results" class="grid"></div>
<div class="note"><b>सीमा:</b> अगर Meesho सर्वर CAPTCHA, login या anti-bot सुरक्षा के कारण पेज का डेटा नहीं देता, तो यह टूल फोटो नहीं निकाल पाएगा। यह सुरक्षा को bypass नहीं करता। ऐसे में ब्राउज़र में product page खोलकर दोबारा कोशिश करें या अनुमत image URLs इस्तेमाल करें।</div>
<p class="small">यह टूल आपके कंप्यूटर पर ही चलता है (localhost); कोई hosted service या paid API नहीं चाहिए।</p>
</main>
<script>
const $=id=>document.getElementById(id);let images=[];
function show(list){images=list||[];$('results').innerHTML='';$('downloadrow').hidden=!images.length;
images.forEach((x,i)=>{let c=document.createElement('div');c.className='card';let im=document.createElement('img');im.src=x.url;im.loading='lazy';im.alt='Product image '+(i+1);im.onerror=()=>{im.style.opacity='.3';im.alt='Preview load नहीं हुई'};
let u=document.createElement('div');u.className='url';u.textContent=x.url;
let b=document.createElement('button');b.textContent='इमेज खोलें';b.onclick=()=>window.open(x.url,'_blank','noopener');
c.append(im,u,b);$('results').append(c)})}
$('extract').onclick=async()=>{let url=$('url').value.trim();if(!/^https?:\/\/(www\.)?meesho\.com\//i.test(url)){ $('status').textContent='कृपया सही https://www.meesho.com/... लिंक डालें।';return}
$('extract').disabled=true;$('status').textContent='पेज डाउनलोड करके इमेज खोजी जा रही हैं…';show([]);
try{let r=await fetch('/api/extract',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url})});let d=await r.json();if(!r.ok)throw Error(d.error||'Request failed');show(d.images);$('status').textContent=d.message||(`${d.images.length} image(s) मिलीं।`);if(!d.images.length)$('status').textContent+='\\nअगर Meesho ने पेज ब्लॉक किया है तो HTML से फोटो निकालना संभव नहीं हो सकता।'}
catch(e){$('status').textContent='इमेज नहीं निकल सकीं: '+e.message+'\\nMeesho ने पेज ब्लॉक किया हो सकता है या नेटवर्क उपलब्ध नहीं है।'}
finally{$('extract').disabled=false}};
$('zip').onclick=async()=>{if(!images.length)return;$('zip').disabled=true;$('status').textContent='इमेज डाउनलोड करके ZIP बनाई जा रही है…';
try{let r=await fetch('/api/zip',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({images})});if(!r.ok){let d=await r.json();throw Error(d.error||'ZIP नहीं बनी')}let blob=await r.blob();let a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='meesho-product-images.zip';a.click();URL.revokeObjectURL(a.href);$('status').textContent='ZIP डाउनलोड शुरू हो गया।'}
catch(e){$('status').textContent='ZIP नहीं बन सकी: '+e.message+'\\nकुछ image servers डाउनलोड रोक सकते हैं।'}finally{$('zip').disabled=false}};
$('clear').onclick=()=>{$('url').value='';show([]);$('status').textContent='फॉर्म साफ कर दिया गया।'};
</script></body></html>'''

def valid_meesho(url):
    p = urlparse(url)
    return p.scheme in ("http", "https") and (p.hostname or "").lower().endswith("meesho.com")

def normalize_image(u, base_url):
    if not isinstance(u, str):
        return None
    u = unquote(u.strip().replace("\\\\/", "/"))
    if u.startswith("//"):
        u = "https:" + u
    u = urljoin(base_url, u)
    p = urlparse(u)
    if p.scheme not in ("http", "https"):
        return None
    low = u.lower()
    if any(x in low for x in ("data:image", "base64,", "sprite", "favicon", "logo", "avatar")):
        return None
    if not any(ext in low for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif", "image", "images")):
        if not any(x in (p.hostname or "").lower() for x in ("meesho")):
            return None
    return u

def walk_json(obj, base_url, found):
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = str(k).lower()
            if isinstance(v, str) and kl in ("image", "images", "imageurl", "image_url", "src", "url", "original", "largeimage", "thumbnail"):
                u = normalize_image(v, base_url)
                if u: found.add(u)
            else:
                walk_json(v, base_url, found)
    elif isinstance(obj, list):
        for v in obj: walk_json(v, base_url, found)
    elif isinstance(obj, str) and obj.startswith(("http://", "https://", "//")):
        u = normalize_image(obj, base_url)
        if u: found.add(u)

def scrape(url):
    r = SESSION.get(url, timeout=25, allow_redirects=True)
    if r.status_code >= 400:
        raise ValueError(f"Meesho ने HTTP {r.status_code} लौटाया।")
    html = r.text
    soup = BeautifulSoup(html, "html.parser")
    found = set()
    for tag in soup.find_all("meta"):
        prop = (tag.get("property") or tag.get("name") or "").lower()
        if prop in ("og:image", "twitter:image", "twitter:image:src"):
            u = normalize_image(tag.get("content", ""), r.url)
            if u: found.add(u)
    for tag in soup.find_all("img"):
        for attr in ("src", "data-src", "data-original", "data-lazy-src", "srcset"):
            value = tag.get(attr)
            if not value: continue
            if attr == "srcset":
                value = value.split(",")[0].strip().split(" ")[0]
            u = normalize_image(value, r.url)
            if u: found.add(u)
    for script in soup.find_all("script", type="application/ld+json"):
        try: walk_json(json.loads(script.string or script.get_text()), r.url, found)
        except Exception: pass
    for match in re.findall(r'''(?i)(?:https?:)?(?:\\/\\/|//)[^"'\\\s<>]+''', html):
        candidate = match.replace("\\u002F", "/").replace("\\/", "/").rstrip("),;")
        u = normalize_image(candidate, r.url)
        if u: found.add(u)
    result = sorted(found, key=lambda x: (not any(t in x.lower() for t in ("meesho")), len(x)))
    return r.url, result[:100], len(html)

@app.get("/")
def home():
    return render_template_string(PAGE)

@app.post("/api/extract")
def api_extract():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not valid_meesho(url):
        return jsonify(error="कृपया valid Meesho product link दें।"), 400
    try:
        final_url, urls, size = scrape(url)
        images = [{"url": u} for u in urls]
        if not images:
            msg = f"पेज डाउनलोड हुआ ({size:,} characters), लेकिन image URLs नहीं मिले। Meesho ने dynamic content या anti-bot protection इस्तेमाल की हो सकती है।"
        else:
            msg = f"{len(images)} संभावित image URL मिले। Preview देखकर जाँचें।"
        return jsonify(images=images, message=msg, final_url=final_url)
    except requests.RequestException as e:
        return jsonify(error="वेबसाइट से कनेक्ट नहीं हो पाया: " + str(e)), 502
    except ValueError as e:
        return jsonify(error=str(e)), 502

@app.post("/api/zip")
def api_zip():
    data = request.get_json(silent=True) or {}
    images = data.get("images") or []
    if not images or len(images) > 100:
        return jsonify(error="ZIP के लिए 1 से 100 image URLs तक दें।"), 400
    mem = io.BytesIO()
    used = set()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for i, item in enumerate(images, 1):
            url = item.get("url", "") if isinstance(item, dict) else ""
            p = urlparse(url)
            if p.scheme not in ("http", "https"):
                continue
            try:
                resp = SESSION.get(url, timeout=20, stream=True)
                if resp.status_code != 200: continue
                ctype = resp.headers.get("content-type", "").lower()
                if "image" not in ctype and not re.search(r"\.(jpg|jpeg|png|webp|avif)(?:$|\?)", url, re.I):
                    continue
                content = resp.content
                if not content or len(content) > 20*1024*1024: continue
                ext = os.path.splitext(urlparse(url).path)[1].lower()
                if ext not in (".jpg", ".jpeg", ".png", ".webp", ".avif"):
                    ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/avif": ".avif"}.get(ctype.split(";")[0], ".img")
                name = f"product-image-{i}{ext}"
                if name in used: name = f"product-image-{i}-{hashlib.md5(url.encode()).hexdigest()[:5]}{ext}"
                used.add(name)
                z.writestr(name, content)
            except Exception:
                continue
    mem.seek(0)
    if not used:
        return jsonify(error="कोई image डाउनलोड नहीं हुई। Image server ने access रोका हो सकता है।"), 502
    return send_file(mem, mimetype="application/zip", as_attachment=True, download_name="meesho-product-images.zip")

if __name__ == "__main__":
    print("\\nMeesho Image Extractor is running: http://127.0.0.1:5000")
    print("इस विंडो को खुला रखें। बंद करने के लिए Ctrl+C दबाएँ.\\n")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
