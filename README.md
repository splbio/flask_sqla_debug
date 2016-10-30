A class that can be used to debug flask's use of sqlalchemy.

The following things can be done:
Warn/throw an exception when queries are taking too long.
Log queries being generated using python's `with` syntax.
Warn/throw when too many queries are generated inside of a request.
Provide some simple stats on your endpoint's query count and latency.

This is handy because you will get a stack trace including the requesting url when you exceed latency
and query count thresholds.

