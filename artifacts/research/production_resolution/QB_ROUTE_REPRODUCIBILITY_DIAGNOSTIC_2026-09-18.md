# FSFFL NEXT - Bounded QB-route reproducibility diagnostic

Date: 2026-09-18

Status: **DIAGNOSTIC COMPLETE — FIRST REPRODUCIBLE DIVERGENCE IDENTIFIED; STOP BEFORE GATE A**

Scope: QB A2+C+D reproducibility only. No Gate A board, Gate B/C, Intrinsic/Shapley run, model change, tuning, promotion, main edit, or PR #147 edit.

## Surviving original execution provenance

Original current-player sentinel execution:
- run id: `current-player-sentinel-20260917-01`;
- result commit: `1012215b784bc1e9846378df0f1c9285886da779`;
- parent routing checkpoint: `62f2368864545e89fd9000b067be243714b3ec0a`;
- historical Phase 2 workflow run: `35196266697`;
- Phase 2 workflow head: `cbf723945e5442d654482fcfeb2a53cd7dc4b178`;
- Phase 2 artifact id: `10486530017`;
- Phase 2 ZIP SHA-256: `f7e9cfeee05687d5eb44085124c112c70d812ba95f6d30ca1213c6f92d1ac6ff`;
- Phase 2 panel SHA-256: `c2ebfd365d2828e79afbdc518939f404fa0c45cde57ec6f459abae9bd245c3b7`;
- corrected Q3 age/state rows SHA-256: `9c504c9e765bd113406b59185a3cc80d23cca2401ecf31857692e15720b29063`;
- governing fast-harness Git blob: `6906a11d8fbec7a62bc392b627963a393413a61e`;
- frozen current-I1 facts SHA-256: `dbea7f754e0910a83a85518880a5e3f649579116a205f9d30d8a4c9f39a7932d`;
- durable sentinel JSON SHA-256: `7d3de0c6dd58dcf0e83f744c7ef36e67de2f37a4a98f7d7bb286ad6a56f67f91`.

The original sentinel was a local research execution. No separate durable script, fitted-estimator pickle, coefficient manifest, vectorizer manifest, or Python/sklearn/numpy environment manifest for that local run survives in the repository.

## 1. Historical training-row membership and row order

The reconstruction uses the exact frozen Phase 2 files and the governing fast-harness.

Y2/H1+H2 fit:
- filter: horizons in {1,2}, `source_season + horizon <= 2025`;
- rows: 20,052 total; 2,542 QB;
- canonical reconstructed frame SHA-256: `0def9cfa6ef3ce4bcb748bd1b1784a12866bb112fbdbb393a47dbf5a5462ef38`;
- QB-only frame SHA-256: `578951b38b9e69ec86d601304bdd56ac1d4d627e1e81981d818a79c35d65af69`.

Y3 fit:
- filter: horizon 3, `source_season + 3 <= 2025`;
- rows: 10,026 total; 1,271 QB;
- canonical reconstructed frame SHA-256: `8a005fd12071ba6254be49e4f06e997b1c08d236dce3f9710cbe0540300e02c0`;
- QB-only frame SHA-256: `91b3496ecde22598df50b729ec974ffe26c343d26f50c3dc2a6655de88bc239c`.

No original row-order digest was persisted, so byte-identical original-vs-reconstruction comparison is unavailable. The surviving original provenance names the same Phase 2 artifact, cutoff, and harness; no upstream row-selection discrepancy is evidenced.

## 2. H1/H2 pooling and H3 construction

Surviving governing code mechanically specifies:
- Y2/current horizon 2: fit on pooled historical horizons (1,2);
- Y3/current horizon 3: fit on historical horizon (3) only;
- outcomes must satisfy `source_season + horizon <= 2025`.

This matches the original sentinel artifact's stated cutoff: target outcomes through 2025; source rows through 2022.

No divergence identified here.

## 3. A2/C/D feature values and key ordering

A2 and D construction are recovered directly from the governing harness. The reconstruction's non-QB route reproduces durable sentinel probabilities exactly, providing a control for the common feature machinery.

The **first reproducible QB divergence occurs before vectorization, in the current-player C memory feature `prior_age_state_resid_z`**.

Approved replacement PIT coordinate supplies:
- Aaron Rodgers: `0.12329059927104599`;
- Sam Darnold: `1.245717856456657`.

Those values produce the previously recorded parity failures.

