-- what information is available about an applicats previous credit?

select 
    sk_id_curr, 
    sum(case when credit_active = 'Active' then 1 else 0 end) as num_active, 
    sum(AMT_CREDIT_SUM) as total_credit_all, 
    SUM(AMT_CREDIT_SUM_DEBT)                              AS total_debt,
    sum(case when credit_active = 'Active' then amt_credit_sum else 0 end) as total_active_credit,  
    max(credit_day_overdue) as max_days_overdue,
    max(AMT_CREDIT_MAX_OVERDUE) as max_dpd_ever -- not sure about this
from bureau 
group by SK_id_curr
order by total_active_credit desc;

