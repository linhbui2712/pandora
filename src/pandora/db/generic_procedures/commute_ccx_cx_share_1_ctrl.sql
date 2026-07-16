-- Rule: Toffoli-CNOT commutation (Toffoli and CNOT share 1 one qubit: Toffoli control =  CNOT control)
-- Before:
-- q1: ───@───@───
--        │   │
-- q2: ───@───┼───
--        │   │
-- q3: ───X───┼───
--            │
-- q4: ───────X───
-- After:
-- q1: ───@───@───
--        │   │
-- q2: ───┼───@───
--        │   │
-- q3: ───┼───X───
--        │
-- q4: ───X───────


create or replace procedure commute_ccx_cx_share_1_ctrl(pass_count int, timeout int)
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

    tof_port_connected int;

    cx_type smallint;
    cxpow_type smallint;
    toffoli_types smallint[];

    left_id bigint;
    right_id bigint;

    cx_next_q1 bigint;

    tof_ctrl_prev bigint;

    cx_ctrl bigint;
    tof_ctrl bigint;

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
                       and get_type_from_link(prev_q1) = any(toffoli_types) 
                       and get_port_from_link(prev_q1) in (0, 1)
                       -- ensure that the CNOT target is not on the same qubit as one of the Toffoli qubits
                       and not left_dependency(prev_q2, get_id_from_link(prev_q1))
                       -- and partition_id = my_partition
        loop 
            -- attempt to lock the two gates
            -- if not already locked by another process (skip locked), lock the pair of gates (for update)

            select * into cx from linked_circuit where id = gate.id for update skip locked;
            select * into toffoli from linked_circuit where id = get_id_from_link(cx.prev_q1) for update skip locked;
            
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
                or get_id_from_link(cx.prev_q1) != toffoli.id
                or left_dependency(cx.prev_q2, toffoli.id)
                or not (toffoli.type = any(toffoli_types))
                or get_id_from_link(toffoli.next_q3) = cx.id                
            then
                commit;
                continue;
            end if;

            tof_port_connected := get_port_from_link(cx.prev_q1);
            if tof_port_connected = 0
                and get_id_from_link(toffoli.next_q1) = cx.id

                -- ensure that Toffoli's other two qubits are not on the same line as CNOT's qubits
                and not right_dependency(toffoli.next_q2, cx.id)
                and not right_dependency(toffoli.next_q3, cx.id)

                and get_port_from_link(toffoli.next_q1) = 0
            then 
                tof_ctrl_prev := toffoli.prev_q1;
            elsif tof_port_connected = 1
                and get_id_from_link(toffoli.next_q2) = cx.id
                and not right_dependency(toffoli.next_q1, cx.id)
                and not right_dependency(toffoli.next_q3, cx.id)
                and get_port_from_link(toffoli.next_q2) = 0
            then 
                tof_ctrl_prev := toffoli.prev_q2;
            else 
                commit;
                continue;
            end if;

            -- Compute the ids of the neighbours
            left_id := get_id_from_link(tof_ctrl_prev);
            right_id := get_id_from_link(cx.next_q1);
        
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
            cx_ctrl := create_link(cx.id, 0, cx.type);
            tof_ctrl := create_link(toffoli.id, tof_port_connected, toffoli.type);

            -- Update links of the left and right neighbours 
            perform update_next_link(left_id, tof_ctrl_prev, cx_ctrl);
            perform update_prev_link(right_id, cx.next_q1, tof_ctrl);

            -- Update Toffoli and CNOT 
            cx_next_q1 := cx.next_q1;
            update linked_circuit set (prev_q1, next_q1) = (tof_ctrl_prev, tof_ctrl) where id = cx.id;

            if tof_port_connected = 0 then
                update linked_circuit set (prev_q1, next_q1) = (cx_ctrl, cx_next_q1) where id = toffoli.id;
            else
                update linked_circuit set (prev_q2, next_q2) = (cx_ctrl, cx_next_q1) where id = toffoli.id;
            end if;

            commit; -- release the lock

        end loop; -- end gate loop

	    if extract(epoch from (clock_timestamp() - start_time)) > timeout then
            exit;
        end if;

        pass_count = pass_count - 1;

    end loop; --end pass loop
end;$$;

