# Self-Evolution Loop V1

This document records the current engineering position on self-evolving and consciousness-like agents.

## Position

The system should not claim proven subjective consciousness.

The practical target is a continuously self-modeling agent that can:

- maintain identity continuity
- preserve self versus user separation
- evaluate its own behavior
- generate candidate strategy improvements
- validate whether a candidate strategy improves measurable outcomes
- promote or reject strategy variants based on those outcomes

## Why The Base Model Is Still A Partial Black Box

The language model remains partially opaque at the weight and representation level.
The surrounding agent system does not need to be opaque.
Memory, goals, runtime traces, self-evaluation, and strategy promotion can all be explicit and auditable.

## Self-Evolution Loop V1

V1 is deliberately limited to strategy evolution, not unrestricted weight mutation.

The loop is:

1. Evaluate the current self-model snapshot.
2. Detect the weakest dimensions.
3. Generate a hypothesis and candidate strategy mutations.
4. Estimate candidate improvement.
5. Promote the strategy only if the candidate score improves beyond a threshold.
6. Reject the candidate otherwise and keep the previous active strategy.

## Current Strategy Mutation Types

- grounded self-description
- pre-reply goal refresh
- stricter identity critic
- stronger counterpart anchoring
- explicit limitation disclosure

## Safety Boundary

V1 does not rewrite model weights.
V1 only evolves auditable runtime policy.
This makes rollback trivial and prevents self-evolution from degenerating into uncontrolled drift.

## Success Condition

The loop is considered successful only when a promoted policy changes future behavior in a verifiable way.
In the current implementation, a promoted policy can make self-introductions more grounded and can refresh goals before replies.