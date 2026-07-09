-- Rule: Toffoli-CNOT commutation (Toffoli and CNOT share 1 one control and 1 target)
-- Before:
-- q1: ───@───@───
--        │   │
-- q2: ───@───┼───
--        │   │
-- q3: ───X───X───
-- After:
-- q1: ───@───@───
--        │   │
-- q2: ───┼───@───
--        │   │
-- q3: ───X───X───


create or replace procedure ccx_cx_commute(pass_count int, timeout int)
--- create or replace procedure ccx_cx_commute(pass_count int, timeout int, run_nr int)
    language plpgsql
as
$$
declare
    toffoli record;
    cx record;

    tof_prev_c_id bigint;
    tof_prev_t_id bigint;
    cx_next_c_id bigint;
    cx_next_t_id bigint;

    left_c record;
    left_t record;
    right_c record;
    right_t record;

    gate record;

    start_time timestamp;

    ctrl_port smallint;

    cx_type smallint;
    cxpow_type smallint;
    toffoli_types smallint[];

    cx_next_c bigint;
    cx_next_t bigint;

    tof_ctrl_left_link bigint;
    cx_ctrl bigint;
    cx_tgt bigint;
    tof_ctrl bigint;
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
                       and get_type_from_link(prev_q1) = any(toffoli_types) 
                       and get_type_from_link(prev_q2) = any(toffoli_types)
                       and get_id_from_link(prev_q1) = get_id_from_link(prev_q2)
                       and get_port_from_link(prev_q1) in (0, 1)
                       and get_port_from_link(prev_q2) = 2
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
                or not ((cx.type = cxpow_type and cx.param = 1) 
                    or(cx.type = cx_type and cx.param = 0)
                )
                or not (toffoli.type = any(toffoli_types))
            then
                commit;
                continue;
            end if;

            ctrl_port := get_port_from_link(cx.prev_q1);
            if ctrl_port = 0 then
                tof_ctrl_left_link := toffoli.prev_q1;                
            else
                tof_ctrl_left_link := toffoli.prev_q2;
            end if;

            -- Both gates must still share the same control and target lines
            ctrl_port := get_port_from_link(cx.prev_q1);
            if not (ctrl_port in (0, 1) and get_port_from_link(cx.prev_q2) = 2)
            then
                commit;
                continue;
            end if;

            if ctrl_port = 0 then
                tof_ctrl_left_link := toffoli.prev_q1;                
            else
                tof_ctrl_left_link := toffoli.prev_q2;
            end if;


            -- Compute the ids of the neighbours
            cx_next_c_id := get_id_from_link(cx.next_q1);
            cx_next_t_id := get_id_from_link(cx.next_q2);

            tof_prev_c_id := get_id_from_link(tof_ctrl_left_link);
            tof_prev_t_id := get_id_from_link(toffoli.prev_q3);
        
            -- Attempt to lock the neighbours of the pair (left of first gate and right of second gate)
            select * into left_c from linked_circuit where id = tof_prev_c_id for update skip locked;
            select * into left_t from linked_circuit where id = tof_prev_t_id for update skip locked;
            select * into right_c from linked_circuit where id = cx_next_c_id for update skip locked;
            select * into right_t from linked_circuit where id = cx_next_t_id for update skip locked;

            -- If locking the neighbours failed, commit and move to the next candidate pair
            if left_c.id is null
                or left_t.id is null
                or right_c.id is null
                or right_t.id is null
            then
                commit;
                continue;
            end if;

            -- Save the two right neighbour links
            cx_next_c := cx.next_q1;
            cx_next_t := cx.next_q2;

            -- Compute new links for the pair and neighbouring gates 
            cx_ctrl := create_link(cx.id, 0, cx.type);
            cx_tgt  := create_link(cx.id, 1, cx.type);
            tof_ctrl := create_link(toffoli.id, ctrl_port, toffoli.type);
            tof_tgt := create_link(toffoli.id, 2, toffoli.type);

            -- Update links of the left and right neighbours 
            if get_port_from_link(tof_ctrl_left_link) = 0 then
                update linked_circuit set next_q1 = cx_ctrl where id = tof_prev_c_id;
            elsif get_port_from_link(tof_ctrl_left_link) = 1 then
                update linked_circuit set next_q2 = cx_ctrl where id = tof_prev_c_id;
            else
                update linked_circuit set next_q3 = cx_ctrl where id = tof_prev_c_id;
            end if;

            if get_port_from_link(toffoli.prev_q3) = 0 then
                update linked_circuit set next_q1 = cx_tgt where id = tof_prev_t_id;
            elsif get_port_from_link(toffoli.prev_q3) = 1 then
                update linked_circuit set next_q2 = cx_tgt where id = tof_prev_t_id;
            else
                update linked_circuit set next_q3 = cx_tgt where id = tof_prev_t_id;
            end if;

            if get_port_from_link(cx.next_q1) = 0 then
                update linked_circuit set prev_q1 = tof_ctrl where id = cx_next_c_id;
            elsif get_port_from_link(cx.next_q1) = 1 then
                update linked_circuit set prev_q2 = tof_ctrl where id = cx_next_c_id;
            else
                update linked_circuit set prev_q3 = tof_ctrl where id = cx_next_c_id;
            end if;

            if get_port_from_link(cx.next_q2) = 0 then
                update linked_circuit set prev_q1 = tof_tgt where id = cx_next_t_id;
            elsif get_port_from_link(cx.next_q2) = 1 then
                update linked_circuit set prev_q2 = tof_tgt where id = cx_next_t_id;
            else
                update linked_circuit set prev_q3 = tof_tgt where id = cx_next_t_id;
            end if;  
                                                          
            -- Update Toffoli and CNOT 
            update linked_circuit set (prev_q1, prev_q2, next_q1, next_q2) = (tof_ctrl_left_link, toffoli.prev_q3, tof_ctrl, tof_tgt) where id = cx.id;
            
            if ctrl_port = 0 then
                update linked_circuit set (prev_q1, prev_q3, next_q1, next_q3) = (cx_ctrl, cx_tgt, cx_next_c, cx_next_t) where id = toffoli.id;
            else
                update linked_circuit set (prev_q2, prev_q3, next_q2, next_q3) = (cx_ctrl, cx_tgt, cx_next_c, cx_next_t) where id = toffoli.id;
            end if;

            commit; -- release the lock

        end loop; -- end gate loop

	    if extract(epoch from (clock_timestamp() - start_time)) > timeout then
            exit;
        end if;

        pass_count = pass_count - 1;

    end loop; --end pass loop
end;$$;

