# Singlestore Vector Test

Some scenarios on vector data with singlestore

## Test Environment

* 2 aggregate nodes (4 vcore 32 GB)
* 4 leaf nodes (4 vcore 32 GB)

on VM ware (`Intel(R) Xeon(R) Gold 6226R CPU @ 2.90GHz`)


## File Inventory
* `500m.sql`: Generate 33 million random 512 dim normalized vectors and store in singlestore
* `README.md`: me
* `vectory_query.sql`: Single 512 dim query
* `vectory_query_load.py`: Multi threaded query vector data


## Test scenario

* 33 million rows loaded using `500m.sql`  script
* Query using `vector_query_load.py` 

Index create and query performance for different index types

### IVF_PQ

```sql
alter table vecs add vector index ivfpq_nlist (v) INDEX_OPTIONS='{"index_type":"IVF_PQ", "nlist": 790}';
-- Query OK, 0 rows affected (10 min 33.50 sec)
```

Total 3200 queries (32-way) run in 23.3362 sec (137.13 qps)

### IVF_PQFS

```sql
alter table vecs add vector index ivfpq_nlist (v) INDEX_OPTIONS='{"index_type":"IVF_PQFS", "nlist": 790}';
-- Query OK, 0 rows affected (3 min 47.26 sec)
```

Total 3200 queries (32-way) run in 20.6958 sec (154.62 qps)

### IVF_FLAT

```sql
alter table vecs add vector index ivfpq_nlist (v) INDEX_OPTIONS='{"index_type":"IVF_FLAT", "nlist": 2018, "nprobe": 128}';
-- Query OK, 0 rows affected (9 min 43.27 sec)
```

Total 3200 queries (32-way) run in 201.5580 sec (15.88 qps)

Not that wierd. 512 dim vector without quantization with more probing slows down index performance.

### HNSW_FLAT

```sql
alter table vecs add vector index ivfpq_nlist (v) INDEX_OPTIONS='{"index_type":"HNSW_FLAT"}';
--
```


### HNSW_PQ

```sql
alter table vecs add vector index ivfpq_nlist (v) INDEX_OPTIONS='{"index_type":"HNSW_PQ"}';
--
```

## TODO

* Different ANN index accuracies should be tested wrt exact (FLAT) NN indicies.