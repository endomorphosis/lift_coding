# Control-Surface Policy Store

This directory is the default local persistence root for HAO policy bundles.
`hallucinate_app.control_surface_store.PolicyBundleStore` writes deterministic
JSON records under `bundles/`, compiled IR under `compiled/`, artifact sidecars
under `artifacts/`, and user/profile attachment indexes under `profiles/`.
