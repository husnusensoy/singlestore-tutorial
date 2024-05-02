import singlestoredb as s2
import numpy as np
from threading import Thread, Lock
import time
from tqdm import trange
from enum import Enum

AGGREGATOR_NODES = ["172.12.2.68","172.12.2.69"]
PORT = 3306
USER = "root"
PASSWORD = "server"
DATABASE = "deeplearning"

SQL = """
SELECT id, v  <*> '[{vector}]'
                     as distance
                 FROM vecs
                 ORDER BY distance use index (ivfpq_nlist) desc
                            limit 100;
"""

class LoadBalanceStrategy(Enum):
    RoundRobin = 0
    Random =1 

class LoadBalance():
    def __init__(self, hosts:list[str],strategy: LoadBalanceStrategy.RoundRobin) -> None:
        self.hosts = hosts
        self.nextidx = -1

    def next(self) -> str:
        self.nextidx = (self.nextidx + 1 )%len(self.hosts)

        return self.hosts[self.nextidx]


g_rt=[]
lck = Lock()
NTHREAD = 32
NREPEAT = 100
def query(index:int, host:str, n:int = 100):
    l_rt = []

    global g_rt 
    with s2.connect(
        host=host, port=PORT, user=USER, password=PASSWORD, database=DATABASE
    ) as conn:
        with conn.cursor() as cur:
            if index == 0:
                for _ in trange(n):
                    x = np.random.rand(512)
                    sql = SQL.format(vector=",".join(map(str,x.tolist())))
                    t0 = time.time()
                    cur.execute(sql)
                    t1 = time.time()
                    l_rt.append(t1-t0)
            else:
                for _ in range(n):
                    x = np.random.rand(512)
                    sql = SQL.format(vector=",".join(map(str,x.tolist())))
                    t0 = time.time()
                    cur.execute(sql)
                    t1 = time.time()
                    l_rt.append(t1-t0)

    with lck:
        g_rt += l_rt

                

lb = LoadBalance(AGGREGATOR_NODES, strategy=LoadBalanceStrategy.RoundRobin)
threads = [Thread(target=query,args=(i, lb.next(),NREPEAT,)) for i in range(NTHREAD)]

t0 = time.time()
for t in threads:
    t.start()

for t in threads:
    t.join()
t1 = time.time()

print()
print(f"Total {NTHREAD * NREPEAT} queries ({NTHREAD}-way) run in {t1-t0:.4f} sec ({ (NTHREAD * NREPEAT )/(t1-t0):.2f} qps) ")

msec = np.array(g_rt)*1000
p50,p95,p99 = np.percentile(msec, [50,95,99])

print()
print(f"Latency: {msec.mean():.2f} ms ± {msec.std():.2f} [{msec.min():.2f} - {msec.max():.2f}] p50={p50:.2f} p95={p95:.2f} p99={p99:.2f}")