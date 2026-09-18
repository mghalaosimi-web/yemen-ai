import re

path = r'f:\yai_v94\app\static\app.js'
content = open(path, encoding='utf-8').read()

# New, correct saveSetting function — type-aware parsing
new_fn = (
    "async function saveSetting(e){"
    "e.preventDefault();"
    "const key=document.getElementById('settingKey').value.trim(),"
    "raw=document.getElementById('settingValue').value;"
    "if(!key){showToast('\u0645\u0641\u062a\u0627\u062d \u0627\u0644\u0625\u0639\u062f\u0627\u062f \u0645\u0637\u0644\u0648\u0628','error');return}"
    "if(raw===''){showToast('\u0642\u064a\u0645\u0629 \u0627\u0644\u0625\u0639\u062f\u0627\u062f \u0644\u0627 \u064a\u0645\u0643\u0646 \u0623\u0646 \u062a\u0643\u0648\u0646 \u0641\u0627\u0631\u063a\u0629','error');return}"
    "let value;"
    "if(raw==='true')value=true;"
    "else if(raw==='false')value=false;"
    r"else if(/^-?\d+(\.\d+)?$/.test(raw.trim()))value=Number(raw.trim());"
    "else{try{value=JSON.parse(raw)}catch(ignored){value=raw}}"
    "try{"
    "const x=await api('/api/settings/'+encodeURIComponent(key),"
    "{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({value})});"
    "showToast(x.message,'success');loadSettings()"
    "}catch(err){showToast(err.message,'error')}}"
)

pat = re.compile(r'async function saveSetting\(e\)\{.*?\}\}', re.DOTALL)
m = pat.search(content)
if m:
    snippet = m.group()
    # Only replace if it looks like the buggy version
    if "value=raw===" in snippet:
        content = content[:m.start()] + new_fn + content[m.end():]
        open(path, 'w', encoding='utf-8').write(content)
        print("REPLACED OK")
    else:
        print("Already fixed or different pattern:", repr(snippet[:120]))
else:
    print("Pattern NOT FOUND")
    idx = content.find("saveSetting")
    print("saveSetting context:", repr(content[idx:idx+400]))
