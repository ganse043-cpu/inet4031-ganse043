# Week 11 Data Plan

## Data source and approach

I will use Approach B, the Python pipeline. I will generate 12,000
synthetic Harborlight Logistics support tickets across 16 weeks and load
them into a separate PostgreSQL table named `capstone_tickets`. This
keeps the capstone dataset separate from the Flask app's `tickets` table.
I will use a fixed random seed and snapshot date so I can reproduce the
same dataset. A reload will replace the capstone rows to avoid duplicates.

I will export the capstone table using `psql` and use Python to validate
the exported rows. In Week 12, the Python pipeline will use the export
to produce the summary tables, charts, and statistical check.

## Categories and resolution times

The generator will assign every ticket to one of five categories:
scanners and handhelds, dispatch app, printers and labels, logins and
access, or network. Each category will have its own list of ticket titles
and typical resolution duration.

The generator will create more tickets on weekdays and during business
hours, with a gradual increase in weekly volume. Tickets that resolve by
the snapshot date will be marked closed and have a `resolved_at`
timestamp. Open and in-progress tickets will have a blank `resolved_at`.
For closed tickets, elapsed resolution time is the difference between
`created_at` and `resolved_at`.

## Data quality and limitations

I will verify that the exported dataset has at least 10,000 rows, spans
at least 90 days, includes a category on every row, and includes a valid
resolution timestamp for every closed ticket. I will record the results
in `output/data_quality.csv`.

The ticket volume, categories, and resolution times are simulated and
contain no real customer information. The analysis will show whether
the pipeline can recover the patterns built into the dataset. Elapsed
resolution time includes waiting, so the staffing analysis will use a
separate assumption for how much time an agent spends working on a ticket.