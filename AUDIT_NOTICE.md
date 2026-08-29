# Audit notice — 2026-08-29

This repository is part of the Merkabit research corpus (2026). In August 2026
the corpus underwent a **complete self-audit** — every registry claim
re-verified, reframed, or refuted, with runnable code, refutations recorded at
equal prominence by design:

**https://github.com/selinaserephina-star/Merkabit_corpus_audit**

The underlying computations in this repository **reproduce exactly**; several
*interpretations* are corrected by the audit. Findings affecting this
repository:

- The tunnel's 'exact destructive interference zero 0.000' is an estimator floor: on entangled registers the SWAP test measures <SWAP> on the joint state (not an overlap), and sqrt(max(0, .)) clamps the actual <SWAP> = -0.14 to exactly 0.000 (thread T10).
- The directional beta/gamma asymmetry is real and chirality-driven (an achiral control is exactly symmetric) but operating-point-local: the sign flips at other J and p_coupling (T10).
- Recommendation from the audit: report <SWAP> itself, signs included.

— Selina Stenberg, with Claude (Anthropic)
