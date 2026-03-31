-- which income bins have the highest default risk?

with amt_income_bins as (
    select 
        amt_income_total, 
        ntile(10) over (order by amt_income_total) as bin,
        target
    from application_train
) 
select 
    bin, 
    count(*) as total_num, 
    sum(target) as n_targets,
    sum(target) / count(*) * 100 as default_rate
from amt_income_bins 
group by bin 
order by default_rate desc;