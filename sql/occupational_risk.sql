-- which occupations have the highest default risk?

select 
    OCCUPATION_TYPE, 
    count(*) as total_num, 
    sum(target) as n_targets,
    sum(target) / count(*) * 100 as default_rate
from application_train 
group by occupation_type 
order by default_rate desc;