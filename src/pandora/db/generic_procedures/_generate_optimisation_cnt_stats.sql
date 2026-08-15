create or replace procedure generate_optimisation_cnt_stats(sleep_for float, logid int, timeout int)
    language plpgsql
as
$$
declare
    total int;
    cx_cnt int;
    x_cnt int;
    ccx_cnt int;
    count int := 0;

    start_time timestamp;

    x_types smallint[];
    cx_types smallint[];
    ccx_types smallint[];
    

begin
    start_time := clock_timestamp();

    select array_agg(id) into x_types from gate_types where name = 'paulix';
    select array_agg(id) into ccx_types from gate_types where name in ('ccx', 'toffoli');
    select array_agg(id) into cx_types from gate_types where name in ('cx', 'cxpow');

    while true loop
        count := count + 1;

        select count(*) into total from linked_circuit;
        select count(*) into x_cnt from linked_circuit where type=any(x_types);
        select count(*) into cx_cnt from linked_circuit where type=any(cx_types);
        select count(*) into ccx_cnt from linked_circuit where type=any(ccx_types);

        insert into optimization_results_cnt(id, elapsed_time, logger_id, total_count, x_count, cx_count, ccx_count)
        values (count, extract(epoch from (clock_timestamp() - start_time)), logid, total, x_cnt, cx_cnt, ccx_cnt);

        if extract(epoch from (clock_timestamp() - start_time)) > timeout then
            exit;
        end if;
		-- perform pg_sleep(sleep_for);
	end loop;
    commit;
end;$$;
