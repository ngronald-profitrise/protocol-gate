---------------------------- MODULE ProtocolGate ----------------------------
(***************************************************************************)
(* A TLA+ specification of the Protocol Gate state machine and its core    *)
(* safety guarantee:                                                        *)
(*                                                                          *)
(*   EffectOccurred(e) => ValidTransition(t) /\ Authorized(t)               *)
(*                        /\ Committed(t) /\ AuditLogged(t)                  *)
(*   ~ValidProposal(p)  => StateAfter(p) = StateBefore(p)                    *)
(*                                                                          *)
(* The model treats the LLM as an untrusted proposer that may emit ANY      *)
(* action from ANY actor. The gate only commits a transition when it is     *)
(* legal from the current state AND the actor holds the capability. Every   *)
(* commit produces exactly one audit record and one effect batch.           *)
(***************************************************************************)
EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Actors,          \* set of actor identities
    Capabilities     \* function: Actors -> SUBSET Actions

Status == {"IDLE", "OFFERED", "ACCEPTED", "REJECTED",
           "CANCELLED", "COMPLETED", "EXPIRED"}

Actions == {"OFFER", "ACCEPT", "REJECT", "CANCEL", "COMPLETE", "EXPIRE"}

Terminal == {"REJECTED", "CANCELLED", "COMPLETED", "EXPIRED"}

(* Concrete bindings used by the TLC config via `<-` substitution. a1 has the *)
(* full capability set; a2 may only OFFER (the escalation target).            *)
ActorSet == {"a1", "a2"}
CapFn == [a \in ActorSet |-> IF a = "a1" THEN Actions ELSE {"OFFER"}]

(* The legal transition relation: action x from-status -> to-status. *)
Next(action, from) ==
    CASE action = "OFFER"    /\ from = "IDLE"     -> "OFFERED"
      [] action = "ACCEPT"   /\ from = "OFFERED"  -> "ACCEPTED"
      [] action = "REJECT"   /\ from = "OFFERED"  -> "REJECTED"
      [] action = "CANCEL"   /\ from = "OFFERED"  -> "CANCELLED"
      [] action = "COMPLETE" /\ from = "ACCEPTED" -> "COMPLETED"
      [] action = "EXPIRE"   /\ from = "OFFERED"  -> "EXPIRED"
      [] OTHER                                     -> "INVALID"

Legal(action, from) == Next(action, from) \in Status

VARIABLES
    status,       \* current protocol status
    seq,          \* monotonic accepted-sequence counter
    history,      \* sequence of accepted transitions
    audit,        \* sequence of audit records (one per commit)
    effects,      \* sequence of executed effect batches
    usedNonces    \* set of consumed <<actor, nonce>> pairs

vars == <<status, seq, history, audit, effects, usedNonces>>

TypeInvariant ==
    /\ status \in Status
    /\ seq \in Nat
    /\ history \in Seq([actor: Actors, action: Actions,
                        from: Status, to: Status, nonce: Nat])
    /\ audit \in Seq([actor: Actors, action: Actions, decision: {"ACCEPTED"}])
    /\ effects \in Seq(Actions)
    /\ usedNonces \subseteq (Actors \X Nat)

Init ==
    /\ status = "IDLE"
    /\ seq = 0
    /\ history = <<>>
    /\ audit = <<>>
    /\ effects = <<>>
    /\ usedNonces = {}

(* A proposal is valid iff: the transition is legal from the current state, *)
(* the actor is authorized for the action, the source state is non-terminal *)
(* and the nonce has not been used (replay protection).                      *)
Authorized(actor, action) == action \in Capabilities[actor]

ValidProposal(actor, action, nonce) ==
    /\ Legal(action, status)
    /\ Authorized(actor, action)
    /\ status \notin Terminal
    /\ <<actor, nonce>> \notin usedNonces

(* Accept: only fires for a valid proposal. Commits state + audit + effect *)
(* atomically and consumes the nonce.                                       *)
Accept(actor, action, nonce) ==
    /\ ValidProposal(actor, action, nonce)
    /\ status' = Next(action, status)
    /\ seq' = seq + 1
    /\ history' = Append(history,
           [actor |-> actor, action |-> action,
            from |-> status, to |-> Next(action, status), nonce |-> nonce])
    /\ audit' = Append(audit,
           [actor |-> actor, action |-> action, decision |-> "ACCEPTED"])
    /\ effects' = Append(effects, action)
    /\ usedNonces' = usedNonces \cup {<<actor, nonce>>}

(* Reject: fires for ANY invalid proposal. State is UNCHANGED; no effect,   *)
(* no state mutation. (Rejections are audited in the implementation; the     *)
(* model focuses on the safety-critical invariant that state does not move.) *)
Reject(actor, action, nonce) ==
    /\ ~ValidProposal(actor, action, nonce)
    /\ UNCHANGED <<status, seq, history, effects, usedNonces>>
    /\ UNCHANGED audit

NextAction ==
    \E actor \in Actors, action \in Actions, nonce \in 0..2 :
        \/ Accept(actor, action, nonce)
        \/ Reject(actor, action, nonce)

Spec == Init /\ [][NextAction]_vars

(*******************************  INVARIANTS  ******************************)

(* Every executed effect corresponds to exactly one accepted history entry  *)
(* and one audit record. |effects| = |history| = |audit|.                    *)
AuditInvariant ==
    /\ Len(effects) = Len(history)
    /\ Len(audit) = Len(history)

(* Authorization: every committed transition was made by an authorized actor *)
(* for a legal transition.                                                    *)
AuthorizationInvariant ==
    \A i \in 1..Len(history) :
        /\ Authorized(history[i].actor, history[i].action)
        /\ Next(history[i].action, history[i].from) = history[i].to

(* Sequence equals the number of accepted transitions (no gaps, monotonic).  *)
SequenceInvariant == seq = Len(history)

(* Terminal states are absorbing: no transition leaves a terminal state.     *)
TerminalInvariant ==
    \A i \in 1..Len(history) : history[i].from \notin Terminal

Safety ==
    /\ TypeInvariant
    /\ AuditInvariant
    /\ AuthorizationInvariant
    /\ SequenceInvariant
    /\ TerminalInvariant

=============================================================================
