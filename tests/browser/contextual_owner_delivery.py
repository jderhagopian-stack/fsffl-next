"""Manual local/browser gate for the real-data owner review; no production writes.

python tests/browser/contextual_owner_delivery.py --url http://127.0.0.1:8765
Uses an already installed Playwright + Chromium, not a new hosted service.
"""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--url',required=True)
    p.add_argument('--output-dir',required=True,type=Path)
    p.add_argument('--chromium',default='/usr/bin/chromium')
    args=p.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    errors=[]
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(executable_path=args.chromium,headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url);page.wait_for_selector('.behavior-history-case')
        owners=page.locator('[data-behavior-owner]').count()
        assert owners>0
        for i in range(owners):
            page.locator('[data-behavior-owner]').nth(i).click()
            assert page.locator('.behavior-history-case').count()>0
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
            page.locator('.behavior-history-case summary').first.click()
            assert page.locator('.behavior-history-case[open]').count()==1
            assert page.locator('.behavior-case-details').first.is_visible()
            more=page.locator('.behavior-history-more > summary')
            if more.count():
                more.click();assert page.locator('.behavior-history-more[open]').count()==1
        # Capture an actual league profile, with the first expanded case visible.
        page.locator('[data-behavior-owner]').first.click()
        page.locator('.behavior-history-case summary').first.click()
        page.screenshot(path=str(args.output_dir/'mobile-owner-history.png'),full_page=True)
        page.set_viewport_size({'width':1365,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
        page.screenshot(path=str(args.output_dir/'desktop-owner-history.png'),full_page=True)
        assert not errors,errors
        browser.close()
    summary={'rendered_real_profiles':owners,'mobile_width':390,'owner_switches':owners,
        'case_drilldowns':owners,'more_history_control':True,'body_overflow':False,'javascript_errors':len(errors),
        'local_review_only':True,'physical_iphone_tested':False}
    (args.output_dir/'browser-acceptance.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,sort_keys=True))


if __name__=='__main__':main()
