set sql_mode = pipes_as_concat;

delimiter //
create or replace function randbetween(a float, b float) returns float
as 
begin
  return (rand()*(b - a) + a);
end //

create or replace function gen_vector(length int) returns text as
declare s text = "[";
begin
  if length < 2 then 
    raise user_exception("length too short: " || length);
  end if;

  for i in 1..length-1 loop
    s = s || randbetween(-1,1) || "," ;
  end loop;
  s = s || randbetween(-1,1) || "]";
  return s;
end //

create or replace function normalize(v blob) returns blob as
declare
  squares blob = vector_mul(v,v);
  length float = sqrt(vector_elements_sum(squares));
begin
  return scalar_vector_mul(1/length, v);
end //

create or replace function norm512(v vector(512)) returns vector(512) as
begin
  return normalize(v);
end //

create or replace function nrandv512() returns vector(512) as
begin
  return norm512(gen_vector(512));
end  //
delimiter ;

/* GENERATING RANDOM VECTORS
This loop generates 160,000,000 random vectors of dimensionality 1536 directly in the below table. */

create table vecs(
id bigint(20),
url text default null,
paragraph text default null, 
v vector(512, f32) not null, 
shard key(id), 
key(id) using hash, 
fulltext (paragraph)
);

insert into vecs (id, v) values (1, nrandv512());
delimiter //
do 
declare num_rows bigint = 33000000;
declare c int;
begin
  select count(*) into c from vecs;
  while c < num_rows loop
    insert into vecs(id, v)
    select id + (select max(id) from vecs), nrandv512()
    from vecs
    where id <= 1024*1024; /* chunk size 128K so we can see progress */
    select count(*) into c from vecs;
  end loop;
end //
delimiter ;

alter table vecs add vector index ivfpq_nlist (v) INDEX_OPTIONS='{"index_type":"IVF_PQ", "nlist": 790}';

OPTIMIZE TABLE vecs FULL;

insert into vecs
select id, url, paragraph, embedding from wiki_scrape;




alter table vecs add vector index ivfpq_nlist (v) INDEX_OPTIONS='{"index_type":"IVF_PQ", "nlist": 790}';





