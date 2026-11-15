/* Presentation of returned Decision availability; no valuation or decision rules. */
(function(){
  const labels={intrinsic_value:'long-term Intrinsic trade economics',long_term_franchise_value:'long-term Intrinsic trade economics',market_value:'market economics',market_economics:'market economics',near_term_competitive:'season simulation',roster_impact:'roster impact',largest_single_player_lineup_drop:'lineup resilience',expected_wins:'expected wins',playoff_probability:'playoff odds',championship_probability:'championship odds'};
  window.fsfflTradeEvidenceStatus=function(result){
    const action=result?.disposition?.action||result?.disposition?.disposition||result?.disposition?.shape||'';
    const dimensions=[...(result?.decision_dimensions?.confidence?.missing_dimensions||[]),...(result?.decision_completeness?.missing_authorities||[])];
    const missing=[...new Set([...(result?.disposition?.evidence?.unavailable_metrics||[]),...dimensions].map(key=>labels[key]||String(key).replaceAll('_',' ')))];
    if(result?.package_economics?.status==='incomplete')missing.push('package structure economics');
    const incomplete=!action||action==='insufficient_evidence'||missing.length>0||result?.availability?.final_trade_disposition===false||result?.decision_completeness?.final_disposition_available===false;
    return {incomplete,missing,title:incomplete?'Decision incomplete':'',detail:missing.length?`Missing: ${missing.join(', ')}. Completed results remain available below.`:incomplete?'The response does not include all required Decision evidence. Completed results remain available below.':''};
  };
})();
