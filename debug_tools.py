#!/usr/bin/env python
import time
import multiprocessing
import Queue #needed separately for the Empty exception

class Custom_Timer(object):
    def __init__(self,name):
        self.name = name
        self.begin()
        self.update_t()

    def update_t(self):
        self.t = time.clock() - self.t0
        return self.t

    def begin(self):
        self.t0 = time.clock()

    def t_elapsed(self):
        return self.t-self.t0
    
    def __str__(self):
        return str(self.name)
    
class timer_dt(Custom_Timer):
    def __init__(self, name,target_dt=1.0):
        super(timer_dt,self).__init__(name)
        self.t_prev = time.clock() - self.t0
        self.n = 0
        self.target_dt = target_dt
        
    @property
    def dt(self):
        self.update_t()
        dt = self.t - self.t_prev
        self.t_prev = self.t
        return dt
    
    def check(self):
        self.update_t()
        dt = self.t - self.t_prev
        if dt > self.target_dt:
            self.t_prev = self.t
            self.n += 1
            return True
        else:
            return False

class timer_loop(Custom_Timer):
    def __init__(self, *args):
        super(timer_loop,self).__init__(*args)
        self.n = 0
        self.total_time = 0
        
    def end(self):
        self.n += 1
        self.update_t()
        self.total_time += self.t
        
    @property
    def avg_loop_time(self):
        if self.n > 0:
            return self.total_time/self.n
        else:
            return -1

    def __str__(self):
        return '%s: N: %d, total: %.3e, avg: %.3e' %(self.name,self.n,\
                            self.total_time, self.avg_loop_time)

def q_send(q,x,n=1,delay=None):
    for i in range(n):
        try:
            q.put(x)
        except Queue.Full:
            print 'Queue Full',x
            pass
        if delay:
            time.sleep(delay)
            
def q_get(q,n=1,delay=None,name=''):
    for i in range(n):
        try:
            dat = q.get(False)
            return dat
        except Queue.Empty:
            #print 'Queue Empty',name
            pass
        if delay:
            time.sleep(delay)