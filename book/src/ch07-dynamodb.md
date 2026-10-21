# Amazon DynamoDB

> **In this chapter**
> - The data model, primary keys and partition-key design
> - Capacity modes and **RCU/WCU math**, throttling, consistency
> - The API: Get/Put/Update/Delete, batch operations, Query vs Scan, expressions, pagination
> - Conditional writes, optimistic locking, atomic counters, transactions
> - LSI vs GSI, TTL, Streams, DAX, global tables, backups, security
>
> **Exam weight**: Domain 1 Task 1.3 (heavily tested), plus Domains 2 and 4
> · **Exercises**: `ddb_1`–`ddb_9` · **Quiz**: `uv run awslings quiz dynamodb`

## Data model

- A **table** holds **items** (rows, max **400 KB** each, attribute names included), made of **attributes**.
- Only the **primary key** is mandatory and fixed. Everything else is schemaless.
  - **Simple key**: a **partition key** (e.g. `user_id`).
  - **Composite key**: **partition key + sort key** (e.g. `customer_id` + `order_date`). Items with
    the same partition key form an *item collection*, stored together and sorted by sort key.
- Types: scalars `S`, `N`, `B`, `BOOL`, `NULL`. Documents `M` (map), `L` (list). Sets `SS`, `NS`, `BS`.
  The low-level API uses typed JSON (`{"S": "abc"}`). The boto3 `Table` resource converts for you,
  with numbers as `Decimal` (floats are rejected, see exercise `res_2`).

### Partition key design

DynamoDB hashes the partition key to spread items over **partitions**. Throughput is spread too,
so the key decides scalability:

- Use **high-cardinality** keys accessed fairly evenly: `user_id`, `order_id`, `device_id`.
- Avoid **hot partitions**: a `status` or a date as partition key concentrates traffic on a few values.
- For write-heavy hot keys, use **write sharding**: append a suffix (`2026-10-21#7`, with a random or
  computed suffix in 0–9) and query all suffixes when reading.
- Sort keys enable hierarchical queries: `COUNTRY#CITY#STORE`, `ORDER#2026-10-21T10:00:00Z`, so
  `begins_with` and ranges work.

> **Exam tip** — "Throttling even though total consumed capacity is far below provisioned capacity"
> → a **hot partition**. Fix the key design (higher cardinality, sharding). Adaptive capacity helps
> but does not fix a bad key.

## Capacity modes

| | **Provisioned** | **On-demand** |
|---|---|---|
| You pay for | RCU/WCU per hour, whether used or not | Each read/write request |
| Scaling | **Auto scaling** (target utilization) or manual. Reserved capacity discounts | Instant, automatic. Adapts to traffic up to double the previous peak quickly |
| Best for | Predictable, steady traffic → cheaper | Unknown, spiky, new workloads, or low/irregular traffic |

### Capacity math (memorize this)

| Unit | Definition |
|---|---|
| **1 RCU** | 1 **strongly consistent** read/s of an item up to **4 KB**, **or** 2 **eventually consistent** reads/s up to 4 KB, **or** ½ transactional read/s |
| **1 WCU** | 1 write/s of an item up to **1 KB**. Transactional writes cost 2 WCU per KB |

Sizes are **rounded up**: 4 KB blocks for reads, 1 KB blocks for writes.

```text
Read 10 items/s of 6 KB, strongly consistent  → ceil(6/4) = 2 units × 10 = 20 RCU
Same, eventually consistent                    → 20 / 2                    = 10 RCU
Same, transactional                            → 20 × 2                    = 40 RCU
Write 10 items/s of 2.5 KB                     → ceil(2.5) = 3 units × 10  = 30 WCU
Read 3 items/s of 1 KB, eventually consistent  → 1 × 3 / 2 = 1.5          → 2 RCU
```

- Throttling raises **`ProvisionedThroughputExceededException`** (or `ThrottlingException`). The SDK retries with
  exponential backoff. **Burst capacity** (unused capacity saved for up to 5 minutes) and **adaptive
  capacity** absorb short spikes and uneven access.
- A **Query/Scan** consumes capacity for the data **read**, before any `FilterExpression`.
- `ReturnConsumedCapacity="TOTAL"` shows what a request cost.

### Consistency

- Reads are **eventually consistent** by default (half the cost), and usually consistent within a second.
- `ConsistentRead=True` gives **strongly consistent** reads on tables and LSIs, **not on GSIs**
  (and not across Regions in global tables).

## The core API

