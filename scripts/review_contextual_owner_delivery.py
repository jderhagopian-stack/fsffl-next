"""Render an API-shaped owner profile payload with the actual product component.

Local review only: no acquisition, database writes, hosting or production change.
The normal application API is verified separately by the integrated route test.
"""
import argparse
import json
from pathlib import Path
import shutil
from fsffl.behavioral.models import OwnerBehaviorProfile


def write_owner_review(payload,output_dir):
    allowed=set(OwnerBehaviorProfile.model_fields)|{'current_team_id','current_team_name'}
    profiles=[]
    for item in payload.get('profiles',()):
        if set(item)-allowed:raise ValueError('unexpected owner review fields')
        profile=OwnerBehaviorProfile.model_validate({k:v for k,v in item.items()if k in OwnerBehaviorProfile.model_fields})
        profiles.append({**profile.model_dump(mode='json'),**{k:item[k]for k in ('current_team_id','current_team_name')if k in item}})
    if not profiles:raise ValueError('owner review requires real supplied profiles')
    safe={'status':'ready','profiles':profiles}
    encoded=json.dumps(safe,ensure_ascii=True).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    out=Path(output_dir);static=out/'static';static.mkdir(parents=True,exist_ok=True)
    source=Path(__file__).resolve().parents[1]/'src/fsffl/product/static'
    for name in ('app.css','behavioral_intelligence.css','behavioral_intelligence.js'):
        shutil.copyfile(source/name,static/name)
    html='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Owner history · local review</title><link rel="stylesheet" href="static/app.css"><link data-fsffl-behavior-css rel="stylesheet" href="static/behavioral_intelligence.css"><style>main{max-width:1100px;margin:auto;padding:16px}.review-label{color:#9ab8c8;font-size:12px;margin:0 0 12px}[data-behavior-open-trade]{display:none}</style></head><body><main><p class="review-label">Local review · historical owner context</p><div id="generic-screen"></div></main><script id="owner-review-data" type="application/json">'''+encoded+'''</script><script>
const supplied=JSON.parse(document.getElementById('owner-review-data').textContent);
const state={context:{league_id:'local-owner-review',team_id:null}};
function escapeHtml(value){return String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
async function api(path){if(path!=='/api/behavioral/profiles')throw new Error('Only owner history is available in this local review');return supplied}
window.setRoute=function(){};
</script><script src="static/behavioral_intelligence.js"></script><script>renderFsfflBehavioralIntelligence();</script></body></html>'''
    (out/'index.html').write_text(html)
    return out/'index.html'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profiles-json',required=True,type=Path)
    p.add_argument('--output-dir',required=True,type=Path)
    args=p.parse_args()
    print(write_owner_review(json.loads(args.profiles_json.read_text()),args.output_dir))


if __name__=='__main__':main()
