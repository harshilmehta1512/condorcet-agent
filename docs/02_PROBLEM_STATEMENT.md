# 02 — Problem Statement, Thesis and Approach (LOCKED 1:46 PM)

**Project:** Condorcet Agent — a trust agent that acts only when its decision holds up across different evidence
**Track:** Build a Trust Agent (Ezio Decision-Grade AI buildathon, Oct 10, 2026, build window 1:15–3:00 PM PT)
**Deliverable:** 1–2 min demo video (main report + one other report) + repo link + tools-used note

---

## 1. The problem

An LLM answers a question. Ezio checks it and produces a trust report: claims with verdicts and sources, module scores (accuracy, bias, tone, agreement) and findings. Someone then has to **act**: publish, put it in a client note, brief a decision maker.

The usual trust agent reads the report and makes one decision. Two hidden weaknesses:
1. **Agreement isn't independence.** "Supported by 4 sources" may be one press release repeated four times. "Several AI checks agree" may be one shared blind spot repeated. Recent research shows **9 LLM judges from 7 model families ≈ 2 independent votes**, and the best single judge matches the whole panel (Kohli 2026). When two models are both wrong, they often give the same wrong answer (60% on one leaderboard, Kim et al., ICML 2025).
2. **One decision hides how fragile it is.** If the decision would change depending on which piece of evidence the decision-maker happened to focus on, nobody finds out. Then the decision isn't reliable, even if it happens to be right.

## 2. Thesis

> **A decision is reliable when it holds up across independent views of the evidence.** The agent should act only when its decision is stable across judges that each see a different slice of the evidence. When the decision isn't stable, it should identify the specific evidence the decision depends on and ask an accountable human about exactly that.

We **do not claim** to know whether a decision is "correct." Without ground truth nobody can. We claim to measure whether it **holds up**, and to route it to a human when it doesn't.

## 3. Research basis

| Idea | Source | How we use it |
|---|---|---|
| Majority evidence beats any one voter only if votes are independent | Condorcet jury theorem (1785) | Why we measure independence, not agreement |
| LLM judge panels have correlated errors: 9 judges ≈ 2 effective votes | Guneet Kohli, *Nine Judges, Two Effective Votes*, preprint 2026 — https://arxiv.org/abs/2605.29800 | Why a plain multi-LLM vote isn't trustworthy |
| LLMs share errors across providers | Kim, Garg, Peng & Garg, *Correlated Errors in LLMs*, ICML 2025 — https://arxiv.org/abs/2506.07962 | Same |
| Effective number of independent votes: n_eff = n / (1 + (n−1)·ρ̄) | Kish, effective sample size | We report n_eff for the panel |
| Giving each ensemble member a different subset of the inputs reduces correlation | Ho, *The Random Subspace Method*, 1998 — https://doi.org/10.1109/34.709601 ; Breiman, *Random Forests*, 2001 — https://doi.org/10.1023/A:1010933404324 | Each judge sees a different evidence slice |
| Copying between sources inflates apparent agreement; it can be detected and discounted | Dong, Berti-Équille & Srivastava, *Integrating Conflicting Data: The Role of Source Dependence*, VLDB 2009 | We group a claim's sources by shared origin before counting them |

**Ours (untested before today):** applying random evidence subspaces to an LLM judge panel *inside a trust agent*, and using the **evidence that flips the decision** as the target of the human handoff.

## 4. How the agent works

1. **Parse** the Ezio report PDF: analyzed text, verdict, module scores (count █ blocks), claims with verdict and sources (type, title, date), findings with severity.
2. **Group sources by origin** per claim (same outlet / near-identical title / same story and date) → number of sources vs number of **independent origins**.
3. **Build evidence pieces:** one per claim (with its grouped sources), one for the module scores, one per finding.
4. **Judge panel with evidence subspaces:** 9 judges (different model families via TokenRouter). Each sees the decision context plus a **different subset of the evidence pieces** (each piece shown to ~4 of 9 judges). Each picks APPROVE / REWRITE / PULL_SOURCE / ESCALATE / BLOCK and cites the evidence it used.
5. **Three outcomes (revised 2:53 after an external review, see `05` D22):**
   - **STABLE:** ≥ 70% of judges choose the same action → the agent takes it.
   - **INFO_GAP:** the split is fully explained by *who was shown* one piece (each exposure group ≥ 80% internally agreed). That disagreement is one **we created by hiding evidence**, so it is **not** called uncertainty: the decision follows the judges who saw the piece, and the piece is reported as the evidence a reviewer must not miss.
   - **FRAGILE:** judges who saw the same evidence still disagree → genuine disagreement → a human decides.
   - Every decision also shows a **simple-rule baseline** ("contradicted / CRITICAL / unverified → act on it") and a **"panel adds beyond the rule: yes/no"** flag, so we never claim value the rule alone would give.
6. **Hard rules in code (safety floor):** a load-bearing claim that Ezio marks as contradicted can never be APPROVE; a CRITICAL finding can never be silently approved. The LLM panel can make the decision stricter, never looser than these rules.
7. **Human in the loop:** if fragile, escalate to the accountable person named in the context with **one question about the flip evidence**. Their answer is added as new evidence, the panel re-runs, and the trace shows the decision before → after.

## 5. Use cases (decision contexts)

- **Comms lead** deciding whether to publish an AI-drafted explainer (Work from home report).
- **Analyst** deciding whether an AI answer can go into a client note (EV market report).
- **Policy staff** briefing a decision maker on a contested topic (Nuclear energy / AGI timelines).

One agent, one policy, any of the 4 reports. Only the context changes.

## 6. What's different from other teams

Most teams map Ezio's verdict to an action, maybe with one LLM summary. We:
- treat agreement as evidence **only when it's independent** (sources and judges),
- test whether the decision **survives different views of the evidence**,
- tell the human **exactly which evidence** the decision depends on.

## 7. Honest limits
- **With simulated judges the panel mostly reproduces the simple rule** (they are rules). On our 4 reports: same action and focus as the rule on EV, Work-from-home and AGI; different action only on Nuclear. Whether real LLM judges add anything beyond the rule is the open experiment (needs TokenRouter).
- Judges are LLMs. Their stability isn't correctness; we say "holds up," never "correct."
- Source grouping uses simple transparent rules; it can miss hidden shared origins.
- 9 judges per report is a small panel; n_eff is reported with that caveat.
- If the real reports contain no repeated sources, we don't claim any. The panel stability still works.

## 8. Pitch (≈ 45 s)
> "Our trust agent reads an Ezio trust report and decides what happens next: approve, rewrite, pull another source, escalate, or block. Most agents take the report's verdict at face value. But agreement isn't proof. Recent research by Guneet Kohli shows nine AI judges agreeing carry about the information of two independent votes. So we borrowed a classic fix from random forests, the random subspace method: each judge sees a different slice of the evidence. If the decision holds no matter which evidence a judge sees, the agent acts. If it changes, the agent finds the exact piece of evidence the decision depends on and asks a human about that one thing. We don't just check the answer. We check whether the decision survives."
