-- Rule: Toffoli-CNOT commutation (Toffoli control = CNOT target, Toffoli target = CNOT control)
-- Before:
-- q1: ───@───X───
--        │   │
-- q2: ───@───┼───
--        │   │
-- q3: ───X───@───
-- After:
-- q1: ───X───@───X───@───
--        │   │   │   │
-- q2: ───┼───@───@───@───
--        │   │   │   │
-- q3: ───@───X───@───X───
create or replace procedure commute_ccx_cx_share_2_mixed(pass_count int, timeout int)
--- create or replace procedure linked_tc_to_cntn(pass_count int, timeout int, run_nr int)
    language plpgsql
as
$$
declare
    toffoli record;
    cx record;

    tof_prev_c_id bigint;
    tof_prev_t_id bigint;
    tof_next_c_id bigint;
    cx_next_c_id bigint;
    cx_next_t_id bigint;

    left_c record;
    left_t record;
    right_c_tof record;
    right_t record;
    right_c_cx record;

    gate record;

    start_time timestamp;

    ctrl_port int;

    cx_type smallint;
    cxpow_type smallint;
    toffoli_types smallint[];

    cx_next_c bigint;
    cx_next_t bigint;

    tof_ctrl_left_link bigint;
    tof_ctrl_right_link bigint;
    cx_ctrl bigint;
    cx_tgt bigint;
    tof_ctrl_1 bigint;
    tof_ctrl_2 bigint;
    tof_tgt bigint;

    new_tof_type smallint := 23;

    new_tof_id_1 bigint;
    new_tof_id_2 bigint;
    new_tof_1_ctrl_1 bigint;
    new_tof_1_ctrl_2 bigint;
    new_tof_1_tgt bigint;
    new_tof_2_ctrl_1 bigint;
    new_tof_2_ctrl_2 bigint;
    new_tof_2_tgt bigint;
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
                       and get_type_from_link(prev_q2) = any(toffoli_types)
                       and get_id_from_link(prev_q1) = get_id_from_link(prev_q2)
                       and get_port_from_link(prev_q1) = 2
                       and get_port_from_link(prev_q2) in (0, 1)
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
                or get_port_from_link(cx.prev_q1) != 2
                or get_id_from_link(toffoli.next_q3) != cx.id
                or get_port_from_link(toffoli.next_q3) != 0
                or not ((cx.type = cxpow_type and cx.param = 1) 
                    or(cx.type = cx_type and cx.param = 0)
                )
                or not (toffoli.type = any(toffoli_types))
            then
                commit;
                continue;
            end if;

            -- Recheck if Toffoli control = CNOt target
            ctrl_port := get_port_from_link(cx.prev_q2);
            if ctrl_port = 0 -- control port of Toffoli that is shared with CNOT target 
                and get_id_from_link(toffoli.next_q1) = cx.id
                and get_port_from_link(toffoli.next_q1) = 1
            then 
                tof_ctrl_left_link := toffoli.prev_q1; -- left neighbour of Toffoli control that is shared with CNOT target
                tof_ctrl_right_link := toffoli.next_q2; -- right neighbour of Toffoli control that is not shared with CNOT target
            elsif ctrl_port = 1 
                and get_id_from_link(toffoli.next_q2) = cx.id
                and get_port_from_link(toffoli.next_q2) = 1
            then 
                tof_ctrl_left_link := toffoli.prev_q2; 
                tof_ctrl_right_link := toffoli.next_q1;
            else
                commit;
                continue;
            end if;
    
            -- Compute the ids of the neighbours
            cx_next_c_id := get_id_from_link(cx.next_q1);
            cx_next_t_id := get_id_from_link(cx.next_q2);

            tof_prev_c_id := get_id_from_link(tof_ctrl_left_link);
            tof_prev_t_id := get_id_from_link(toffoli.prev_q3);
            tof_next_c_id := get_id_from_link(tof_ctrl_right_link);
        
            -- Attempt to lock the neighbours of the pair (left of first gate and right of second gate)
            select * into left_c from linked_circuit where id = tof_prev_c_id for update skip locked;
            select * into left_t from linked_circuit where id = tof_prev_t_id for update skip locked;
            select * into right_c_cx from linked_circuit where id = cx_next_c_id for update skip locked;
            select * into right_t from linked_circuit where id = cx_next_t_id for update skip locked;
            select * into right_c_tof from linked_circuit where id = tof_next_c_id for update skip locked;

            -- If locking the neighbours failed, commit and move to the next candidate pair
            if left_c.id is null
                or left_t.id is null
                or right_c_cx.id is null
                or right_t.id is null
                or right_c_tof.id is null
            then
                commit;
                continue;
            end if;
            
            -- Compute new links for the candidate and neighbouring gates 
            cx_ctrl := create_link(cx.id, 0, cx.type);
            cx_tgt  := create_link(cx.id, 1, cx.type);
            tof_ctrl_1 := create_link(toffoli.id, ctrl_port, toffoli.type); -- link to shared control of Toffoli
            tof_ctrl_2 := create_link(toffoli.id, 1 - ctrl_port, toffoli.type); -- link to independent control of Toffoli
            tof_tgt := create_link(toffoli.id, 2, toffoli.type);

            
            --- Insert 2 new Toffoli gates for the replacement

            -- the new Toffoli following the original Toffoli gate (Toffoli 1)
            insert into linked_circuit(prev_q1, prev_q2, prev_q3, type, param, switch, next_q1, next_q2, next_q3, label)
            values (tof_ctrl_2, tof_tgt, tof_ctrl_1, new_tof_type, 1, false, null, null, null, cx.label)
            returning id 
            into new_tof_id_1;

            new_tof_1_ctrl_1 := create_link(new_tof_id_1, 0, new_tof_type);
            new_tof_1_ctrl_2 := create_link(new_tof_id_1, 1, new_tof_type);
            new_tof_1_tgt := create_link(new_tof_id_1, 2, new_tof_type);    

            -- the new Toffoli following Toffoli 1 (Toffoli 2)
            insert into linked_circuit(prev_q1, prev_q2, prev_q3, type, param, switch, next_q1, next_q2, next_q3, label)
            values (new_tof_1_ctrl_1, new_tof_1_tgt, new_tof_1_ctrl_2, new_tof_type, 1, false, tof_ctrl_right_link, cx.next_q2, cx.next_q1, cx.label)
            returning id 
            into new_tof_id_2;

            new_tof_2_ctrl_1 := create_link(new_tof_id_2, 0, new_tof_type);
            new_tof_2_ctrl_2 := create_link(new_tof_id_2, 1, new_tof_type);
            new_tof_2_tgt := create_link(new_tof_id_2, 2, new_tof_type);  

            update linked_circuit set next_q1 = new_tof_2_ctrl_1, next_q2 = new_tof_2_tgt, next_q3 = new_tof_2_ctrl_2 where id = new_tof_id_1;

            -- Update links of the left and right neighbours 
            perform update_next_link(tof_prev_c_id, tof_ctrl_left_link, cx_tgt);
            perform update_next_link(tof_prev_t_id, toffoli.prev_q3, cx_ctrl);
            perform update_prev_link(cx_next_c_id, cx.next_q1, new_tof_2_tgt);
            perform update_prev_link(cx_next_t_id, cx.next_q2, new_tof_2_ctrl_2);
            perform update_prev_link(tof_next_c_id, tof_ctrl_right_link, new_tof_2_ctrl_1);

            -- Update Toffoli and CNOT 
            update linked_circuit set (prev_q1, prev_q2, next_q1, next_q2) = (toffoli.prev_q3, tof_ctrl_left_link, tof_tgt, tof_ctrl_1) where id = cx.id;

            if ctrl_port = 0 then
                update linked_circuit set (prev_q1, prev_q3, next_q1, next_q2, next_q3) = (cx_tgt, cx_ctrl, new_tof_1_tgt, new_tof_1_ctrl_1, new_tof_1_ctrl_2) where id = toffoli.id;
            else
                update linked_circuit set (prev_q2, prev_q3, next_q1, next_q2, next_q3) = (cx_tgt, cx_ctrl, new_tof_1_ctrl_1, new_tof_1_tgt, new_tof_1_ctrl_2) where id = toffoli.id;

            end if;

            
            commit; -- release the lock

        end loop; -- end gate loop

	    if extract(epoch from (clock_timestamp() - start_time)) > timeout then
            exit;
        end if;

        pass_count = pass_count - 1;

    end loop; --end pass loop
end;$$;

