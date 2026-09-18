---
name: lra-random-forest
description: Rank LRA portable drafts and search the hierarchical skill tree with a tiny random forest. Use for family→group→skill paths or CALL ptr://skill/port_random_forest / port_skill_tree. Never writes Lean. Lake is the oracle.
---

# LRA random forest + skill tree

- **Yes, we have RF:** `nca_rankers.train_random_forest` / CALL `ptr://skill/port_random_forest`.
- **Hierarchical tree:** `nca_skill_tree.SKILL_TREE` — keep_structure, search_space, rankers, sequence, graph, autoencoder, wraps. Live `decision_tree(tactics)` families merge in.
- **Search:** `search_with_forest` scores every leaf with the forest; returns `ranked_paths` (`family/group/stem`) and `pipeline_bias`. JSON-LD of the tree is stored on `nca.jsonld`.
- CALL `ptr://skill/port_skill_tree` for the catalog search alone.
- Forest score is not a lake admit. Never docker0.
