import rrdtool
import random
import time
import os

def create_rrdtool(name, start, step) :
    return rrdtool.create(name, "--start", start, "--step", str(step),
    "DS:courant:GAUGE:"+str(1+int(step*3/4))+":0:30",
    "DS:tension:GAUGE:"+str(1+int(step*3/4))+":0:300",
    "DS:dephasage:GAUGE:"+str(1+int(step*3/4))+":0:360",
    "DS:puiss_active:GAUGE:"+str(1+int(step*3/4))+":0:10000",
    "DS:puiss_reactive:GAUGE:"+str(1+int(step*3/4))+":0:10000",
    "DS:puiss_apparente:GAUGE:"+str(1+int(step*3/4))+":0:10000",
    "RRA:AVERAGE:0.5:"+str(step)+":"+str(int(10*24*60*60/step)),
    "RRA:AVERAGE:0.5:"+str(step*60)+":"+str(int(90*24*60/step)),
    "RRA:AVERAGE:0.5:"+str(step*60*60)+":"+str(int(18*31*24/step)),
    "RRA:AVERAGE:0.5:"+str(step*60*60*24)+":"+str(int(10*366/step)),
    "RRA:HWPREDICT:"+str(int(10*24*60*60/step))+":0.1:0.0035:"+str(int(60*60*24/step))
    )

#create_rrdtool("test.rrd", "N", 1)

while (True) :
  r1=str(random.randint(0,30))
  r2=str(random.randint(0,300))
  r3=str(random.randint(0,360))
  r4=str(random.randint(0,3000))
  r5=str(random.randint(0,3000))
  r6=str(random.randint(0,3000))
  rrdtool.update("test.rrd", str(int(time.time()))+":"+r1+":"+r2+":"+r3+":"+r4+":"+r5+":"+r6)
  #os.system("rrdtool update test.rrd "+str(int(time.time()))+":"+r1+":"+r2+":"+r3+":"+r4+":"+r5+":"+r6)
  print(str(int(time.time()))+":"+r1+":"+r2+":"+r3+":"+r4+":"+r5+":"+r6)
  time.sleep(1)