| Operation | Notes |
|---|---|
| `PutItem` | Creates or **replaces** the whole item |
| `UpdateItem` | Modifies attributes, creates the item if missing (upsert). `UpdateExpression` with `SET`, `REMOVE`, `ADD` (numbers and sets), `DELETE` (remove from a set) |
| `GetItem` | Needs the **full** primary key. `ProjectionExpression` limits the attributes returned |
| `DeleteItem` | Optional condition |
| `BatchGetItem` | Up to **100 items / 16 MB**, multiple tables. Returns `UnprocessedKeys` |
| `BatchWriteItem` | Up to **25** put/delete requests / 16 MB. **No updates, no conditions, not atomic**. Returns `UnprocessedItems`, which you must retry with backoff (exercise `ddb_7`) |
| `Query` | One partition key value (+ sort key condition `=, <, <=, >, >=, BETWEEN, begins_with`), sorted by sort key (`ScanIndexForward=False` for descending) |
| `Scan` | Reads the **whole** table/index. Use rarely, with `Limit`, or **parallel scan** (`Segment`/`TotalSegments`) for bulk jobs |
| `ExecuteStatement` | **PartiQL** (SQL-compatible syntax) over the same operations |

Expressions use placeholders: `ExpressionAttributeNames` (`#s` → `status`, **required for reserved
words** such as `status`, `name`, `date`, `data`, `count`, `views`...) and `ExpressionAttributeValues`
(`:v`). `ReturnValues`: `NONE`, `ALL_OLD`, `UPDATED_OLD`, `ALL_NEW`, `UPDATED_NEW`.

```python
from boto3.dynamodb.conditions import Key

resp = table.query(
    KeyConditionExpression=Key("customer_id").eq("c-1") & Key("order_date").gte("2026-10-01"),
    ProjectionExpression="order_id, total",
    Limit=50,
)
while "LastEvaluatedKey" in resp:                       # results are paginated (1 MB per page)
    resp = table.query(..., ExclusiveStartKey=resp["LastEvaluatedKey"])
```

> **Trap** — `FilterExpression` does **not** reduce consumed RCU: the items are read, then filtered.
> To read less, design a key or index that lets you **Query** exactly what you need.
> `ProjectionExpression` reduces the network payload, not the RCU.

## Conditional writes and concurrency

- **Idempotent create**: `ConditionExpression="attribute_not_exists(pk)"` fails with
  `ConditionalCheckFailedException` if the item exists (idempotency keys, exercise `lambda_5`).
- **Optimistic locking**: store a `version` number, write with `ConditionExpression="version = :expected"`
  and `SET version = :expected + 1`. A failed condition means someone else updated the item first,
  so reload and retry (exercise `ddb_5`).
- **Atomic counters**: `UpdateExpression="ADD view_count :one"` (or `SET n = if_not_exists(n, :zero) + :one`).
  Never read-modify-write in code (exercise `ddb_6`).

## Transactions

`TransactWriteItems` / `TransactGetItems`: up to **100 actions** (Put, Update, Delete,
ConditionCheck) across tables, **4 MB**, all-or-nothing (ACID), in the same account and Region.

- Cost: **2×** the normal read/write capacity.
- Failure: `TransactionCanceledException` with `CancellationReasons` (one entry per action, e.g.
  `ConditionalCheckFailed`, `TransactionConflict`).
- `ClientRequestToken` makes the call idempotent for 10 minutes.
- Use cases: transfers between accounts, an order plus stock decrement, enforcing uniqueness of several attributes (exercise `ddb_8`).

## Secondary indexes

| | **Local secondary index (LSI)** | **Global secondary index (GSI)** |
|---|---|---|
| Key | **Same partition key**, different sort key | **Any** partition key and sort key |
| Created | **Only at table creation** | Any time (backfilled) |
| Max per table | 5 | 20 (default quota) |
| Consistency | Eventual **or strong** | **Eventual only** |
| Capacity | Shares the table's capacity | **Its own** capacity (provisioned mode). A throttled GSI **throttles writes on the table** |
| Size limit | 10 GB per partition key value (item collection) | None |

- **Projection**: `KEYS_ONLY`, `INCLUDE` (selected attributes), or `ALL`. Querying an attribute that is not
  projected costs a fetch from the table (LSI) or is impossible (GSI).
- **Sparse indexes**: only items that have the index key attributes appear in the GSI. That makes a cheap
  "flag" pattern (e.g. only `OPEN` tickets carry `open_since`).
- Query an index with `IndexName=...` (exercise `ddb_4`).

> **Exam tip** — "Need a new query pattern on an existing table" → **GSI** (LSIs cannot be added
> later). "Need strongly consistent reads on an alternate sort key" → **LSI** (decided at creation).

## Time To Live (TTL)

Choose a **Number** attribute holding an **epoch timestamp in seconds**. DynamoDB deletes expired
items in the background **at no cost** (no WCU consumed), typically **within a few days** of expiry.
Until then they can still be read, so filter them out if it matters. TTL deletions appear in Streams
as service deletions. Typical uses: sessions, temporary tokens, idempotency records, old events.

## DynamoDB Streams

