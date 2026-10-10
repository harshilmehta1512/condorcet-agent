# 02 — Problem Statement, Thesis and Approach

**Project:** Condorcet — measuring, and restoring, the independence of AI judge panels
**Track:** Build Trust Agent (alternative framing: Approval Gate — confirm at the 1:00 PM reveal)
**Team:** 2 people · Stanford Decision-Grade AI Buildathon · Oct 10, 2026

---

## 1. The problem

The most common way to make an AI decision "trustworthy" is to **have several models check it and trust it if they agree.** This covers LLM juries, cross-model review and multi-agent verification. Products and research pipelines treat "5 of 5 models agreed" as strong evidence.

This depends on the **Condorcet jury theorem (1785)**: a majority of voters is more likely to be right than any one voter, and adding voters helps, **but only if their errors are independent.**

For LLMs, errors are not independent:

| Evidence | Source |
|---|---|
| Across 350+ LLMs: on one leaderboard, when two models are both wrong they give the **same wrong answer 60% of the time**. More accurate models have **more** correlated errors, across providers and architectures. | Kim, Garg, Peng & Garg, *Correlated Errors in Large Language Models*, ICML 2025 — https://arxiv.org/abs/2506.07962 |
| A **9-judge panel from 7 model families ≈ 2 independent votes** (n_eff ≈ 1.94–2.48). The panel falls 8–22 points short of what independent voting predicts (MNLI: ~94% predicted vs 72% observed). **The best single judge matches or beats the full panel in every condition.** Better vote-combining methods close at most 11% of the gap. Changing prompts, temperature or chain-of-thought doesn't fix it. | Kohli, *Nine Judges, Two Effective Votes*, preprint, May 2026 — https://arxiv.org/abs/2605.29800 |

**Consequence for decision-critical AI:** a system that acts because "9 of 9 models agreed" is **overconfident in the dangerous direction.** Agreement among correlated judges isn't confirmation.

**Plain-language version:** if all 9 of your weather apps use the same forecast model, checking 9 apps is like checking 1. When that model is wrong, all 9 are wrong together.

## 2. Key quantity: effective number of judges

For n judges with average pairwise error correlation ρ̄ (Kish's effective sample size):

```
n_eff = n / (1 + (n − 1) · ρ̄)
```
- ρ̄ = 0 → n_eff = n (fully independent)
- ρ̄ = 1 → n_eff = 1 (copies of one judge)
- n = 9, ρ̄ ≈ 0.44 → n_eff ≈ 2

## 3. Our thesis (two parts)

### Part 1: Replication on a new task (Kohli 2026's claim)
> LLM judge panels have strongly correlated errors, so a 9-judge panel is worth far fewer than 9 independent judges and does no better than its best single member.

Kohli tested natural-language inference. **We test scientific claim verification** (SciFact) with a different set of models. Replicating it shows the result generalizes beyond NLI.

### Part 2: New hypothesis (ours, not found in any published work)
> **Giving each judge a different subset of the evidence makes judge errors less correlated, raising n_eff enough that the panel beats its best single member.**

**Why we think it could work:**
- The jury theorem assumes jurors have **independent private signals**. LLM judges are given the **identical input**, so they have no independent signals. Part of their correlation may come from this shared input, not only from shared training.
- **Breiman, *Random Forests* (2001)**: an ensemble's error is bounded by the average correlation between members relative to their strength squared (ρ̄ · (1 − s²) / s²). Lower correlation lowers the bound. https://doi.org/10.1023/A:1010933404324
- **Ho, *The Random Subspace Method* (1998)**: giving each ensemble member a random subset of input features decorrelates their errors. https://doi.org/10.1109/34.709601
- We apply this to AI juries: **random evidence subspaces for LLM judges**, with an explicit option to abstain (NOT_ENOUGH_INFO).

**The known risk (the trade-off Breiman's bound predicts):** each judge sees less evidence, so each judge's accuracy (strength) drops. Part 2 works only if lower correlation more than makes up for weaker judges. **This may fail.** That outcome is reported honestly as a trade-off result.

## 4. Pre-registered hypotheses and success criteria

Written before any real data is seen. **Don't edit after results arrive.**

| ID | Hypothesis | Pass condition |
|---|---|---|
| **H1** (replication) | Standard panel A has strongly correlated errors | n_eff(A) ≤ n/2 (for 9 judges: ≤ 4.5) |
| **H2** (replication) | Standard panel A doesn't beat its best single judge | Panel A accuracy ≤ best single judge + 2 points, on the same items |
| **H3** (ours) | Split-evidence panel B is more independent | n_eff(B) − n_eff(A) ≥ 0.5, with non-overlapping bootstrap 95% CIs reported (overlap is reported as "inconclusive") |
| **H4** (ours) | Split-evidence panel B beats its best single judge | Panel B accuracy > best single judge accuracy, on the items panel B decided |

**Part 2 succeeds only if H3 and H4 both pass.**

## 5. Approach (what we do and why)

| Step | What | Why |
|---|---|---|
| Dataset | **SciFact** (Wadden et al., EMNLP 2020, https://arxiv.org/abs/2004.14974): scientific claims + research abstracts, **human labels (SUPPORT/CONTRADICT)** and **human-marked evidence sentences** | Ground truth from people; known evidence location lets us score judges fairly even when they see only part of the abstract |
| Judges | n = 9 (minimum 5), different model families, cheap tiers | Mirrors Kohli's "nine judges"; cheap models make more natural errors, so we don't need hand-built traps (which frontier models caught in all our morning tests) |
| Condition A | Every judge sees the full abstract | The standard panel everyone builds |
| Condition B | Each sentence goes to r = ⌈0.4·n⌉ judges (n = 9 → r = 4), so each judge sees ≈40–45%; abstaining is allowed | Random evidence subspace; every sentence is still seen by several judges, so the panel as a whole sees everything |
| Scoring | Against human labels; in B, a judge without the gold evidence is scored correct for abstaining | No LLM grading; fair to judges that weren't shown the evidence |
| Panel decision | Majority of committed (non-abstaining) judges; tie or no committed judges → ESCALATE | Standard, simple, and how a real system would fall back to a human |
| Fair comparison | Best single judge (highest accuracy in A) scored on **the same items the panel decided** | Prevents a panel from looking better just by skipping hard items |
| Uncertainty | Wilson 95% intervals; bootstrap (1,000×) for n_eff | N = 150 is small; we state it |

## 6. Why this matters (who uses the result)

- **Any team running multi-model verification**, including many at this event: the Consensus Auditor tells them what their panel's agreement is actually worth and what approval threshold hits a target error rate.
- **Model routers (TokenRouter, 140+ models):** choose the 3 models whose errors are least correlated for a domain, so votes actually count.
- **Decision-critical deployments** (finance, health, legal): replace "N models agreed" with a measured probability.

## 7. Scope limits (stated up front)
- One task (scientific claim verification), N ≈ 150 claims, 9 judges, one prompt. Results are evidence, not a general law.
- Kohli 2026 is a single-author preprint and not yet peer-reviewed. Kim et al. 2025 is peer-reviewed (ICML).
- We don't claim to have discovered judge correlation. We replicate it, turn it into a tool, and test a new remedy.

## 8. One-line pitch
> *"Nine AI judges agreeing sounds like certainty. Research shows it's worth about two votes. We built the tool that measures what your AI jury is actually worth, and tested whether an idea from random forests can make it worth more."*
