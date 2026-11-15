# Held-out autoencoder results

All rows use the frozen 1,913-source cohort. Source embedding reconstruction is a diagnostic, not semantic fidelity.

| Arm | Sources | Mean cosine | Mean MSE | Memory hits | Decoder calls |
|---|---:|---:|---:|---:|---:|
| T0 | 1913 | 0.196116 | 0.00252708 | — | 1913 |
| T1-104729 | 1913 | 0.196116 | 0.00252708 | 0 | 0 |
| T1-130363 | 1913 | 0.196116 | 0.00252708 | 0 | 0 |
| T1-155921 | 1913 | 0.196116 | 0.00252708 | 0 | 0 |
| T2-104729 | 1913 | 0.559938 | 0.00182343 | — | 1913 |
| T2-130363 | 1913 | 0.559938 | 0.00182343 | — | 1913 |
| T2-155921 | 1913 | 0.559938 | 0.00182343 | — | 1913 |
| T3-104729 | 1913 | 0.559938 | 0.00182343 | — | 0 |
| T3-130363 | 1913 | 0.559938 | 0.00182343 | — | 0 |
| T3-155921 | 1913 | 0.559938 | 0.00182343 | — | 0 |
| TRAIN mean supplement | 1913 | 0.538117 | 0.00240564 | — | 0 |

The primary paired component bootstrap uses 10,000 draws over 20 original source components. The largest contains 1730 / 1913 units. Training seeds are averaged within source units.
T2−T0 cosine: +0.36382199; component-bootstrap 95% interval [+0.35193936, +0.41635245].
T2−T0 mse: -0.00070365; component-bootstrap 95% interval [-0.00083814, -0.00066779].

T3 decoder entries are reused by exact parameter isolation; the native isolated proof heads are evaluated separately. T1 counts actual memory lookups and verifies every cold fallback against the T0 projection.