- An ordered (per item) log of item-level changes, kept **24 hours**.
- **Stream view types**: `KEYS_ONLY`, `NEW_IMAGE`, `OLD_IMAGE`, `NEW_AND_OLD_IMAGES` (needed to compare before/after).
- Consumed by **Lambda** (event source mapping: batch size, bisect, retries, on-failure destination)
  or the KCL adapter. Uses: triggers (send a welcome email on INSERT), aggregations, syncing a search
  index, cross-Region replication (global tables use streams).
- Alternative: **Kinesis Data Streams for DynamoDB** (longer retention, more consumers, Firehose delivery).

## DAX — DynamoDB Accelerator

- An in-memory, **write-through** cache cluster in your VPC, **API-compatible** with DynamoDB (swap the
  client, no other code change). Reads in **microseconds**.
- **Item cache** (GetItem/BatchGetItem) and **query cache** (Query/Scan results). Default TTL 5 minutes.
- Only helps **eventually consistent** reads. Strongly consistent reads pass through to DynamoDB.
- Not useful for write-heavy or rarely-read data.

> **Exam tip** — "Read-heavy DynamoDB app needs microsecond latency **with minimal code changes**" →
> **DAX**. "Cache computed results/aggregations, or data from several sources" → **ElastiCache** (chapter 8).

## Global tables, backups, import/export

- **Global tables**: multi-Region, multi-active replication (typically within a second), last writer
  wins, for low-latency global apps and disaster recovery.
- **On-demand backups** (full, kept until deleted) and **point-in-time recovery (PITR)** (any second of the
  last 35 days). A restore always creates a **new table**.
- **Export to S3** (from PITR, consumes no table capacity) for analytics with Athena. **Import from S3** creates a new table.

## Security

- **Encryption at rest is always on**: AWS owned key (default), AWS managed key (`aws/dynamodb`), or a customer managed KMS key.
- **Fine-grained access control** with IAM conditions:
  - `dynamodb:LeadingKeys`: users can only touch items whose partition key equals their id
    (e.g. `${cognito-identity.amazonaws.com:sub}` or `${aws:PrincipalTag/...}`),
  - `dynamodb:Attributes`: restrict the attributes that can be read or written.
- Private access from a VPC with a **gateway endpoint**. CloudTrail logs control-plane calls (data-plane events optionally).

## Hands-on

| Exercise | Skill |
|---|---|
| `ddb_1` | RCU/WCU calculations |
| `ddb_2` | CRUD, composite keys, reserved words, ReturnValues |
| `ddb_3` | Query with key conditions and pagination (no Scan) |
| `ddb_4` | GSI with INCLUDE projection, no strong consistency on GSIs |
| `ddb_5` | Optimistic locking with a version attribute |
| `ddb_6` | Atomic counters and TTL in epoch seconds |
| `ddb_7` | BatchWriteItem in chunks of 25, retrying UnprocessedItems |
| `ddb_8` | Transactions and CancellationReasons |
| `ddb_9` | Processing a stream with NEW_AND_OLD_IMAGES |

## Summary

- 400 KB items. Partition key (+ sort key). High-cardinality keys avoid hot partitions.
- RCU: 4 KB strong / 2 × 4 KB eventual / transactional ×2. WCU: 1 KB, transactional ×2. Round sizes up.
- Query one partition, never Scan in hot paths. Filters do not save RCU. Paginate with LastEvaluatedKey.
- Conditions for idempotency and optimistic locking. ADD for counters. Transactions for all-or-nothing (100 actions, 2× cost).
- LSI = same PK, created with the table, strong reads possible. GSI = any key, any time, eventual only, own capacity.
- TTL in epoch seconds, free deletion. Streams: 24 h, 4 view types. DAX = microsecond cache with no code change.

## Check yourself

1. You need 20 strongly consistent reads/s of 9 KB items. How many RCUs?
2. A table has `order_id` as partition key. The app must list a customer's orders by date. What do you add?
3. Why does a Scan with a FilterExpression that returns 10 items still consume a lot of capacity?
4. Two users update the same document at the same time and one update is lost. Which DynamoDB feature prevents it?
5. A BatchWriteItem call returns HTTP 200 but some items are missing. Why?

<details><summary>Answers</summary>

1. ceil(9/4) = 3 units × 20 = **60 RCU**.
2. A **GSI** with partition key `customer_id` and sort key `order_date`.
3. Capacity is consumed for every item read by the Scan before the filter is applied.
4. **Optimistic locking**: a version attribute with a condition expression on update.
5. Throttled items come back in `UnprocessedItems`. The code must retry them with exponential backoff.

</details>

## Further reading

- [DynamoDB developer guide](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Introduction.html) and [FAQ](https://aws.amazon.com/dynamodb/faqs/)
- [Read/write capacity mode](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadWriteCapacityMode.html)
- [Best practices for designing partition keys](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-partition-key-design.html)
- [Using expressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.html) and [reserved words](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/ReservedWords.html)
- [DAX](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DAX.html)
