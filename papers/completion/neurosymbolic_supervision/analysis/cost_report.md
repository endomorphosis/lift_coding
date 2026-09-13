# Separate measured cost scopes

No child/wrapper/gateway/scorer/client or grant-to-terminal intervals are added together. Known sums cover only observed values; missing values and settlement remain unavailable, never zero.

| Clock (seconds) | Known sum | Known / planned | Missing | Mean | p95 |
|---|---:|---:|---:|---:|---:|
| Provider child | 13439.3 | 32 / 32 | 0 | 419.979 | 595.001 |
| HTTP wrapper | 13471.2 | 32 / 32 | 0 | 420.976 | 595.684 |
| Gateway proposal | 13488.6 | 32 / 32 | 0 | 421.517 | 596.163 |
| Gateway score | 83.394 | 16 / 32 | 16 | 5.21212 | 11.6746 |
| Grant to terminal observation | 30754.1 | 32 / 32 | 0 | 961.065 | 1736.17 |
| Client polls wall | 120.006 | 32 / 32 | 0 | 3.75018 | 6.42358 |
| Client polls CPU | 29.2995 | 32 / 32 | 0 | 0.91561 | 1.77727 |

API usage/ticks are observed usage, not settled charges:

- completion_tokens: known sum 7125; observed 16/32, missing 16; settlement unavailable.
- cost_in_usd_ticks: known sum 7.30409e+09; observed 16/32, missing 16; settlement unavailable.
- prompt_tokens: known sum 229853; observed 16/32, missing 16; settlement unavailable.
- total_tokens: known sum 532847; observed 16/32, missing 16; settlement unavailable.

Isolated ablation costs: No isolated ablation measurements; empty datasets do not estimate or zero main/prior/setup costs.

Operator phase records (seconds; every record is copied, with no new total):

These enclosing helper clocks include signing/continuation checks after the signed gateway sampling point. They are separate from all signed/client clocks and introduce no compliance relabeling. Missing phases are neither zero cost nor extra experiments. Links resolve after the reports are adopted at their declared repository paths.

