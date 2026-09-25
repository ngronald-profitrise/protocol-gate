# Formal proofs

This directory contains the TLA+ specification of the Protocol Gate state machine
and its safety invariants.

## Files

| File | Purpose |
|---|---|
| `ProtocolGate.tla` | The specification: states, actions, the transition relation, and the safety invariants |
| `ProtocolGate.cfg` | TLC model-checker configuration (2 actors, one fully-capable, one OFFER-only) |

## The guarantee

The spec encodes the harness's core safety property:

```
EffectOccurred(e) ⟹ ValidTransition(t) ∧ Authorized(t) ∧ Committed(t) ∧ AuditLogged(t)
¬ValidProposal(p)  ⟹ StateAfter(p) = StateBefore(p)
```

These are checked as the `Safety` invariant, composed of:

- **TypeInvariant** — all variables stay within their declared domains.
- **AuditInvariant** — `|effects| = |history| = |audit|`: every executed effect has
  exactly one accepted transition and one audit record.
- **AuthorizationInvariant** — every committed transition was made by an authorized
  actor and is a legal transition of the state machine.
- **SequenceInvariant** — the accepted-sequence counter equals the number of
  accepted transitions (monotonic, no gaps).
- **TerminalInvariant** — terminal states are absorbing; no transition leaves one.

The `Reject` action models the fail-closed contract: for **any** invalid proposal,
`status`, `history`, `effects` and the nonce set are `UNCHANGED`.

## Running the model checker

Install the TLA+ tools (`tla2tools.jar`) from the
[TLA+ releases](https://github.com/tlaplus/tlaplus/releases), then:

```bash
# Syntax / semantic check only
java -cp tla2tools.jar tla2sany.SANY ProtocolGate.tla

# Full model check of the Safety invariant
java -cp tla2tools.jar tlc2.TLC -config ProtocolGate.cfg ProtocolGate.tla
```

Expected output ends with `Model checking completed. No error has been found.`

The bundled model explores a small but representative state space (two actors,
nonces `0..2`). Widen `Actors`, `Capabilities`, and the nonce range in the `.cfg`
to check larger configurations.
