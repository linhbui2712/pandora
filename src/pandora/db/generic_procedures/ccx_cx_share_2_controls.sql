-- Rule: Toffoli-CNOT commutation (Toffoli shares 2 control lines with CNOT)
-- Before:
-- q1: ───@───@───
--        │   │
-- q2: ───@───X───
--        │
-- q3: ───X───────
-- After:
-- q1: ───@───────@───────
--        │       │
-- q2: ───X───X───@───X───
--                │
-- q3: ───────────X───────

create or replace procedure ccx_cx_share_2_controls(pass_count int, timeout int)
--- create or replace procedure linked_tc_to_cntn(pass_count int, timeout int, run_nr int)
    language plpgsql
as
$$
declare
    toffoli record;
    cx record;

    tof_ctrl_left_1 bigint; -- prev link of CNOT control to Toffoli control 
    tof_ctrl_left_2 bigint; -- prev link of CNOT target to Toffoli control

    tof_prev_id_1 bigint;
    tof_prev_id_2 bigint;
    cx_next_q1_id bigint;
    cx_next_q2_id bigint;

    left_1 record; -- left neighbour of Toffoli control that is connected to CNOT control
    left_2 record; -- left neighbour of Toffoli control that is connected to CNOT target
    right_q1 record;
    right_q2 record;

    gate record;

    start_time timestamp;

    port_nr int;

    cx_type smallint;
    cxpow_type smallint;
    toffoli_types smallint[];
    x_type smallint;

    cx_next_q1 bigint;
    cx_next_q2 bigint;

    cx_ctrl bigint;
    cx_tgt bigint;
    tof_ctrl_1 bigint;
    tof_ctrl_2 bigint;

    x_1 bigint;
    x_2 bigint;

    x_1_link bigint;
    x_2_link bigint;

    cx_ctrl_port int;
    cx_tgt_port int;

