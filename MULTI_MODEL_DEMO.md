## Prepare Demo
* Create an openai API_KEY
* Set OpenAI API_KEY, SingleStore USERNAME/PASSWORD and CONN_STR in `.env` file
* Create `deeplearning` database.
* Run `python scrape.py` to load `wiki_scrape` table with some wikipedia data with vector embeddings. Remember that this table contains both text and embedding data.
* See row count in `wiki_scrape` table.

```sql
select count(1) from wiki_scrape;

-- +----------+
-- | count(1) |
-- +----------+
-- |    44319 |
-- +----------+
-- 1 row in set (0.00 sec)
```

* See a sample row in `wiki_scrape` table

```sql
SET @@sql_mode = PIPES_AS_CONCAT;
select id,url, substr(paragraph,1,20)||'...' paragraph from wiki_scrape limit 3;

-- +-------+-----------------------------------------------------------------+-------------------------+
-- | id    | url                                                             | paragraph               |
-- +-------+-----------------------------------------------------------------+-------------------------+
-- | 30135 | https://en.wikipedia.org/wiki/Titanfall_2                       | The game used a heav... |
-- | 30169 | https://en.wikipedia.org/wiki/Tokyo_Mirage_Sessions_%E2%99%AFFE | The scenario was wri... |
-- | 30398 | https://en.wikipedia.org/wiki/Undertale                         | Monsters will talk t... |
-- +-------+-----------------------------------------------------------------+-------------------------+
-- 3 rows in set (0.02 sec)

```

### Hybrid Search - Re-ranking and Blending Searches

* Query by vector ANN vector index (check explain plan)

```sql
SET @v_mario_kart = (SELECT embedding FROM wiki_scrape 
          WHERE URL = "https://en.wikipedia.org/wiki/Super_Mario_Kart" 
          ORDER BY id LIMIT 1);

SELECT id
        , substr(paragraph,1,50)||'...' paragraph
        , embedding <*> @v_mario_kart AS SCORE
FROM wiki_scrape
ORDER BY score DESC 
LIMIT 5;

-- +------+-------------------------------------------------------+--------------------+
-- | id   | paragraph                                             | SCORE              |
-- +------+-------------------------------------------------------+--------------------+
-- | 5473 | Super Mario Kart[a] is a kart racing game develope... | 0.9999998807907104 |
-- | 5489 | Super Mario Kart received critical acclaim and pro... |  0.832332193851471 |
-- | 5500 | Several sequels to Super Mario Kart have been rele... | 0.8000606298446655 |
-- | 5475 | Super Mario Kart received positive reviews and was... | 0.7844879627227783 |
-- | 5491 | Super Mario Kart has been listed among the best ga... | 0.7702401876449585 |
-- +------+-------------------------------------------------------+--------------------+
```

* Query same table using FULL TEXT index filter

```sql
SELECT id, substr(paragraph,1,50)||'...' paragraph,
    MATCH(paragraph) AGAINST("mario kart") AS SCORE
  FROM wiki_scrape
  WHERE MATCH(paragraph) AGAINST("mario kart")
  ORDER BY SCORE desc 
  LIMIT 5;

-- +-------+-------------------------------------------------------+-------+
-- | id    | paragraph                                             | SCORE |
-- +-------+-------------------------------------------------------+-------+
-- | 32877 | A Samus amiibo figure can be used to unlock a Mii ... |     1 |
-- | 36500 | In Wario's Woods (1994), Wario is the main antagon... |     1 |
-- | 36481 | Waluigi is a playable driver in the Mario Kart ser... |     1 |
-- |  5497 | Nintendo re-released Super Mario Kart in 2017 as p... |     1 |
-- |  5500 | Several sequels to Super Mario Kart have been rele... |     1 |
-- +-------+-------------------------------------------------------+-------+  
```

* Filter using full text index and best match with vector


```sql
SELECT id, substr(paragraph,1,50)||'...' paragraph,
    MATCH(paragraph) AGAINST("mario kart") AS SCORE2
    , embedding <*> @v_mario_kart AS SCORE
  FROM wiki_scrape
  WHERE MATCH(paragraph) AGAINST("mario kart")
  ORDER BY SCORE desc 
  LIMIT 5;

-- +------+-------------------------------------------------------+--------------------+--------------------+
-- | id   | paragraph                                             | SCORE2             | SCORE              |
-- +------+-------------------------------------------------------+--------------------+--------------------+
-- | 5473 | Super Mario Kart[a] is a kart racing game develope... | 0.9420013427734375 | 0.9999998807907104 |
-- | 5489 | Super Mario Kart received critical acclaim and pro... | 0.5303301215171814 |  0.832332193851471 |
-- | 5500 | Several sequels to Super Mario Kart have been rele... |                  1 | 0.8000606298446655 |
-- | 5475 | Super Mario Kart received positive reviews and was... |  0.815587043762207 | 0.7844879627227783 |
-- | 5491 | Super Mario Kart has been listed among the best ga... | 0.7753469347953796 | 0.7702401876449585 |
-- +------+-------------------------------------------------------+--------------------+--------------------+
-- 5 rows in set (0.00 sec)
```


* More details can be found in [Hybrid Search - Re-ranking and Blending Searches](https://docs.singlestore.com/db/v8.5/developer-resources/functional-extensions/hybrid-search-re-ranking-and-blending-searches/)