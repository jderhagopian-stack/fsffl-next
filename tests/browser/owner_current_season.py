"""Local component journey, using an explicitly supplied fixture review page."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',required=True)
    parser.add_argument('--output-dir',required=True,type=Path)
    args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(args.url);page.locator('.behavior-current-season').wait_for()
        owners=page.locator('[data-behavior-owner]').count()
        for index in range(owners):
            page.locator('[data-behavior-owner]').nth(index).click()
            current=page.locator('.behavior-current-season')
            assert 'Where things stand' in current.inner_text()
            assert current.locator('.behavior-resume-stats strong').count()==3
            current.locator('summary').first.click()
            assert current.locator('details[open]').count()>=1
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(args.output_dir/'owner-season-mobile.png'),full_page=True)
        # A legacy saved profile initializes its missing current feed exactly once.
        page.evaluate("""async()=>{
          window.__ownerRefreshCalls=0;let initial=true;
          window.api=async path=>{
            if(path==='/api/behavioral/refresh'){window.__ownerRefreshCalls++;return {status:'running'}}
            if(path==='/api/behavioral/status')return {status:'ready'};
            if(initial){initial=false;const old=JSON.parse(JSON.stringify(supplied));
              old.profiles.forEach(p=>p.current_season.counts=null);return old}
            return supplied;
          };
          await renderFsfflBehavioralIntelligence();
        }""")
        page.locator('[data-behavior-owner]').first.click()
        page.wait_for_timeout(2300)
        assert page.evaluate('window.__ownerRefreshCalls')==1
        assert page.locator('.behavior-current-season .behavior-live-activity').count()==1
        # Updating activity must not replace another route after the user leaves.
        page.evaluate("""()=>{window.api=async path=>path==='/api/behavioral/refresh'?{status:'running'}:{status:'ready'};}""")
        page.locator('[data-behavior-refresh-season]').click()
        page.evaluate("document.querySelector('#generic-screen').innerHTML='<h1>Another page</h1>'")
        page.wait_for_timeout(2300)
        assert page.locator('h1').inner_text()=='Another page'
        page.reload();page.locator('.behavior-current-season').wait_for()
        page.set_viewport_size({'width':1365,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(args.output_dir/'owner-season-desktop.png'),full_page=True)
        assert not errors,errors
        browser.close()
    print(json.dumps({'owner_switches':owners,'mobile_width':390,'overflow':False,
        'late_update_route_overwrite':False,'missing_activity_initialized_once':True,'javascript_errors':len(errors),
        'fixture_component_review':True,'physical_iphone_verified':False}))


if __name__=='__main__':main()
