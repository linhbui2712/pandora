-- Rule: Toffoli-CNOT commutation (sharing 1 qubit: Toffoli target = CNOT control)
-- Before:
-- q1: ───@───────
       │
-- q2: ───@───────
--        │
-- q3: ───X───@───
--            │
-- q4: ───────X───
-- After:
-- q1: ───────@───@───
--            │   │
-- q2: ───────@───@───
--            │   │
-- q3: ───@───X───┼───
--        │       │
-- q4: ───X───────X───

create or replace procedure ccx_cx_share_1_tgt_ctrl(pass_count int, timeout int)
--- create or replace procedure ccx_cx_commute(pass_count int, timeout int, run_nr int)
    language plpgsql
as
$$
declare
-- Gates
    toffoli record;
    cx record;
    gate record;

    -- Locked neighbours
    left_q3  record;
    right_q1 record;
    right_q2 record;
    right_q3 record;
    right_q4 record;

    -- Timing
    start_time timestamp;

    -- Gate type ids
    cx_type smallint;
    cxpow_type smallint;
    toffoli_types smallint[];

    -- Neighbour ids
    tof_prev_q3_id bigint;
    tof_next_q1_id bigint;
    tof_next_q2_id bigint;
    cx_next_q1_id bigint;
    cx_next_q2_id bigint;

    -- Encoded links
    cx_ctrl bigint;
    cx_tgt bigint;
    tof_ctrl_1 bigint;
    tof_ctrl_2 bigint;
    tof_tgt bigint;

    new_tof_ctrl_1 bigint;
    new_tof_ctrl_2 bigint;
    new_tof_tgt bigint;

    cx_right_q1 bigint;

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
                       and get_type_from_link(prev_q1) = any(toffoli_types) 
                       and get_port_from_link(prev_q1) = 2
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
            if get_id_from_link(cx.prev_q1) != toffoli.id
                or get_port_from_link(cx.prev_q1) != 2
                or not ((cx.type = cxpow_type and cx.param = 1) 
                    or(cx.type = cx_type and cx.param = 0)
                )
                or get_id_from_link(toffoli.next_q3) != cx.id
                or get_port_from_link(toffoli.next_q3) != 0
                or not (toffoli.type = any(toffoli_types))
            then
                commit;
                continue;
            end if;

            -- Compute the ids of the neighbours
            cx_next_q1_id := get_id_from_link(cx.next_q1);
            cx_next_q2_id := get_id_from_link(cx.next_q2);
            tof_next_q1_id := get_id_from_link(toffoli.next_q1);
            tof_next_q2_id := get_id_from_link(toffoli.next_q2);
            tof_prev_q3_id := get_id_from_link(toffoli.prev_q3);

            -- Attempt to lock the neighbours of the pair (left of first gate and right of second gate)
            select * into left_q3 from linked_circuit where id=tof_prev_q3_id for update skip locked;
            select * into right_q1 from linked_circuit where id=tof_next_q1_id for update skip locked;
            select * into right_q2 from linked_circuit where id=tof_next_q2_id for update skip locked;
            select * into right_q3 from linked_circuit where id=cx_next_q1_id for update skip locked;
            select * into right_q4 from linked_circuit where id=cx_next_q2_id for update skip locked;

            -- If locking the neighbours failed, commit and move to the next candidate pair
            if left_q3.id is null
                or right_q1.id is null
                or right_q2.id is null
                or right_q3.id is null
                or right_q4.id is null
            then
                commit;
                continue;
            end if;

            -- Compute new links to the pair
            cx_ctrl := create_link(cx.id, 0, cx.type);
            cx_tgt  := create_link(cx.id, 1, cx.type);
            tof_ctrl_1 := create_link(toffoli.id, 0, toffoli.type);
            tof_ctrl_2 := create_link(toffoli.id, 1, toffoli.type);
            tof_tgt := create_link(toffoli.id, 2, toffoli.type);

            --- Insert a new Toffoli gate 
            insert into linked_circuit(prev_q1, prev_q2, prev_q3, type, param, switch, next_q1, next_q2, next_q3, label)
            values (tof_ctrl_1, tof_ctrl_2, cx_tgt, 23, 1, false, toffoli.next_q1, toffoli.next_q2, cx.next_q2, cx.label)
            returning id, type 
            into new_tof_id, new_tof_type;

            -- Compute links to the new Toffoli gate
            new_tof_ctrl_1 := create_link(new_tof_id, 0, new_tof_type);
            new_tof_ctrl_2 := create_link(new_tof_id, 1, new_tof_type);
            new_tof_tgt := create_link(new_tof_id, 2, new_tof_type);

            -- Update links of the left and right neighbours 
            perform update_next_link(left_q3.id, get_port_from_link(toffoli.prev_q3), cx_ctrl);
            perform update_prev_link(right_q1.id, get_port_from_link(toffoli.next_q1), new_tof_ctrl_1);
            perform update_prev_link(right_q2.id, get_port_from_link(toffoli.next_q2), new_tof_ctrl_2);
            perform update_prev_link(right_q3.id, get_port_from_link(cx.next_q1), tof_tgt);
            perform update_prev_link(right_q4.id, get_port_from_link(cx.next_q2), new_tof_tgt);

            -- Update the target paor Toffoli and CNOT 
            cx_right_q1 := cx.next_q1;
            update linked_circuit set (prev_q1, next_q1, next_q2) = (toffoli.prev_q3, tof_tgt, new_tof_tgt) where id = cx.id; 
            update linked_circuit set (prev_q3, next_q1, next_q2, next_q3) = (cx_ctrl, new_tof_ctrl_1, new_tof_ctrl_2, cx_right_q1) where id = toffoli.id;
            
            commit; -- release the lock

        end loop; -- end gate loop

	    if extract(epoch from (clock_timestamp() - start_time)) > timeout then
            exit;
        end if;

        pass_count = pass_count - 1;

    end loop; --end pass loop
end;$$;

