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

    tof_prev_q1_id bigint;
    tof_prev_q2_id bigint;
    cx_next_q1_id bigint;
    cx_next_q2_id bigint;

    left_q1 record;
    left_q2 record;
    right_q1 record;
    right_q2 record;

    gate record;

    start_time timestamp;

    port_nr int;

    cx_type smallint;
    toffoli_type smallint;
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
    port_nr := 0;
    start_time := clock_timestamp();
    select id into cx_type from gate_types where name = 'cxpow';
    select id into toffoli_type from gate_types where name = 'ccx';
    select id into x_type from gate_types where name = 'xpow';

    while pass_count > 0 loop
        for gate in
            select * from linked_circuit
                     where
                       type = cx_type 
                       and get_type_from_link(prev_q1) = toffoli_type 
                       and get_type_from_link(prev_q2) = toffoli_type
                       and get_id_from_link(prev_q1) = get_id_from_link(prev_q2)
                       and param = 1
                       and ((get_port_from_link(prev_q1) = 0 and get_port_from_link(prev_q2) = 1)
                        or (get_port_from_link(prev_q1) = 1 and get_port_from_link(prev_q2) = 0)
                       )
                       -- and partition_id = my_partition
        loop 
            select * into cx from linked_circuit where id = gate.id for update skip locked;
            select * into toffoli from linked_circuit where id = get_id_from_link(cx.prev_q1) for update skip locked;

            if cx.id is null
                or toffoli.id is null
                or cx.type != cx_type
                or toffoli.type != toffoli_type
                or cx.param != 1
            then
                commit;
                continue;
            end if;

            -- cnot must still connect to the same toffoli
            if get_id_from_link(cx.prev_q1) != toffoli.id
                or get_id_from_link(cx.prev_q2) != toffoli.id
            then
                commit;
                continue;
            end if;

            -- both cnot links must connect to the control ports of the toffoli
            if not (
                (get_port_from_link(cx.prev_q1) = 0 and get_port_from_link(cx.prev_q2) = 1)
                or (get_port_from_link(cx.prev_q1) = 1 and get_port_from_link(cx.prev_q2) = 0)
                )
            then
                commit;
                continue;
            end if;

            -- Compute the ids of the neighbours
            cx_next_q1_id := get_id_from_link(cx.next_q1);
            cx_next_q2_id := get_id_from_link(cx.next_q2);

            tof_prev_q1_id := get_id_from_link(toffoli.prev_q1);
            tof_prev_q2_id := get_id_from_link(toffoli.prev_q2);
        
            -- Lock the neighbour rows for update
            select * into left_q1 from linked_circuit where id=tof_prev_q1_id for update skip locked;
            select * into left_q2 from linked_circuit where id=tof_prev_q2_id for update skip locked;
            select * into right_q1 from linked_circuit where id=cx_next_q1_id for update skip locked;
            select * into right_q2 from linked_circuit where id=cx_next_q2_id for update skip locked;
        
            if left_q1.id is null
                or left_q2.id is null
                or right_q1.id is null
                or right_q2.id is null
            then
                commit;
                continue;
            end if;

            cx_next_q1 = cx.next_q1;
            cx_next_q2 = cx.next_q2;

            -- compute new links for the pair and neighbouring gates 
            cx_ctrl := create_link(cx.id, 0, cx.type);
            cx_tgt  := create_link(cx.id, 1, cx.type);
            tof_ctrl_1 := create_link(toffoli.id, 0, toffoli.type);
            tof_ctrl_2 := create_link(toffoli.id, 1, toffoli.type);

            -- update left and right links (exept for right_q2, which will be updated by the new X gate)
            if get_port_from_link(toffoli.prev_q1) = 0 then
                update linked_circuit set next_q1 = cx_ctrl where id = tof_prev_q1_id;
            elsif get_port_from_link(toffoli.prev_q1) = 1 then
                update linked_circuit set next_q2 = cx_ctrl where id = tof_prev_q1_id;
            else
                update linked_circuit set next_q3 = cx_ctrl where id = tof_prev_q1_id;
            end if;

            if get_port_from_link(toffoli.prev_q2) = 0 then
                update linked_circuit set next_q1 = cx_tgt where id = tof_prev_q2_id;
            elsif get_port_from_link(toffoli.prev_q2) = 1 then
                update linked_circuit set next_q2 = cx_tgt where id = tof_prev_q2_id;
            else
                update linked_circuit set next_q3 = cx_tgt where id = tof_prev_q2_id;
            end if;

            if get_port_from_link(cx.next_q1) = 0 then
                update linked_circuit set prev_q1 = tof_ctrl_1 where id = cx_next_q1_id;
            elsif get_port_from_link(cx.next_q1) = 1 then
                update linked_circuit set prev_q2 = tof_ctrl_1 where id = cx_next_q1_id;
            else
                update linked_circuit set prev_q3 = tof_ctrl_1 where id = cx_next_q1_id;
            end if;
            
           --- insert two X gates 
            insert into linked_circuit(prev_q1, type, next_q1, param, label) values (cx_tgt, x_type, tof_ctrl_2, 1, cx.label)
                                                          returning id into x_1;
            insert into linked_circuit(prev_q1, type, next_q1, param, label) values (tof_ctrl_2, x_type, cx.next_q2, 1, cx.label)
                                                          returning id into x_2;       
                                                          
            -- These are the links that the Toffoli and CNOT should use
            x_1_link := create_link(x_1, port_nr, x_type);
            x_2_link := create_link(x_2, port_nr, x_type);

            -- Update Toffoli and CNOT
            update linked_circuit set (prev_q1, prev_q2, next_q1, next_q2) = (toffoli.prev_q1, toffoli.prev_q2, tof_ctrl_1, x_1_link) where id = cx.id; 
            update linked_circuit set (prev_q1, prev_q2, next_q1, next_q2) = (cx_ctrl, x_1_link, cx_next_q1, x_2_link) where id = toffoli.id;

            -- Update the right_q2 link to point to the new X gate
            if get_port_from_link(cx.next_q2) = 0 then
                update linked_circuit set prev_q1 = x_2_link where id = cx_next_q2_id;
            else
                update linked_circuit set prev_q2 = x_2_link where id = cx_next_q2_id;
            end if;
            
            commit; -- release the lock

        end loop; -- end gate loop

	    if extract(epoch from (clock_timestamp() - start_time)) > timeout then
            exit;
        end if;

        pass_count = pass_count - 1;

    end loop; --end pass loop
end;$$;