Using the frozen reconstructed fitted model, the durable sentinel logits algebraically imply that the original local sentinel supplied:
- Aaron Rodgers C memory value: `0.1179406059162609`;
- Sam Darnold C memory value: `1.314278044900251`.

These values are **diagnostic inferences from durable outputs, not authorized replacement inputs and not a recovered provenance source**.

Critically, each inferred value is independently identical across Y2 and Y3. Substituting only that one observed C feature value, with every fitted coefficient and every other feature left unchanged, reproduces all six durable routed probabilities for both QBs to floating-point precision.

Examples:

Aaron Rodgers Y2 durable / diagnostic reproduction:
- out `0.33457621892194744`;
- depth durable `0.014410744352984034`, reproduced `0.014410744352984181`;
- usable `0.03826702822663774`;
- starter durable `0.07604567818303547`, reproduced `0.07604567818303606`;
- premium durable `0.1824738580563042`, reproduced `0.18247385805630495`;
- elite durable `0.3542264722590911`, reproduced `0.35422647225908965`.

Sam Darnold Y2 durable / diagnostic reproduction:
- out `0.04805943783398858`;
- depth durable `0.012791269112814705`, reproduced `0.012791269112816606`;
- usable durable `0.01820503562580699`, reproduced `0.018205035625803608`;
- starter durable `0.041044346079081306`, reproduced `0.041044346079082895`;
- premium durable `0.10479698512936639`, reproduced `0.10479698512935634`;
- elite durable `0.7751029262189421`, reproduced `0.7751029262189519`.

Y3 likewise reproduces to approximately 1e-14 or better after changing only the observed C input.

This localizes the discrepancy upstream of DictVectorizer/model fitting: **the lost original current-player C-feature materialization is not the same as the later approved replacement PIT coordinate's C value.**

## 4. DictVectorizer vocabulary/order and matrices

Reconstructed Y2 persistence:
- vocabulary size 53;
- vocabulary SHA-256 `e56a158d9ec017c586a818fea3d25f9106a19ac10e5b4dd5ba5ceda999e99b8d`;
- matrix shape (20052,53);
- CSR digest `dcf38b9f38cdeb4d1cb251b83b690c6f5c63cd43bc9c9013d3cd36391ab4d26a`.

Reconstructed Y2 ordered-state:
- vocabulary size 67;
- vocabulary SHA-256 `378f294409d06c5623a2b08e45f38526757bbc45df2626e23b36d1add0e26630`;
- matrix shape (13355,67);
- CSR digest `c074343456a4b4a89eb9614975571ee7c0c14c8ead7c76b8934a42eb64143acb`.

Reconstructed Y3 persistence:
- vocabulary size 44;
- vocabulary SHA-256 `c559e8c13dea8daa06123edd5b5de7dbab43ca68d4db8aaba409651d9ce8ac97`;
- matrix shape (10026,44);
- CSR digest `b0b6c00962763012a91451e3a64489664fab917b4c1067e32b320cb037a73e8c`.

Reconstructed Y3 ordered-state:
- vocabulary size 58;
- vocabulary SHA-256 `0eb981cc921e1a1f2173ac67d6272a10aa6d0af0e670b203388d647c1c777280`;
- matrix shape (4781,58);
- CSR digest `1f65ebad15892bda53723817ed21147573da0029c097d69665c311005179c835`.

Original vectorizer/matrix digests were not persisted. No evidence of a divergence here; exact downstream reproduction after changing only the current C scalar is inconsistent with vectorizer-order divergence being the operative cause.

## 5. Targets / sample weights

The governing harness passes binary targets directly to sklearn. No sample weights are supplied.

Reconstructed target digests:

Y2:
- persistence `78445c208594bcf7026cc714066804ac4fceff7837d6ad16195d8c38120c0ee2`;
- useful `0a8bb24e7809d9ed17bff7bf10ef997489a1fcc731a03d5b4eff358aa2663580`;
- starter `c35dc2ab67d9785c001bba94c2ed0d122b7ffd335a5cc53b23da1ff0fafc22c9`;
- premium `762a833e19d5cb0d839eb3ffe2af994334655cab8def1cde5e1d2b28101ff8c1`;
- elite `88dcb1f188886714b3936ef6c8c4244ded16c52c8a80a8c5643175e02456f785`.

