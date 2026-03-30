CREATE OR REPLACE TABLE application_train AS
SELECT * FROM read_csv_auto('data/application_train.csv');

CREATE OR REPLACE TABLE application_test AS
SELECT * FROM read_csv_auto('data/application_test.csv');

CREATE OR REPLACE TABLE bureau AS
SELECT * FROM read_csv_auto('data/bureau.csv');

CREATE OR REPLACE TABLE bureau_balance AS
SELECT * FROM read_csv_auto('data/bureau_balance.csv');

CREATE OR REPLACE TABLE previous_application AS
SELECT * FROM read_csv_auto('data/previous_application.csv');

CREATE OR REPLACE TABLE POS_CASH_balance AS SELECT * FROM read_csv_auto('data/POS_CASH_balance.csv');

CREATE OR REPLACE TABLE installments_payments AS SELECT * FROM read_csv_auto('data/installments_payments.csv');

CREATE OR REPLACE TABLE credit_card_balance AS SELECT * FROM read_csv_auto('data/credit_card_balance.csv'); 