| Cell | Phase | Elapsed host wall | Measured | Missing reason | Exit | Automatic retry | Exact record |
|---|---|---:|---|---|---|---|---|
| 1 | build_offer | 0.06412520899903029 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/a697cac18747530038dc36a1f29b2c221e25155c1949b955c408bbdea8141936) |
| 1 | dispose_failed | 0.25577256898395717 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/31cf97012cc5faadc1cf601a7d6712728f13c9e8a2c6c98e9ebd9625790dac7e) |
| 1 | disposition_template | 0.11984705901704729 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/5f1e71ebfef4c80ef9a2a22c6b1fa0859b4c37d2604f252c050e2d7f6e01b0a2) |
| 1 | execute | 596.1593543239869 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/73d9f3344db613915dac16841fc17c6914b566a87293a4f236309763a8a842bf) |
| 1 | poll_command001 | 0.5055161450291052 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/8def8fb6a81525bf391595d7565dbd71f204cf69c96336775d916cc4ce68a39c) |
| 1 | poll_command002 | 0.5986008460167795 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/13f902de4edead975b7542533618a5972f708d75a833b19da8f6ddc4779bbed8) |
| 1 | prepare | 1.5751926499651745 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/757c922aefa90cd230b6f8606bcc3f2815081c6e6bb3ef578c0cdcb764c527e2) |
| 1 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 1 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 2 | build_offer | 0.046464666025713086 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/e67eaf0b8417406e375dd8ae206a692680b0869c25df19519d6b30788625e0f7) |
| 2 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 2 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 2 | execute | 396.8680444849888 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/a243acefeaf6091f2d6513877775d4e7c455c5b64ac35efb9e1701a5550f3899) |
| 2 | poll_command001 | 0.535099075990729 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/981c01db7002d58cec9388b92c80bb0eb800d23138d963404ecc5921f67793dc) |
| 2 | poll_command002 | 0.5599258519941941 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/dd91907cdbd75e8c5f7bfbcae4478f1edb1cb0c44f091f43aad781ae8cd890ce) |
| 2 | prepare | 1.1897840859601274 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/1e5298229528e138a5a1a27eee38ea35659c9d3fd09979a04e3a33d4d57ee6b3) |
| 2 | review-template | 0.45079904794692993 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/39e20a394caeef082c59c45856f861ea4df47cfa0fb7bce0482caf2fbce331c6) |
| 2 | score | 3.3288096190663055 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/c7f76461bc4c75008765b27eb4b06bf90ce49d8210f26dd04d57ffa79a19989e) |
| 3 | build_offer | 0.04626795602962375 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/48748bf64749a168477f7435cfad4d1827eb3e53dc0c7460f1afd54da89e3f70) |
| 3 | dispose_failed | 0.17839277209714055 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/413e7727d9def9b80f19954d679d2ef5bdb31abcd48a52451e33d86cd6b1d82f) |
| 3 | disposition_template | 0.1383474210742861 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/63a2a8e679d9ab1e560bba2a377cc6dbc6834f7a631bdeceb4e48b24c26055ce) |
| 3 | execute | 428.48058001697063 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/6d968e9ac2b1ccda2238fa14c3a0276f04cdf26b1bbfa4f5d1bc28bee47620bb) |
| 3 | poll_command001 | 0.4841546870302409 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/90b6d07d22c469e058c5cc52397b324ea2279444d33d236643be302f7f296897) |
| 3 | poll_command002 | 0.6742144260788336 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ecca152e06124dac3eaa06c7dc2b29251430b5939a91813580f78bad9990ba56) |
| 3 | prepare | 1.2854994609951973 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/346a3360af5c5d7525ff3c4008314203673738729bef85f6beda0ccb52b07af6) |
| 3 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 3 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 4 | build_offer | 0.05972535000182688 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/c22bc34ac2490c5395a64a969eb634769f9384489b6e6044205f3c10f38c51fc) |
| 4 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 4 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 4 | execute | 552.7205498269759 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/1b48a0d0c8784a24f5ad131aba7dc1b9373f2667b7a8076acda7325ba5714d6b) |
| 4 | poll_command001 | 1.0562379750190303 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/f2799ea4aaaa3845262da83b8660c4a72bb86e7c13eb19b07bad7676ce4628cd) |
| 4 | poll_command002 | 0.5978194229537621 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/a861e4c4544eae5b7fbd90423bee35cd9f44e7718e9e708090aed6cfaf9ef4b7) |
| 4 | prepare | 1.291302375961095 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/e2d1887e15498f2f0158ea4f04d1716079ef7d4c5b69272c05a27cdedd3a5611) |
| 4 | review-template | 0.45733167498838156 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/3f0f63ee2424cb2d4a310d778c997b1eb8012c2403d50471fc5d46944943993c) |
| 4 | score | 3.1427387120202184 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/036a1b6cfff60d840043ba5a01949a6801323b87e96d4da7c3ca39ccde3e92c9) |
| 5 | build_offer | 0.06963330099824816 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ab43f2d4b12c07aa63dbc3c39dc633f1b45b0c9865af057abd77c2b2b68fcd04) |
| 5 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 5 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 5 | execute | 472.8419211289147 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/e44b58322e67e3d5476f837d06ffb7c4a7ce67d75f29daaf987343f6af90ff9a) |
| 5 | poll_command001 | 0.6180578999919817 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/cec308b59c2bb37348603f5aab09f41a8443ff5fa016d56d4e1039c0b1c07839) |
| 5 | poll_command002 | 0.7113301400095224 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/95ce20c1874fc09c21f4b80ac373f12a5eee6fadce41c3c53a1bcda78948b6b7) |
| 5 | prepare | 1.1498963789781556 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/73d7586580637fa4ef659053551c913e3de45c348bf0ed381a4c54b5a713b4bf) |
| 5 | review-template | 0.4845932739553973 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/19a78885909ec0cb4ea98a61cdd33a615d69b1f3823688a114177a13082ec9f5) |
| 5 | score | 2.6661843999754637 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/5b53d3b82edff5a99ccddfc064e327d6b0af19f2083a8d34a63223869ddf0103) |
| 6 | build_offer | 0.0529268360696733 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/6647987e6d204825a70cac425e8b3862ea577bb0460b560c917144d8e8b3900b) |
| 6 | dispose_failed | 0.23067533900029957 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/71d97b4bb47b4bc4a61127533b5fc0a888083f39e790cbb825a698c1954420c7) |
| 6 | disposition_template | 0.1189206870039925 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/fb59244a7d2c0267faae6902a1b848995c459b190501a3bbd816c06281f0dfcc) |
| 6 | execute | 596.1176189859398 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/15ae48eae012b2d8bdc2fa4fd5065435b6f9889838400f39677204b598225fbd) |
| 6 | poll_command001 | 0.6064294840907678 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ea248c0fc8af9902fd001e458b66bac3ea89778c384cffbe647a8b66f6406e9f) |
| 6 | poll_command002 | 0.633795642061159 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/12722d9322f4bebe6f63b3b2bebef7513596e79d29a87b1ad1217331dd7d6cf3) |
| 6 | prepare | 1.1556870270287618 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/bed887f4aae54e36a7c39c1f9b53ba54bf63ced438c2d5161468fda6c3a787bc) |
| 6 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 6 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 7 | build_offer | 0.06484080490190536 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/11c11c4dd1e57a189a067f3cc7550ca1bc59e4b4e68317e1a3bb6f8614dfd6e3) |
| 7 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 7 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 7 | execute | 596.0170160050038 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/5d9ddc6b960e0ebb6861692bac0f32a439f6d130e91b32b60bb70cf1d33b9b96) |
| 7 | poll_command001 | 0.5249649879988283 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/6ecb74d97284d82f6f4b2e766ed483ca54ff49f5cbfd6fff88b78b2f36b53b0b) |
| 7 | poll_command002 | 0.6944069029996172 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/00800a445bede01e8b04794871e29948fc4f7730d5309f44cbeb56d48580a040) |
| 7 | prepare | 1.0899025299586356 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/bcfde3a98d9e52076641287d13b9cf3969c64e2d0bff2c20a89887776459e749) |
| 7 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 7 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 8 | build_offer | 0.09832268499303609 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/e65a33b99525e49a2775494ac0bb7013cfc10f2be4371ea4cd14053214f1dd4e) |
| 8 | dispose_failed | 0.24481116596143693 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ce0c4e298f060fb589e4d46f20447b183a9a51140d60e1562fc825c43cde88bc) |
| 8 | disposition_template | 0.16308022395242006 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/656197d2db523d26d54028c58ee161f7139b441c010cf80e48c3eb50f8ce4004) |
| 8 | execute | 596.6057293900521 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ebe834f9ea19c6198d96fc63c12b6860b9170546abcf78f586845105a1627e03) |
| 8 | poll_command001 | 1.103801965015009 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/f9c35ed04c1c45213257d2d86c39637b655e4e0833323d9ae4789a5717b9918f) |
| 8 | poll_command002 | 1.1436157949501649 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/498085cb59b9b84d17699f11d89c58277d6b48433293a186d66172cf4704a252) |
| 8 | prepare | 1.1636070110835135 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/a42ff3880e0312921ba90460d57e1ab173e853318e8952590997efeac1ad7059) |
| 8 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 8 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 9 | build_offer | 0.08647183002904058 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ffc60d9c1e9d1e411eeecf6bb2aaf41f7862402a0c806f7047ad249b2c0408ac) |
| 9 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 9 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 9 | execute | 83.4227830299642 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/82cb85ca8c00248c695dfccb15783ba0e92648ed73b945eba91472f8a92685f4) |
| 9 | poll_command001 | 1.3084920230321586 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/45c115c66cfb26735dd833802b7fad8173b3380a8e8240d6fef37a95d9836661) |
| 9 | poll_command002 | 1.1672535459510982 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/301260b038c7e9332423a309ddb127f2eafb47ea6b829b6ffaf407fe9ad45b2d) |
| 9 | prepare | 3.1582893980666995 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/2c840d5affbbfb6b1397ab0c9ceedd74076d6f85a3c5ce9c517bb68c31f9efe3) |
| 9 | review-template | 1.425801681005396 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ef69e115ecdaf833a3955d3fde004103a56915cac22be3b48604f7fb3c9067bf) |
| 9 | score | 9.988476132974029 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/7a435733bc558791ccf458d75ee005b61f0c202968cd7c1796e4def1e526ac40) |
| 10 | build_offer | 0.07819861301686615 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/d796be81ff728bd5e9be7f8b935581aaad133ba4e968a20de7a30d4c01c98656) |
| 10 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 10 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 10 | execute | 74.8206427609548 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/d32d00bbfb7620823c66019aaf87d9a2a4c12e3bfdd46273109bd9a0e2929990) |
| 10 | poll_command001 | 1.2663118779892102 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/2590ea4cc182ef5223a7f2cde4e166b7d522ba02e70afa6918832aff4d34c498) |
| 10 | poll_command002 | 1.2281939799431711 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/83cab011605e4bb553425bb1d2d37e4c1f960ffe54c2ef54a279e21bdfca92ed) |
| 10 | prepare | 3.102198963984847 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/c65b1a927a906c737a67b5ed05c17f87fafdd1604efaa673a672257ed4768c29) |
| 10 | review-template | 1.3395887820515782 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/5c6333180ef783fe5e07719e4dccd6560782ab58bf0bf26f1819dff3d3454db7) |
| 10 | score | 9.968679281999357 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/333538f2c8ef9876032262a4b6c0ef88718da2273aa683b818aec47e1a133f4a) |
| 11 | build_offer | 0.09399504004977643 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/35e7cb71687dc892c713333b71c793fd3e5db81610453cb2064fcb977d12d8b5) |
| 11 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 11 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 11 | execute | 68.94098733202554 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/dbe743fddddbbce0be608d48f38a6b2c8a577ee43093c1a193e8c37033fccbd8) |
| 11 | poll_command001 | 1.3105433230521157 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/2f0d5328480e23acad3d7001c6117b71dc74105d2ae54e59b66e20b0ff2c1aaf) |
| 11 | poll_command002 | 1.4880381330149248 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/14f1ab0271a52162142210351bfe64a12cb8234083c6bbdb574d2150a36a0ac3) |
| 11 | prepare | 3.04976631491445 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/6725c931bc233bd9d9e92488335807931ce2e2c44311db9620841ea7048b681a) |
| 11 | review-template | 1.418532792944461 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/98d22aca6d21b0843a25584cc0ef6ffb6f0fd9151e8edd0b350a6be7f98cfe04) |
| 11 | score | 9.92387419193983 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ea08528a9b7fcf3e9ca68554eca40614e8fa32398b19aed28f636d9484f8b005) |
| 12 | build_offer | 0.0899230120703578 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/5310e8accf1c9802736a1be37fb733f618157463a8f95f6541dd03f49b176d16) |
| 12 | dispose_failed | 0.2486996940569952 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/2f79629688ffcf6fbc123d3d4a9e17d284a9d30beae586ccd2581d156b72929b) |
| 12 | disposition_template | 0.1582004049560055 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/244d4dbe431fac12dfaba4698e6c66c2a3da2004d67d91f153e74aa0d8eda7cf) |
| 12 | execute | 23.311173244030215 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ada0c2e5c1c94f219f5717d96b291e4ef3666bd068d1e4f4690b6c6de4c607bb) |
| 12 | poll_command001 | 1.3207326949341223 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/05be2419d9dbd6cd290ab604fa5b302cd1ab2416efd94fde38b7905d611b37cb) |
| 12 | poll_command002 | 1.535600321018137 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/b147586964b2b5973791727372355cc53ec3a51e23cc822b42398d2afbda1761) |
| 12 | prepare | 3.0653170209843665 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/3942a744942ad41786aef5d5222b3c59826dd795a55310b7828cbb23d69c2da5) |
| 12 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 12 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 13 | build_offer | 0.09986526099964976 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/63455497d35b58963d13db5365d5bc76c5c67b87494cb83dc2847c18f5b4ae8c) |
| 13 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 13 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 13 | execute | 156.66649403003976 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/13d03999e81be94b005727dd47dc1918376a13148f097f5701f6c3953747af12) |
| 13 | poll_command001 | 1.6594342299504206 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/7a30d48d485876b8313c373cf9a735817dde01f7ee98e7024bbc2d2194333b75) |
| 13 | poll_command002 | 6.562949136015959 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/f2143e9cf982db47f4f79c96e25865f4c9f37ce4c669d21252ea40c25c36ac7c) |
| 13 | prepare | 1.3006287689786404 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/1b242f720e62cc973caf753750ce03dfc55659c9988adeadb230c2200542f5b4) |
| 13 | review-template | 0.583861124003306 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/4028b53b00e4d4eede5e3946b51c1fd65be2ed9648ca3bd4fc968278182c2ba8) |
| 13 | score | 12.3450664159609 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/23b87cfe638eebc3932fc853ffcd95e9f76f4e736f1e9a6144533fe89d9e368a) |
| 14 | build_offer | 0.11899959901347756 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/4abaed7271b0c0d5d129f8cffbab35e4366e81ec454fc249ac0688665fc4455e) |
| 14 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 14 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 14 | execute | 199.90514711698052 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/1b89af732715fc10f455001b3a1feb6fe8e8fb702eb5d0367a15cc404424f29f) |
| 14 | poll_command001 | 2.219257591990754 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/441823d350ccb9cc74b6bfd5f5957b1cc4ef4b3a5ea4cf5508ba45101a23c23a) |
| 14 | poll_command002 | 1.8350434900494292 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/a3ff642d754aac809fa8e2e1d2db47a011c9d339180e5ad88305d7ad91d034d5) |
| 14 | prepare | 1.8071965250419453 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/1e2473c1dae5cb136292dadb8d4c43a718ea1441407ef49f8937a0ae87538850) |
| 14 | review-template | 0.3405097509967163 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/e141054af6444fcc8eef0c7234d216c1b969b6b7e3a2466eb1f01018572c7a51) |
| 14 | score | 11.636377972085029 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/170fe55d7f063297d2b9c2b13e7296ee5deb0e1332a7826e6e7215e27f10738b) |
| 15 | build_offer | 0.0744100830052048 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/3fe5371f854a7d6851281b8d0967f46520e335f6c45a90bb1aea4c50d03c7b3e) |
| 15 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 15 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 15 | execute | 168.44988614006434 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/16c4673f01002c858d344b5ead0d4e9d21e55e63a69ee7e76f776a80c6e8fa91) |
| 15 | poll_command001 | 1.6394452740205452 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/74ac458e39a7de0045de34d886ac3098629bcf6b034bd7bdbec0f73006782412) |
| 15 | poll_command002 | 1.5613228359725326 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/be9fcd65be1be18d0f6e78e694f251069d60229df10cf291591e59920b6c6c95) |
| 15 | prepare | 1.1165788769721985 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/aa7ad93cacc8f218cd7620463b1b555c72096073d121f8f790146fe3bc90c1df) |
| 15 | review-template | 0.33610799291636795 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/c0212a9e58a1aa14a43899fde502f1d0d36d99be20fb98375ab803739c1b2626) |
| 15 | score | 11.812370158964768 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/34019bd2899c025b6520ebe84d162eea7de9db5d877603f7df26734e31121123) |
| 16 | build_offer | 0.0918249919777736 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/18a3be7734ccb6523acfa18f1f3541fd2fb1620ac4ecd0f10b5131638106fb27) |
| 16 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 16 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 16 | execute | 161.55926515697502 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/7b5d3697bf20378cdcd38847247ce77ec08d92db4f34915892939ccf0e677d24) |
| 16 | poll_command001 | 1.901210249052383 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/89f2aa544b511a2f8ca2e1f4494d33e83c59a97e5a389b5ea9bd726553103444) |
| 16 | poll_command002 | 2.0036092940717936 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/7a9ca7fc6224ee9778090267f3220680a0c1d30696e627d187f089dc52bc1d13) |
| 16 | prepare | 1.1555006039561704 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/6eb6eafbdb9e71a71d95b5efd70c9cc90721fbfab1d38dabe2e45c7df69e49eb) |
| 16 | review-template | 0.39635494095273316 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/f5f4685252bee094cbfe458835e9ec7e10f91ebc85d2d8da9267a9862fb417e9) |
| 16 | score | 12.389338636072353 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/2e2fa7c91027d29fa3429fda65dcdf7f791b374a67bf63ead0e34251f14f8590) |
| 17 | build_offer | 0.09455196396447718 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/9c1c97a475992973d20f5c006f070c311b6492393182b189695e4f7f16d8ad37) |
| 17 | dispose_failed | 0.32563652202952653 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/01f10b3f93c1c58b8c508b864c4c84eb2f9b56e47438adf0e2d0bc3dfa3b785f) |
| 17 | disposition_template | 0.15115214209072292 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/b45c91e6542ec0eb2d4d74b22210022c0b7623107d65391688fdca18c4a1de81) |
| 17 | execute | 596.0653368360363 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/8af4956b2b4c6ec0361e4da68d3fe6745c997b13976b94efc414fa9158c39bc3) |
| 17 | poll_command001 | 1.717424600967206 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/99441bb79d05c73f700ff86f508d10f4dc98c7077b14ce2939d4f6fd1c956425) |
| 17 | poll_command002 | 2.002888720948249 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/cb9ac7a4e225bf3dc05228cc0412abc3129990b1e974f3fbac897c66ac988ec3) |
| 17 | prepare | 1.6356313090072945 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/4da41e9d5f79ac8b49ab295153d27ff4061490f2ce164dab3cbb0e800d356e6c) |
| 17 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 17 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 18 | build_offer | 0.08277503796853125 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/02c2c6c90a1504c4489845b18e4adf32b4dd7450b98f95217144eda1dc74dd27) |
| 18 | dispose_failed | 0.2258080110186711 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/60916ed3fb833f7adc2d8d0d3ca172a108ea1351996c14c5325061e770b920f7) |
| 18 | disposition_template | 0.1519714220194146 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/153c9b9d39f0089d8ac0ea4e7b75588012f0b78d7f56551fddef0746d8baf2be) |
| 18 | execute | 596.0603626499651 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/1e4c6788ecef3b8d02f05a6202b33e4bc1a18d8645ce11d886b18938dae6df90) |
| 18 | poll_command001 | 1.841360617079772 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/7cdff4a103cd24482e1a8f103c1a9150e7e8bfe7a5befe41ac3e47d0e90739cf) |
| 18 | poll_command002 | 2.11094610998407 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/3d1236870828703e5b8de707edd6a1a4dbd39dfc4bf84279e5124d4e0a934360) |
| 18 | prepare | 1.4338310619350523 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/2a358d1487d5614b6b8af29bc46948cd73962cb0fd201bba9873e71b23c5d40e) |
| 18 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 18 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 19 | build_offer | 0.08033785491716117 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/23164591a3045ffada58c0cd7bf7abc9b826d73c753aa82ca470e9f840526bce) |
| 19 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 19 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 19 | execute | 469.48354796192143 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ee6b9e3413e1be9523984a143a9a7c535c0bead1086de125ceae5403c9d907bb) |
| 19 | poll_command001 | 2.071054885047488 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/0a7f6d07409c4a98bee58cc6f2d4a801ae5bd5008c74053d22f71a44d200a6fd) |
| 19 | poll_command002 | 2.0289182610576972 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/8dda914752defad5c2d5b89b1fde9404ed503fc1923f1d5f0913a05f98ea0ed3) |
| 19 | prepare | 1.4090117230080068 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/1f5f05dcfaaee43454c74a10665d8cbf5849d388074751da3dcdf6e8c320ebb1) |
| 19 | review-template | 0.6108370870351791 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/83f09d61fd61fc6256671106b16e0e854e3d3c3e8228bcde8ca7a5ddf6727dc7) |
| 19 | score | 3.690534883993678 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/407a73df868eb81254bd6849f0823612a19fb922217d05ef0642a7329282140e) |
| 20 | build_offer | 0.0764921170193702 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/78e9813a053075f922a936260ea3b867fe3e67d1750da81a16d5331e212fd985) |
| 20 | dispose_failed | 0.2819547450635582 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/2155f5059d34abb5457c6a829ddd60f1982bcdabf0c15aecc56af813eeb357ec) |
| 20 | disposition_template | 0.14407939498778433 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/d69bf206a100857b071b15f328cf87b93a5c83f220dc40d976a844d28577d33b) |
| 20 | execute | 596.258577013039 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/e456c9780f3c1a86a73b3529bbf68a3797696bf122c13d788153642bf91e7194) |
| 20 | poll_command001 | 1.9290634240023792 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/158a983ffd0aad82ee6823c0ce81dc5fba591c8876590e9bc80448075e946ede) |
| 20 | poll_command002 | 2.3329942059936 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/c67a745cbdf7cb3a04ae26b6b96429a3ae08ab96275d9e1b16ea1b8f991f3410) |
| 20 | prepare | 1.4229128619190305 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/de590b46fc8ab9cf59072d3abe91adffdeae694bc0d65a59188a4cfd7de61401) |
| 20 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 20 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 21 | build_offer | 0.08176276402082294 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/dab1cc8589c1797736ee59cca0b74a68bf122a7d0044983303c5fb3f25558d17) |
| 21 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 21 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 21 | execute | 349.0645576650277 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/e629a661c514a5636a70f01c4730b36292e69b51232ab7bcc7c7cfbe8d96cca9) |
| 21 | poll_command001 | 2.2320407379884273 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/53df8cdde95a3950bbbb5b32985903cd367607491c92a3bc83e7803cd2e73da5) |
| 21 | poll_command002 | 2.5854713389417157 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/f39b642de8b537ffe08f619196d919c623f1035a9e6e077a326958936492ffeb) |
| 21 | prepare | 0.7800484319450334 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/2da05b281cc1428d4a1c9cb2bfb75f7f60091c79fe9ccc097092b7843549bba0) |
| 21 | review-template | 0.2220982030266896 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/6cb57e13293443ba10d7729e62887e6676bb3c14275b1217b4029a075f64526e) |
| 21 | score | 1.5258059630868956 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/884a6fd09e864b8debe2c0476e734587638d657c2db5251070a14d134e62e90a) |
| 22 | build_offer | 0.06974114698823541 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/aeb6251c75a8a5c1bdf89fb2ff6a7fef8618d99eadb4e238bf25a5859f44e1e7) |
| 22 | dispose_failed | 0.2823745448840782 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/8953356a264b17a51d1c0f7e2d8ea3523fabb006b847ec06379b4003e9003835) |
| 22 | disposition_template | 0.1296145060332492 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/8fe013539f7bae59c5747a644c6009319e5f78dc4a33b8840a92fd48848c6579) |
| 22 | execute | 597.1276312700938 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/43d20e5392a2c89e71e0be1ffb97c740f216c03732dc482215833212eee31aa8) |
| 22 | poll_command001 | 2.343644098029472 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/699623be4f3989884656c59f928d9c11052b23b8d0c52f13aa695dd7ca43c9c3) |
| 22 | poll_command002 | 2.4398153520887718 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/c0f373deae8d321fde9751f1ebdc07479f68615fad73679bd6a3a247dc306200) |
| 22 | prepare | 0.8034508019918576 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/8eb4f18285f7d1bedd2acb2b950166a51f3e82c8b32bb492e8c13a7e93f73d57) |
| 22 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 22 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 23 | build_offer | 0.08088145207148045 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/bf98101c1e504deeb0714c5e5b46b3f5e999004c13b9873266884d375d06576c) |
| 23 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 23 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 23 | execute | 475.9019683160586 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/06e284120065c70b7d1f4a13c40799bc5c61ce61b57e61494864dcd7a7f36bf7) |
| 23 | poll_command001 | 2.2317587840370834 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/edbf2453caf0a07f567a6ebd32386ac5e8320432ec7bb3f72bf5e53439c30db4) |
| 23 | poll_command002 | 2.6633004340110347 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/3f4f0f51312ceaa89c4642cbc610b2d52bd7f69d614c15d80679eba36ba91eff) |
| 23 | prepare | 0.8573387250071391 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/9515d71e3bff15b2d5a0102d1bfb1ae92cf16f2191b18601152b9982fc818c15) |
| 23 | review-template | 0.2287462380481884 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/bb2146342432177ca08040e8a6fe082eaef1017a340fe6209b721cfdc8a8339b) |
| 23 | score | 1.4958589280722663 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/69c12a29cc4c5f3726ff2badd9e1a502cf26a20c0335368e1de8831baa71b7a7) |
| 24 | build_offer | 0.10694838408380747 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/693c435baeccfe8036c8388792de86372165e64bb4c9f8f126529d078721543c) |
| 24 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 24 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 24 | execute | 380.4461986729875 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/d44b5cd59eef00cd3de615beb16c693eca76f735464c6f447bff6eb2d72db6e7) |
| 24 | poll_command001 | 2.500094239017926 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/7943aa195fadfa084a02e1fd8482d010bb220222e6a07686d6174ed8e016e6ab) |
| 24 | poll_command002 | 2.3486314020119607 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/12cd09df28e82cb964e29a65e079bfcc6baf37470d3165d606b30176af5e8f7b) |
| 24 | prepare | 0.840495445067063 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/6994100a9b7ca6946dd940083ce1831fb074f40aeb133007ed122c94f928b1ac) |
| 24 | review-template | 0.20477628603111953 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/8dfbec670a896509764ff63fce3d89a633dca2303a349a42ba4e797c32b2c427) |
| 24 | score | 1.4742855259682983 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/a839bf23d8a7f69708bb4c716ca801cd97b5c5d6f63b473ac7c77d5b9d3b3c8f) |
| 25 | build_offer | 0.09224025392904878 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/785407427a42e1ddef855b50bad543230b1c8cf2cb646b0632d0b71c584dc653) |
| 25 | dispose_failed | 0.2719164959853515 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/bdc7f13a8e2686f69d739895493c1cf65ab68ab1e8652ebf7ef575784c5f93a0) |
| 25 | disposition_template | 0.12727603502571583 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/fb74be5afc8a35668c7899a3fcc5e954447d864da48eef2aa515bed09d278d5c) |
| 25 | execute | 596.0903405890567 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/8938846a5342ac42e1199711c3c2a2283cb56eab9f72e5018dab7f9438389571) |
| 25 | poll_command001 | 2.5568885809043422 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/1641e8c4ea27891bccffdf2d33d53762209ee69e80b30c2e3dc958c8de390e03) |
| 25 | poll_command002 | 2.5994751469697803 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/bb68feabf282dc56b708d29a5aa9a8d4a06cd5d523c567df5ab9ed3c89947392) |
| 25 | prepare | 1.0844548030290753 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/9d62fda761afa9f7ec7ace584edac457e03b5da7bdbd44271623366a8e1ee353) |
| 25 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 25 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 26 | build_offer | 0.06637181807309389 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/25ecea6c97e8ed890312ecc2b49eb12e86aad030f85f5a53a31bc2ba2930a428) |
| 26 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 26 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 26 | execute | 461.708428747952 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/74e1f1635a150407bd154b4b993703afd48f89bb6e80fa361611e4326c3d20ce) |
| 26 | poll_command001 | 2.656826955964789 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/21511e37a32348c29853cf3a7605caff726e2d6a7e0685557d64c1adcd670040) |
| 26 | poll_command002 | 2.9734343830496073 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/85bad681eabf442852bee5a8651f41baf1052445488694eee13d651dc35042a2) |
| 26 | prepare | 1.1581156289903447 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/f022a15a1d302f23b1b2a9f43d3d9a20ac77f03a4ef6778abea27dc44be7cd98) |
| 26 | review-template | 0.3762773219496012 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/dca1d5a88e855e0b535830480506fb7a4836472ac557837d0c580e5eb53c2017) |
| 26 | score | 2.776044722995721 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/8c75c63180228ec2467f431755e31a1fd7a1524069a2e29258bf3820d6f863d4) |
| 27 | build_offer | 0.08751848398242146 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/1522aa20d013c154201f4d5173c8f47b75dc1faf6be947d37e8674f0dcd7b1ee) |
| 27 | dispose_failed | 0.24799332593102008 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/3a15608e18b70cb8ffbb6a8a83b1840271af5e1ea5b2ea89e741197cb3bad414) |
| 27 | disposition_template | 0.133794563007541 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/d40456403826c54d9fac3db2ecbd191b9f7c8ad439c2e3a0c9b4a383deb71e90) |
| 27 | execute | 596.1872030230006 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/5c71ac2497ae60c2e3e33f34cda60b93dddf229fae1de924ac7ddbd08e9c9d0e) |
| 27 | poll_command001 | 2.921818475937471 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/8dbf8efd985b2316b03db8a341bc8811dd808f0694e8f7d0630b89fe61a0a990) |
| 27 | poll_command002 | 2.689802346052602 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/323d3032ac3ef83dec07a6d6b2956db2561717d19dcd84380b7096291b49127b) |
| 27 | prepare | 1.1178518669912592 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/0da6a21ec69068736572e21eb63b400bfc47be4c99d6dea99ee26cd41f070eba) |
| 27 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 27 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 28 | build_offer | 0.12189094698987901 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/0f4441221a00e9fd4473c1458ecd452b536b5da3b167fd081911e2c16660e020) |
| 28 | dispose_failed | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 28 | disposition_template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 28 | execute | 227.61510503699537 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/6adc3384ce8d244977a37ea3a6712986d4f49b5260558247b7946aa40f87765f) |
| 28 | poll_command001 | 2.7433775139506906 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/6dd28e75c813c0a11fd3a084aeb820558abdf46a048ca3ee7706b5106da653a1) |
| 28 | poll_command002 | 3.0102575580822304 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/dd73c7045ecae73bd0602397bb50dc6c87df08cd9732f840ed190bca1b827df2) |
| 28 | prepare | 1.0339693080168217 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/182068244a7aeb7c640d17613eb550e63020f5c5929269c18d321d5f7974284d) |
| 28 | review-template | 0.34437210601754487 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/77016189c424cfef3fff5cabd42251a5103e7118ee88863d31a662f612969d10) |
| 28 | score | 2.653516892925836 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/b3cb843cb261b510cb0ee49c9861ff0b6cf3ce28640213776764cf9c6a50e6a2) |
| 29 | build_offer | 0.06704577908385545 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ef2bcf55501bc9cca1f6c144278296c58799c59534c3b99da8df20bd3124cd79) |
| 29 | dispose_failed | 0.27822817710693926 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/e3c6da54b878b9d46d33551e576163165442201e4bb198a9cd42279e5213d1e9) |
| 29 | disposition_template | 0.14374991599470377 | True | unavailable | 1 | False | [retained record](../qualification/operator_inputs/NS-017/objects/39acdb5f51a598d1141d132e376214f0fbf995148ba474fe308721147656734f) |
| 29 | execute | 596.2374480318977 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/e3287f3c63e1ea10dfeda06d1d256bf5de0b7e7760200e92aae8c1e3d90c40c2) |
| 29 | poll_command001 | 2.6981242219917476 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/b7ce954fd4ef81cdb289fae5d482b699ff281fad7f30ebd92089f92832687a0f) |
| 29 | poll_command002 | 3.3452991630183533 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/ed0a93060ea37f2b14e28f953b6603184b98b400970a83b46a57f31ebf660c35) |
| 29 | prepare | 1.494429757934995 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/f1fed1496083728ff30fb297007951baac583f320a3e52ecbb251462bbf316a5) |
| 29 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 29 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 30 | build_offer | 0.09063784498721361 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/9ad6d1ffd962c1fbd0e17deb2bf4a2f4dc2791bbada17113a289ba65950d5147) |
| 30 | dispose_failed | 0.24275600200053304 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/6832b4c473e3cd737ae863d7b36e83a08dc94f8747dfb7458ac6a84a3c641cdf) |
| 30 | disposition_template | 0.14692246005870402 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/b4a255c66579979578c667977292d16a20868858d053d85bca493a133047299e) |
| 30 | execute | 596.2503815849777 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/21a390d9947fadaa5386034e94f12ad0e5fa627677a02c95abaea7760dd0481a) |
| 30 | poll_command001 | 3.0401725448900834 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/79919192081108a419b50af09bf571f39dd5c445f8927da64519c2564f02c90a) |
| 30 | poll_command002 | 3.2223019240191206 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/2c43ccfb74fafb04cd9baae65650351380c654aa4c744324641d44df3f100171) |
| 30 | prepare | 1.6892633140087128 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/6c7087e768e33e078907083ab0b5291a76cc11f92e09946a63dd644dd3254aed) |
| 30 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 30 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 31 | build_offer | 0.07016602798830718 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/b6c830693cf897da0cad17e918e772b27e449506c3efb693cf3e36ee5797cf52) |
| 31 | dispose_failed | 0.2564419220434502 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/f5e73e5dd243e1310f080cf66c03f5377415d231781c972cc2f41101915059ea) |
| 31 | disposition_template | 0.14441026898566633 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/41fe3b52be21bf51b5a1fe9157c4502bc255997882e8dc7888240376268736fe) |
| 31 | execute | 596.4489073979203 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/59c27c29a199eab44e043e36097bfb77523eba98b767c4674ed378b7e0290235) |
| 31 | poll_command001 | 3.109725586953573 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/475afc4fd3723e4f7b13eed0eb6ce6a8df1ad11a51e940ebb07748343e748efc) |
| 31 | poll_command002 | 3.4510553299915045 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/c9863aa081e1b4f1ade54919c1a1513d9f976f8d78686f8ef04bc7d5d7fa6f44) |
| 31 | prepare | 1.6032963710604236 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/22eb1288c6f2e5497d1410470ce27837074ad9b878ef2c5d5612d25d48cf788f) |
| 31 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 31 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 32 | build_offer | 0.08899131801445037 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/a2e97a6231261f8af56dde28aa564d298fcc0eaad73f256417d978c8c34c8d6b) |
| 32 | dispose_failed | 0.29659855004865676 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/bf1784bdff6ea7514cdbc65db3052bdd3e9332a48e6605884f02abe8412934a2) |
| 32 | disposition_template | 0.19011406099889427 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/f9c8bec3e88c8d696f1b5acec6676bd958b4d93be42a1bc01e1f8eff4d5348b5) |
| 32 | execute | 596.2412246259628 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/db061fa41f03e0abac7179471fa2ef8933fc1b00a1b6084a2b4566e0adc4a738) |
| 32 | poll_command001 | 3.203550406033173 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/d30a51c0fd8a2129ce6a81d4072ebd2b37e9fabf804787d1ddc0916481cbbab6) |
| 32 | poll_command002 | 3.3341133119538426 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/fa794bf26da547b5f59889a8f1e01f9222928b9496ba2333bbadd4d9cc0a8757) |
| 32 | prepare | 1.650183329009451 | True | unavailable | 0 | False | [retained record](../qualification/operator_inputs/NS-017/objects/85ba357a55a23c3f04a605406029a4ed06c265737a2aa7ea2027665c0128af4b) |
| 32 | review-template | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |
| 32 | score | unavailable | False | No retained invocation record observed for this phase; no zero cost or extra trial inferred. | unavailable | unavailable | unavailable |

