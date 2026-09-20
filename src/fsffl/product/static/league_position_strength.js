// Phase 3 League now owns league-wide position structure in league_comparison.js.
// Keep this eager-loaded file as a compatibility shim until the shared HTML bundle
// is simplified in a later shell cleanup. Do not append a second League diagnostic.
//
// The shell still guarantees this tiny shim is loaded on every product entry. Use
// that existing eager slot only to attach the lazy Franchise Value Lens assets;
// the lens itself performs no API work until the customer opens its tab.
(function(){
  const version='20260913-intrinsic-dynasty-scale1';
  if(!document.querySelector('link[data-intrinsic-value-experience]')){
    const link=document.createElement('link');link.rel='stylesheet';link.href=`/static/intrinsic_value_experience.css?v=${version}`;link.dataset.intrinsicValueExperience='true';document.head.appendChild(link);
  }
  if(!document.querySelector('script[data-intrinsic-value-experience]')){
    const script=document.createElement('script');script.src=`/static/intrinsic_value_experience.js?v=${version}`;script.defer=true;script.dataset.intrinsicValueExperience='true';document.head.appendChild(script);
  }
})();