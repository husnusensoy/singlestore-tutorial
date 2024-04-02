import singlestoredb as s2
import numpy as np
from threading import Thread
import time
from tqdm import trange

HOST = "172.12.2.68"
PORT = 3306
USER = "root"
PASSWORD = "server"
DATABASE = "deeplearning"

SQL = """
SELECT id, v  <*> '[{vector}]'
                     as distance
                 FROM vecs
                 ORDER BY distance use index (ivfpq_nlist) desc
                            limit 10;
"""

NTHREAD = 32
NREPEAT = 100
def query(index:int, n:int = 100):
    with s2.connect(
        host=HOST, port=PORT, user=USER, password=PASSWORD, database=DATABASE
    ) as conn:
        with conn.cursor() as cur:
            if index == 0:
                for _ in trange(n):
                    x = np.random.rand(512)
                    sql = SQL.format(vector=",".join(map(str,x.tolist())))
                    cur.execute(sql)
            else:
                for _ in range(n):
                    x = np.random.rand(512)
                    sql = SQL.format(vector=",".join(map(str,x.tolist())))
                    cur.execute(sql)
                


threads = [Thread(target=query,args=(i, NREPEAT,)) for i in range(NTHREAD) ]

t0 = time.time()
for t in threads:
    t.start()

for t in threads:
    t.join()
t1 = time.time()

print(f"Total {NTHREAD * NREPEAT} queries ({NTHREAD}-way) run in {t1-t0:.4f} sec ({ (NTHREAD * NREPEAT )/(t1-t0):.2f} qps) ")