Previously reported preparation/protocol/lease costs, copied within their original scopes:

This view copies the installed prior component, whose six original-ledger hashes match the strict analysis. Its known sums are partial measurements, not complete experiment costs. An empty observed sum of zero is retained in the source JSON but displayed as unavailable when no record was observed. No sums, maxima, or estimates are newly calculated here.

| Scope | Clock / units in field name | Retained statistic | Recorded value | Observed | Unknown |
|---|---|---|---:|---:|---:|
| final_metadata_staging | cpu_seconds | known_sum | unavailable | 0 | 2 |
| final_metadata_staging | host_wall_seconds | known_sum | 14.24558069894556 | 2 | 0 |
| final_public_baseline_current32 | cgroup_cpu_seconds_lower_bound | known_sum | 8.616261 | 8 | 0 |
| final_public_baseline_current32 | cgroup_peak_memory_bytes_lower_bound | maximum_observed | 79372288 | 8 | 0 |
| final_public_baseline_current32 | child_elapsed_seconds | known_sum | 10.158299655886367 | 8 | 0 |
| final_public_baseline_current32 | host_attach_wall_seconds | known_sum | 11.953597140032798 | 8 | 0 |
| final_public_baseline_current32 | host_cleanup_wall_seconds | known_sum | 0.16775067627895623 | 8 | 0 |
| final_public_baseline_historical128 | cpu_seconds | known_sum | unavailable | 0 | 16 |
| final_public_baseline_historical128 | host_timestamp_interval_seconds | known_sum | 17.458237 | 16 | 0 |
| final_public_baseline_historical128 | memory_bytes | maximum_observed | unavailable | 0 | 16 |
| final_public_baseline_new128 | cgroup_cpu_seconds_lower_bound | known_sum | 9.162806 | 1 | 0 |
| final_public_baseline_new128 | cgroup_peak_memory_bytes_lower_bound | maximum_observed | 213852160 | 1 | 0 |
| final_public_baseline_new128 | child_elapsed_seconds | known_sum | 9.833202279987745 | 1 | 0 |
| final_public_baseline_new128 | host_attach_wall_seconds | known_sum | 10.036315820063464 | 1 | 0 |
| final_public_baseline_new128 | host_cleanup_wall_seconds | known_sum | 0.025645407964475453 | 1 | 0 |
| final_shared_native_preparation | child_cpu_seconds | known_sum | 339.83170864 | 11 | 0 |
| final_shared_native_preparation | child_wall_seconds | known_sum | 340.96053276292514 | 11 | 0 |
| final_shared_native_preparation | host_wall_seconds | known_sum | 346.68547677702736 | 11 | 0 |
| original_lease_lifecycle | cpu_seconds | known_sum | unavailable | 0 | 1 |
| original_lease_lifecycle | timestamp_occupancy_seconds | known_sum | 5922.720917 | 1 | 0 |
| pilot_public_baseline_historical128 | cpu_seconds | known_sum | unavailable | 0 | 8 |
| pilot_public_baseline_historical128 | host_timestamp_interval_seconds | known_sum | 5.375222999999999 | 8 | 0 |
| pilot_public_baseline_historical128 | memory_bytes | maximum_observed | unavailable | 0 | 8 |
| pilot_shared_native_preparation | cpu_seconds | known_sum | unavailable | 0 | 26 |
| pilot_shared_native_preparation | host_timestamp_interval_seconds | known_sum | 1758.9971320000002 | 26 | 0 |
| prior_protocol_v1 | gateway_proposal_seconds | known_sum | 185.10169843002222 | 3 | 0 |
| prior_protocol_v1 | http_wrapper_seconds | known_sum | 184.1373595170444 | 3 | 0 |
| prior_protocol_v1 | provider_child_seconds | known_sum | 182.49902199499775 | 3 | 0 |
| prior_protocol_v1 | provider_cpu_seconds | known_sum | unavailable | 0 | 3 |
| prior_protocol_v1 | settled_provider_cost | known_sum | unavailable | 0 | 3 |
| prior_protocol_v2 | gateway_proposal_seconds | known_sum | 383.8281252851011 | 3 | 0 |
| prior_protocol_v2 | http_wrapper_seconds | known_sum | 382.8552486639237 | 3 | 0 |
| prior_protocol_v2 | provider_child_seconds | known_sum | 20.350152658997104 | 1 | 2 |
| prior_protocol_v2 | provider_cpu_seconds | known_sum | unavailable | 0 | 3 |
| prior_protocol_v2 | settled_provider_cost | known_sum | unavailable | 0 | 3 |
| prior_terminal_client_verification | child_cpu_seconds | known_sum | 0.259281968 | 6 | 0 |
| prior_terminal_client_verification | child_wall_seconds | known_sum | 0.6116067499388009 | 6 | 0 |
| prior_terminal_client_verification | host_wall_seconds | known_sum | 3.0928884730674326 | 6 | 0 |
| separate_constructed_generation_diagnostic | cpu_seconds | known_sum | unavailable | 0 | 1 |
| separate_constructed_generation_diagnostic | enclosing_wall_seconds | known_sum | 9.367797 | 1 | 0 |
| separate_constructed_generation_diagnostic | nested_http_seconds | known_sum | 8.700476 | 1 | 0 |
| separate_constructed_generation_diagnostic | settled_provider_cost | known_sum | unavailable | 0 | 1 |
| successor_lease_launcher | holder_cpu_seconds | known_sum | unavailable | 0 | 1 |
| successor_lease_launcher | launcher_wall_seconds | known_sum | 0.33431415795348585 | 1 | 0 |
| v2_metadata_enclosing_installation_seconds | cpu_seconds | known_sum | unavailable | 0 | 1 |
| v2_metadata_enclosing_installation_seconds | wall_seconds | known_sum | 38.994561052066274 | 1 | 0 |
| v2_metadata_final_payload_qualification_seconds | cpu_seconds | known_sum | unavailable | 0 | 1 |
| v2_metadata_final_payload_qualification_seconds | wall_seconds | known_sum | 4.125144817051478 | 1 | 0 |
| v2_metadata_initial_payload_qualification_seconds | cpu_seconds | known_sum | unavailable | 0 | 1 |
| v2_metadata_initial_payload_qualification_seconds | wall_seconds | known_sum | 5.615407229983248 | 1 | 0 |
| v2_metadata_installed_eight_request_comparison_seconds | cpu_seconds | known_sum | unavailable | 0 | 1 |
| v2_metadata_installed_eight_request_comparison_seconds | wall_seconds | known_sum | 1.9719368040096015 | 1 | 0 |
| v2_metadata_installed_metadata_builder_seconds | cpu_seconds | known_sum | unavailable | 0 | 1 |
| v2_metadata_installed_metadata_builder_seconds | wall_seconds | known_sum | 38.86050887696911 | 1 | 0 |
| v2_metadata_staged_metadata_builder_seconds | cpu_seconds | known_sum | unavailable | 0 | 1 |
| v2_metadata_staged_metadata_builder_seconds | wall_seconds | known_sum | 37.706350081949495 | 1 | 0 |

