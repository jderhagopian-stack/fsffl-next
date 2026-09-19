from pathlib import Path


def test_beta_corrections_observer_is_scoped_to_product_screen() -> None:
    source = Path("src/fsffl/product/static/beta_product_corrections.js").read_text()

    assert "document.querySelector('#screen')" in source
    assert "observer?.observe(root,{childList:true,subtree:true})" in source
    assert "observer?.observe(document.body" not in source
    assert "window.addEventListener('fsffl:product-context-updated',queueRefresh)" in source
