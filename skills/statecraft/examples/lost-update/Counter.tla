---------------------------- MODULE Counter ----------------------------
(* Two workers each add 1 to a shared count. Unsafe reads the count, then writes
   what it read plus one, in two steps; Safe does both in one step. The law: once
   every worker is done, no update was lost. *)
EXTENDS Naturals, FiniteSets
CONSTANTS Workers, Safe
VARIABLES count, seen, pc
vars == <<count, seen, pc>>

Init == /\ count = 0
        /\ seen = [w \in Workers |-> 0]
        /\ pc = [w \in Workers |-> "read"]

Read(w)  == /\ pc[w] = "read"
            /\ IF Safe THEN /\ count' = count + 1 /\ pc' = [pc EXCEPT ![w] = "done"]
                            /\ UNCHANGED seen
                       ELSE /\ seen' = [seen EXCEPT ![w] = count] /\ pc' = [pc EXCEPT ![w] = "write"]
                            /\ UNCHANGED count
Write(w) == /\ pc[w] = "write"
            /\ count' = seen[w] + 1
            /\ pc' = [pc EXCEPT ![w] = "done"]
            /\ UNCHANGED seen

Next == \E w \in Workers : Read(w) \/ Write(w)
Spec == Init /\ [][Next]_vars

AllDone == \A w \in Workers : pc[w] = "done"
\* Law: no lost update.
NoLostUpdate == AllDone => count = Cardinality(Workers)
=============================================================================
