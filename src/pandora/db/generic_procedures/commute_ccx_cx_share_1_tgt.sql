-- Rule: Toffoli-CNOT commutation (Toffoli and CNOT share 1 one qubit: Toffoli target =  CNOT target)
-- Before:
-- q1: ───@───────
--        │
-- q2: ───@───────
--        │
-- q3: ───X───X───
--            │
-- q4: ───────@───
-- After:
-- q1: ───────@───
--            │
-- q2: ───────@───
--            │
-- q3: ───X───X───
--        │
-- q4: ───@───────

create or replace procedure commute_ccx_cx_share_1_tgt(pass_count int, timeout int)
    language plpgsql
as
$$
declare
    toffoli record;
    cx record;

    left_gate record;
    right_gate record;
    gate record;

    start_time timestamp;

    cx_type smallint;
    cxpow_type smallint;
    toffoli_types smallint[];

    left_id bigint;
    right_id bigint;

    cx_next_q2 bigint;

    cx_tgt bigint;
    tof_tgt bigint;

begin
    start_time := clock_timestamp();
    select id into cx_type from gate_types where name = 'cx';
    select id into cxpow_type from gate_types where name = 'cxpow';
    select array_agg(id) into toffoli_types from gate_types where name in ('ccx', 'toffoli');

    while pass_count > 0 loop
         -- loop through all CNOT gates that currently fit the pattern we are looking for:
        for gate in
            select * from linked_circuit
                     where
                       ((type = cxpow_type and param = 1) or (type = cx_type and param = 0))
                       and get_type_from_link(prev_q2) = any(toffoli_types) 
                       and get_port_from_link(prev_q2) = 2

                       -- ensure that the CNOT control is not on the same qubit as any of the Toffoli qubits 
                       and not left_dependency(prev_q1, get_id_from_link(prev_q2)) -- ensure that the CNOT control is not on the same qubit as one of the Toffoli qubits
                       -- and partition_id = my_partition
        loop 
            -- attempt to lock the two gates
            -- if not already locked by another process (skip locked), lock the pair of gates (for update)

            select * into cx from linked_circuit where id = gate.id for update skip locked;
            select * into toffoli from linked_circuit where id = get_id_from_link(cx.prev_q2) for update skip locked;
            
            -- If acquiring locks is not successful (e.g. gates deleted already by another process),
            -- commit and move to the next candidate pair
            -- locks are released at commit!
            if cx.id is null
                or toffoli.id is null
            then
                commit;
                continue;
            end if;

            -- If gates were updated by another process during the traversal of the for loop
            -- and do not match the template pattern anymore
            -- commit and move to the next candidate pair
            if  not ((cx.type = cxpow_type and cx.param = 1) 
                    or(cx.type = cx_type and cx.param = 0)
                )
                or get_id_from_link(cx.prev_q2) != toffoli.id
                or get_port_from_link(cx.prev_q2) != 2
                or left_dependency(cx.prev_q1, toffoli.id)
                or not (toffoli.type = any(toffoli_types))
                or get_id_from_link(toffoli.next_q3) != cx.id
                or get_port_from_link(toffoli.next_q3) != 1
                or right_dependency(toffoli.next_q1, cx.id)
                or right_dependency(toffoli.next_q2, cx.id)
            then
                commit;
                continue;
            end if;

            -- Compute the ids of the neighbours
            left_id := get_id_from_link(toffoli.prev_q3);
            right_id := get_id_from_link(cx.next_q2);
        
            -- Attempt to lock the neighbours of the pair (left of first gate and right of second gate)
            select * into left_gate from linked_circuit where id = left_id for update skip locked;
            select * into right_gate from linked_circuit where id = right_id for update skip locked;

            -- If locking the neighbours failed, commit and move to the next candidate pair
            if left_gate.id is null
                or right_gate.id is null
            then
                commit;
                continue;
            end if;
            
            -- Compute new links for the pair and neighbouring gates 
            cx_tgt := create_link(cx.id, 1, cx.type);
            tof_tgt := create_link(toffoli.id, 2, toffoli.type);

            -- Update links of the left and right neighbours 
            perform update_next_link(left_id, toffoli.prev_q3, cx_tgt);
            perform update_prev_link(right_id, cx.next_q2, tof_tgt);

            -- Update Toffoli and CNOT 
            cx_next_q2 := cx.next_q2;
            update linked_circuit set (prev_q2, next_q2) = (toffoli.prev_q3, tof_tgt) where id = cx.id;
            update linked_circuit set (prev_q3, next_q3) = (cx_tgt, cx_next_q2) where id = toffoli.id;  

            commit; -- release the lock

        end loop; -- end gate loop

	    if extract(epoch from (clock_timestamp() - start_time)) > timeout then
            exit;
        end if;

        pass_count = pass_count - 1;

    end loop; --end pass loop
end;$$;

