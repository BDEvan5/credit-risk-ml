select 
    SK_ID_PREV,
    count(*) as num_applications,
    sum(amt_application) as total_amount_applied,
    sum(amt_credit) as total_amount_credit,
    sum(case when amt_credit > 0 then 1 else 0 end) as num_successful_applications,
    num_successful_applications / num_applications as pct_successful, 
    case when pct_successful < 1.0 then 1 else 0 end as was_rejected,
    count(distinct CODE_REJECT_REASON) as num_unique_rejection_reasons,
    min(case when CODE_REJECT_REASON is not null then CODE_REJECT_REASON end) as first_rejection_reason
from previous_application
group by SK_ID_PREV