begin
    port_nr := 0; -- single qubit gate has a single port with index 0
    start_time := clock_timestamp();
    select id into cx_type from gate_types where name = 'cx';
    select id into cxpow_type from gate_types where name = 'cxpow';
    select array_agg(id) into toffoli_types from gate_types where name in ('ccx', 'toffoli');    select id into x_type from gate_types where name = 'xpow';

    while pass_count > 0 loop
         -- loop through all CNOT gates that currently fit the pattern we are looking for:
        for gate in
            select * from linked_circuit
                     where
                       ((type = cxpow_type and param = 1) or (type = cx_type and param = 0))
                       and get_type_from_link(prev_q1) = any(toffoli_types) 
                       and get_type_from_link(prev_q2) = any(toffoli_types)
                       and get_id_from_link(prev_q1) = get_id_from_link(prev_q2)
                       and ((get_port_from_link(prev_q1) = 0 and get_port_from_link(prev_q2) = 1)
                        or (get_port_from_link(prev_q1) = 1 and get_port_from_link(prev_q2) = 0)
                       )
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
                or get_id_from_link(cx.prev_q2) != toffoli.id
                or get_id_from_link(toffoli.next_q1) != cx.id 
                or get_id_from_link(toffoli.next_q2) != cx.id
                or not ((cx.type = cxpow_type and cx.param = 1) 
                    or(cx.type = cx_type and cx.param = 0)
                )
                or not (toffoli.type = any(toffoli_types))
            then
                commit;
                continue;
            end if;

            -- Recheck the ports of the two gates to ensure they match the pattern we are looking for
            if get_port_from_link(cx.prev_q1) = 0 
                and get_port_from_link(cx.prev_q2) = 1 
                and get_port_from_link(toffoli.next_q1) = 0
                and get_port_from_link(toffoli.next_q2) = 1
            then
                tof_ctrl_left_1 := toffoli.prev_q1; 
                tof_ctrl_left_2 := toffoli.prev_q2;
                cx_ctrl_port := 0;
                cx_tgt_port := 1;
            elsif
                get_port_from_link(cx.prev_q1) = 1 
                and get_port_from_link(cx.prev_q2) = 0
                and get_port_from_link(toffoli.next_q1) = 1
                and get_port_from_link(toffoli.next_q2) = 0
            then
                tof_ctrl_left_1 := toffoli.prev_q2; 
                tof_ctrl_left_2 := toffoli.prev_q1;
                cx_ctrl_port := 1;
                cx_tgt_port := 0;
            else
                commit;
                continue;
            end if;

            -- Compute the ids of the neighbours
            cx_next_q1_id := get_id_from_link(cx.next_q1);
            cx_next_q2_id := get_id_from_link(cx.next_q2);
            tof_prev_id_1 := get_id_from_link(tof_ctrl_left_1);
            tof_prev_id_2 := get_id_from_link(tof_ctrl_left_2);
    
            -- Attempt to lock the neighbours of the pair (left of first gate and right of second gate)
            select * into left_1 from linked_circuit where id=tof_prev_id_1 for update skip locked;
            select * into left_2 from linked_circuit where id=tof_prev_id_2 for update skip locked;
            select * into right_q1 from linked_circuit where id=cx_next_q1_id for update skip locked;
            select * into right_q2 from linked_circuit where id=cx_next_q2_id for update skip locked;

            -- If locking the neighbours failed, commit and move to the next candidate pair
            if left_1.id is null
                or left_2.id is null
                or right_q1.id is null
                or right_q2.id is null
            then
                commit;
                continue;
            end if;

            -- Save the two right neighbour links
            cx_next_q1 := cx.next_q1;
            cx_next_q2 := cx.next_q2;

            -- Compute links to the Toffoli and CNOT gates
            cx_ctrl := create_link(cx.id, 0, cx.type);
            cx_tgt  := create_link(cx.id, 1, cx.type);
            tof_ctrl_1 := create_link(toffoli.id, cx_ctrl_port, toffoli.type);
            tof_ctrl_2 := create_link(toffoli.id, cx_tgt_port, toffoli.type);

            --- Insert 2 NOT gates after CNOT and after Toffolli
            insert into linked_circuit(prev_q1, type, next_q1, param, label) values (cx_tgt, x_type, tof_ctrl_2, 1, cx.label)
                                                          returning id into x_1;
            insert into linked_circuit(prev_q1, type, next_q1, param, label) values (tof_ctrl_2, x_type, cx.next_q2, 1, cx.label)
                                                          returning id into x_2;       
                                                          
            -- Create links to the new X gates
            x_1_link := create_link(x_1, port_nr, x_type);
            x_2_link := create_link(x_2, port_nr, x_type);

            -- Update links of the left and right neighbours 
            perform update_next_link(tof_prev_id_1, toffoli.prev_q1, cx_ctrl);
            perform update_next_link(tof_prev_id_2 , toffoli.prev_q2, cx_tgt);
            perform update_prev_link(cx_next_q1_id, cx.next_q1, tof_ctrl_1);
            perform update_prev_link(cx_next_q2_id, cx.next_q2, x_2_link);

            -- Update Toffoli and CNOT 
            update linked_circuit set (prev_q1, prev_q2, next_q1, next_q2) = (tof_ctrl_left_1, tof_ctrl_left_2, tof_ctrl_1, x_1_link) where id = cx.id; 
            if cx_ctrl_port = 0 then
                update linked_circuit set (prev_q1, prev_q2, next_q1, next_q2) = (cx_ctrl, cx_tgt, cx_next_q1, x_2_link) where id = toffoli.id;
            else
                update linked_circuit set (prev_q1, prev_q2, next_q1, next_q2) = (cx_tgt, cx_ctrl, x_2_link, cx_next_q2) where id = toffoli.id;
            end if;
            
            commit; -- release the lock

        end loop; -- end gate loop

	    if extract(epoch from (clock_timestamp() - start_time)) > timeout then
            exit;
        end if;

        pass_count = pass_count - 1;

    end loop; --end pass loop
end;$$;

