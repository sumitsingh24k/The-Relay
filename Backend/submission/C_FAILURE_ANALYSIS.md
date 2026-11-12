# C-setting failure analysis

The original C evaluation has two wrong outcomes. The original experiment rows are preserved; this analysis does not relabel them to improve the score.

## Question 3 - Transformer base model dimension

- **Question:** What is the base Transformer model dimension?
- **Recorded answer:** `4096`.
- **Recorded citation:** Moshi, arXiv:2410.00037v1, PDF page 8.
- **Correct paper/value:** Attention Is All You Need, arXiv:1706.03762v7, `d_model = 512`.

### Evidence

`c_failure_retrieval_debug.json` captures the original-query reproduction. Before the correction, title expansion treated the generic word `model` as a title anchor. That added Moshi title terms; the original C run consequently cited Moshi's Helium dimension. This is a **retrieval/query-expansion failure**, followed by a citation that was structurally valid but semantically answered the wrong model.

### Correction and verification

`retrieve.py` now permits paper-title expansion only when a distinctive title term matches, not generic terms such as `model` or `time`. Setting C now genuinely fetches eight BM25 candidates before retaining four via MiniLM. A regression test verifies that the Transformer-dimension query returns Attention-paper evidence only. A separate real Groq regression request returned `512`, cited Attention p.3, and passed citation/claim verification; see `correction_q3_run.json`.

The original row remains graded `wrong`; the correction evidence is not substituted into the original experiment result.

## Question 10 - H-Net

- **Question:** What is an H-Net?
- **Recorded outcome:** safe refusal because the provider output was not valid structured JSON.
- **Retrieved evidence:** Dynamic Chunking passages were present in the BM25 top eight and MiniLM top four; see `c_failure_retrieval_debug.json`.

### Root cause

This is **not a retrieval failure**. Relevant Dynamic Chunking passages were selected. The provider response failed the required JSON structure parse, therefore the safety gate correctly withheld an unverified answer. It is an answerable-question failure caused by **generation/structured-output formatting**, not a citation-integrity bypass.

### Decision

No automatic correction was applied. Relaxing the JSON parser without saving the original malformed provider payload would be speculative and could weaken grounding. The result remains graded `wrong`, while the safe refusal behavior remains intact.
