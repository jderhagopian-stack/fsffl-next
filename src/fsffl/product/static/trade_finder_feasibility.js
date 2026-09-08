(function(){
  const labels={
    mutual_gain_candidate:'Both sides show calculated gains',
    counterparty_dominated:'Other team takes a calculated loss',
    mixed:'Mixed bilateral impact',
    neutral:'Near-neutral bilateral impact',
    incomplete:'Decision evidence incomplete'
  };
  const priorLabel=window.oppDecisionLabel;
  const priorDetail=window.oppDecisionDetail;

  window.oppDecisionLabel=function(row){
    if(row?.negotiation_feasibility_evaluated){
      return labels[row.negotiation_feasibility_shape]||'Bilateral impact evaluated';
    }
    return typeof priorLabel==='function'?priorLabel(row):'Not evaluated';
  };

  window.oppDecisionDetail=function(row){
    if(row?.negotiation_feasibility_evaluated){
      const focal=String(row.focal_decision_shape||'unknown').replaceAll('_',' ');
      const other=String(row.counterparty_decision_shape||'unknown').replaceAll('_',' ');
      return `Decision feasibility only — not an acceptance probability. You: ${focal} · Other team: ${other}`;
    }
    return typeof priorDetail==='function'?priorDetail(row):'Outside the current fast Decision-enrichment budget.';
  };
})();