Y3:
- persistence `899abd7ba5198ef1bf301098c7e16e38939be55f0f7e2eaa92b4f7f53a4fa3b3`;
- useful `1ce0e5672df40f650869bf9d6f69c95699e2e25631aaaebbae3339519b744d45`;
- starter `b4a91a49c60c4ccaf672dccb4e3b67c5bb76a3b448255ad2f6e859235c508771`;
- premium `1db88f237305d0fb8b6acaac6fa5c8d4caf4a3349e2f169c8a545bb4d5a556c4`;
- elite `4393d44ad802fafdc37f9388664377b39fe130daec33c9104550cf5131f50781`.

No divergence identified.

## 6. LogisticRegression constructor

Recovered mechanically from governing blob:
`LogisticRegression(C=0.25, solver="lbfgs", max_iter=2000, random_state=20260915)`.

No other constructor arguments are supplied. No divergence identified.

## 7. Fitted coefficients / intercepts

Original coefficient arrays were not persisted, so byte-for-byte original coefficient comparison is unavailable.

Reconstructed coefficient+intercept SHA-256:

Y2:
- persistence `429c094ea7a11db89feaf4c8e00ee13c955199769c2a58cd7f86a9aa2fc466a6`;
- useful `102628b06d6291193af179d3c03745248710823da93e9955b1d8e6b7e93d41ff`;
- starter `5cf28dbfb3127cb5f8b5ae6f9d5a5bdf2ed0bb9dff2196c169de4e75c52ecd38`;
- premium `a996b8a3dd92dae0295154a70ae07c94ad5f81a05a68fd4c40cb4e16190a7512`;
- elite `a6cc2df6e74c0a8f725ec219ba7adeeb66fb416a27b55616d2f88d25b8a5f976`.

Y3:
- persistence `308bb4a327f5985286416c59c74023a728679c07fd5a7e5e96f7205b5b8e92c9`;
- useful `5be769881300a2ec30d9296c9f6a8fb59ce93ee19bfc146d3ba98ed46296d8b4`;
- starter `f929d3d51b4e671f758474dcc1129031011e11cc246ae6dfc38d1629fe05bb79`;
- premium `6c5f48c833dbfeb54fd32c4def60710756f949eba2d883235bff3332452b972c`;
- elite `626e72fab67c449f0c44269bd2ebde37d22f66d50f33d37a95aefcbfe7c36852`.

Observed evidence strongly supports coefficient equivalence: changing only the current-player C scalar reproduces the durable full probability vectors for Rodgers and Darnold in both horizons to floating-point precision. This is diagnostic evidence, not a substitute for a missing original coefficient digest.

## 8. Runtime versions

Current reconstruction runtime:
- Python 3.13.5;
- scikit-learn 1.8.0;
- NumPy 2.3.5;
- pandas 2.2.3;
- SciPy 1.17.0.

Repository dependency authority only constrains Python >=3.11 and scikit-learn >=1.5,<2. The original local sentinel did not persist an environment/version manifest, so original runtime versions cannot be byte-compared.

Because an upstream input discrepancy has already been identified and changing only that input reproduces the durable QB outputs, this diagnostic does **not** classify the current failure as an execution-environment numerical reproducibility boundary.

## Downstream observation only

With the diagnostically inferred original C scalar and no other change:
- Aaron Rodgers Y2/Y3 full routed probability vectors reproduce the durable sentinel; corresponding durable anticipated points are 116.21815995679677 and 59.60461141796881.
- Sam Darnold Y2/Y3 full routed probability vectors reproduce the durable sentinel; corresponding durable anticipated points are 218.62724656548045 and 194.6045350453237.

These observations are not authorization to use inferred values for any other player or to proceed to Gate A.

## Conclusion / exact boundary

**First reproducible divergence: current-player QB C-memory feature materialization, before vectorization.**

The later replacement PIT coordinate reconstructs 2024 residuals with a documented point-in-time method, but its C values are not the values consumed by the original local sentinel. The original local sentinel's C-feature materialization procedure/source was not persisted sufficiently to derive those values mechanically for the 335-player universe.

The two original C values above can be inferred from the two durable sentinel outputs, but using them as a replacement rule would be reverse-engineering/tuning and is prohibited.

Therefore:
- upstream historical model procedure shows no identified discrepancy;
- the operative discrepancy is **not** currently an environment-only numerical boundary;
- the exact original current-player C materialization cannot yet be mechanically recovered from surviving repository provenance;
- Gate A remains unexecuted;
- Gate B/C remain unexecuted;
- STOP for management review at this C-feature provenance boundary.
