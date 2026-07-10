-- Rule: Toffoli-CNOT commutation (sharing 1 qubit: Toffoli control = CNOT target)
-- Before:
-- q1: ───@───────
--        │
-- q2: ───@───X───
--        │   │
-- q3: ───X───┼───
--            │
-- q4: ───────@───
-- After:
-- q1: ───────@───@───
--            │   │
-- q2: ───X───@───┼───
--        │   │   │
-- q3: ───┼───X───X───
--        │       │
-- q4: ───@───────@───

create or replace procedure ccx_cx_share_1_ctrl_tgt(pass_count int, timeout int)
--- create or replace procedure ccx_cx_commute(pass_count int, timeout int, run_nr int)
    language plpgsql
as
$$
declare
    declare
    -- Gates
    toffoli record;
    cx record;
    gate record;

    -- Links to the Toffoli control neighbours that need to be updated
    tof_ctrl_prev bigint;
    tof_ctrl_next bigint;

    cx_next_q2 bigint;

    -- Which Toffoli control (0 or 1) is shared with the CNOT target
    tof_port_connected int;

    -- Neighbours that need to be updated
    cx_right_q1 record;
    cx_right_q2 record;
    tof_right_ctrl record;
    tof_right_q3 record;
    tof_left_ctrl record;

    -- Timing
    start_time timestamp;

    -- Gate type ids
    cx_type smallint;
    cxpow_type smallint;
    toffoli_types smallint[];

    -- Neighbour ids
    cx_next_q1_id bigint;
    cx_next_q2_id bigint;
    tof_ctrl_prev_id bigint;
    tof_ctrl_next_id bigint;
    tof_next_q3_id bigint;

    -- Encoded links
    cx_ctrl bigint;
    cx_tgt bigint;
    cx_and_neighbour_new_link bigint;
    tof_new_link bigint;
    tof_tgt bigint;

    -- Newly inserted Toffoli links
    new_tof_ctrl_1 bigint;
    new_tof_ctrl_2 bigint;
    new_tof_tgt bigint;

    -- Newly inserted Toffoli
    new_tof_id bigint;
    new_tof_type smallint;
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
                       and get_port_from_link(prev_q2) in (0, 1)
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

            -- Recheck that the locked gates still match the rewrite pattern.
            if not (
                    (cx.type = cxpow_type and cx.param = 1)
                    or (cx.type = cx_type and cx.param = 0)
                )
                or get_id_from_link(cx.prev_q2) != toffoli.id 
                or not (toffoli.type = any(toffoli_types))
            then
                commit;
                continue;
            end if;

            tof_port_connected := get_port_from_link(cx.prev_q2);
            if tof_port_connected = 0
                and get_id_from_link(toffoli.next_q1) = cx.id
                and get_port_from_link(toffoli.next_q1) = 1
            then 
                tof_ctrl_prev := toffoli.prev_q1;
                tof_ctrl_next := toffoli.next_q2;
            elsif tof_port_connected = 1
                and get_id_from_link(toffoli.next_q2) = cx.id
                and get_port_from_link(toffoli.next_q2) = 1
            then 
                tof_ctrl_prev := toffoli.prev_q2;
                tof_ctrl_next := toffoli.next_q1;
            else 
                commit;
                continue;
            end if;

            -- Compute the ids of the neighbours
            cx_next_q1_id := get_id_from_link(cx.next_q1);
            cx_next_q2_id := get_id_from_link(cx.next_q2);
            tof_ctrl_next_id := get_id_from_link(tof_ctrl_next);
            tof_ctrl_prev_id := get_id_from_link(tof_ctrl_prev);
            tof_next_q3_id := get_id_from_link(toffoli.next_q3);

            -- Attempt to lock the neighbours of the pair (left of first gate and right of second gate)
            select * into cx_right_q1 from linked_circuit where id=cx_next_q1_id for update skip locked;
            select * into cx_right_q2 from linked_circuit where id=cx_next_q2_id for update skip locked;
            select * into tof_right_ctrl from linked_circuit where id=tof_ctrl_next_id for update skip locked;
            select * into tof_right_q3 from linked_circuit where id=tof_next_q3_id for update skip locked;
            select * into tof_left_ctrl from linked_circuit where id=tof_ctrl_prev_id for update skip locked;

            -- If locking the neighbours failed, commit and move to the next candidate pair
            if cx_right_q1.id is null
                or cx_right_q2.id is null
                or tof_right_ctrl.id is null
                or tof_right_q3.id is null
                or tof_left_ctrl.id is null
            then
                commit;
                continue;
            end if;

            -- Compute new links to the pair
            cx_ctrl := create_link(cx.id, 0, cx.type);
            cx_tgt  := create_link(cx.id, 1, cx.type);
            if tof_port_connected = 0 then
                cx_and_neighbour_new_link := create_link(toffoli.id, 0, toffoli.type);
                tof_new_link := create_link(toffoli.id, 1, toffoli.type);
            else
                cx_and_neighbour_new_link := create_link(toffoli.id, 1, toffoli.type);
                tof_new_link := create_link(toffoli.id, 0, toffoli.type); 
            end if;
            tof_tgt := create_link(toffoli.id, 2, toffoli.type);

            --- Insert a new Toffoli gate 
            insert into linked_circuit(prev_q1, prev_q2, prev_q3, type, param, switch, next_q1, next_q2, next_q3, label)
            values (tof_new_link, cx_ctrl, tof_tgt, 23, 1, false, tof_ctrl_next, toffoli.next_q3, cx.next_q1, cx.label)
            returning id, type 
            into new_tof_id, new_tof_type;

            -- Compute links to the new Toffoli gate
            new_tof_ctrl_1 := create_link(new_tof_id, 0, new_tof_type); -- right link of the original Toffoli control
            new_tof_ctrl_2 := create_link(new_tof_id, 1, new_tof_type); -- right link of the original CNOT control
            new_tof_tgt := create_link(new_tof_id, 2, new_tof_type);

            -- Update links of the left and right neighbours 
            perform update_next_link(tof_left_ctrl.id, tof_ctrl_prev, cx_tgt);
            perform update_prev_link(tof_right_ctrl.id, tof_ctrl_next, new_tof_ctrl_1);
            perform update_prev_link(tof_right_q3.id, toffoli.next_q3, new_tof_tgt);
            perform update_prev_link(cx_right_q1.id, cx.next_q1, new_tof_ctrl_2);
            perform update_prev_link(cx_right_q2.id, cx.next_q2, cx_and_neighbour_new_link);

            -- Update the target pair Toffoli and CNOT 
            cx_next_q2 := cx.next_q2;
            update linked_circuit set (prev_q2, next_q1, next_q2) = (tof_ctrl_prev, cx_and_neighbour_new_link, new_tof_ctrl_2) where id = cx.id; 
            if tof_port_connected = 0 then
                update linked_circuit set (prev_q1, next_q1, next_q2, next_q3) = (cx_tgt, cx_next_q2, new_tof_ctrl_1, new_tof_tgt) where id = toffoli.id;
            else
                update linked_circuit set (prev_q2, next_q1, next_q2, next_q3) = (cx_tgt, new_tof_ctrl_1, cx_next_q2, new_tof_tgt) where id = toffoli.id;
            end if;            
            commit; -- release the lock

        end loop; -- end gate loop

	    if extract(epoch from (clock_timestamp() - start_time)) > timeout then
            exit;
        end if;

        pass_count = pass_count - 1;

    end loop; --end pass loop
end;$$;