Prior pilot (separate 24-cell developmental cohort; never pooled with final32):

- gateway_proposal_elapsed_sum_seconds: 10867.81474797998.
- gateway_score_elapsed_known_sum_seconds: 196.39898603782058.
- completion_tokens: retained known sum 3246; observed 14 / 24. These are usage/ticks, not settled charges.
- cost_in_usd_ticks: retained known sum 7832954000; observed 14 / 24. These are usage/ticks, not settled charges.
- prompt_tokens: retained known sum 228310; observed 14 / 24. These are usage/ticks, not settled charges.
- total_tokens: retained known sum 537711; observed 14 / 24. These are usage/ticks, not settled charges.

The pilot timing deviations remain unchanged; this is not retrospective final-policy reclassification. Read the linked timing disclosure for its recorded thresholds and counts.

- [coverage.json](../writing_inputs/ns024_prior_evidence_v1/component/coverage.json), SHA256 `fd21b5d85e2de2f7c685066417adb6e60ec5d1b016905a400f14dc73597eafed`.
- [costs/summary.json](../writing_inputs/ns024_prior_evidence_v1/component/costs/summary.json), SHA256 `2ad7f9342948b27094d0654c0da3a72dc59612a88c8fa1e0318da25115d703e7`.
- [costs/records.jsonl](../writing_inputs/ns024_prior_evidence_v1/component/costs/records.jsonl), SHA256 `32cae9fabe186fa513e3c6248f6aad392892791e72bf9f1a587b6e966ed02369`.
- [pilot/summary.json](../writing_inputs/ns024_prior_evidence_v1/component/pilot/summary.json), SHA256 `653749107e4ca5e9007dde5038595f79b3ab1d694bd22120d3a371819a45bb8b`.
- [pilot/adopted_costs.jsonl](../writing_inputs/ns024_prior_evidence_v1/component/pilot/adopted_costs.jsonl), SHA256 `b4ec79ac6ff315f849fbe58183715f30046cb64b5f0496420c33294d7b250685`.
- [pilot/timing_disclosure.json](../writing_inputs/ns024_prior_evidence_v1/component/pilot/timing_disclosure.json), SHA256 `b9c3dcc4fe87deec92db8ee718172eab9d4132de7e01fd4c850531963a0a6b10`.
- [pilot/table.md](../writing_inputs/ns024_prior_evidence_v1/component/pilot/table.md), SHA256 `79c09d44877523d6b944d8174ea50c299512779c82330f3d3a12fe1e234d1024`.

Retained coverage limitations:

- Settled provider charges absent; observed API ticks are not settlement.
- Prior interrupted preparation CPU and complete original preparation CPU are unavailable in the admitted metadata.
- V2 timeout child CPU/duration and remote effects remain unknown where no child result exists.
- Historical baseline CPU/memory unavailable; timestamps yield stage wall intervals only.
- All operator polls, source qualification, authoring, human/AI review, network diagnostics, and packaging costs are not a complete measured ledger.
- Lease occupancy is not computation; successor full lifetime CPU/wall is not measured here.
- Baseline coverage is the four-family pilot plus eight final families; earlier NS026 families and other unrelated controls are outside this component and are not asserted zero.
- Private signed originals, candidate/reference/oracle bytes and original-source-tree replay are not released by this numerical component.

AI/human effort and unmeasured setup are not free. Actual profile overshoots and sanitized incomplete-hidden-validation disclosures remain unchanged.
