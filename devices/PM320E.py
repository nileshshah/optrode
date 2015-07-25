import logging, os, time,sys
import visa
import numpy as np
import time
import matplotlib.pyplot as plt
logger = logging.getLogger(__name__)

class PM320E():
    model='PM320E'
    name = 'PM320E'
    wl=[0, 0]
    sensor_sn=[None, None]
    sensor_pres=[False, False]
    def __init__(self):
        logger.info('Opening VISA session with %s'%self.model)
        rm = visa.ResourceManager('C:\\Windows\\system32\\visa64.dll')
        self.session = rm.open_resource('USB0::0x1313::0x8022::M00237764::INSTR')
        # self.session = visa.instrument('USB0::0x1313::0x8022::M00237764::INSTR')
        # self.session.query_ascii_values(':sens1:sernr?')
        self.session.write(':syst:linefilter 60Hz')
        self.session.write(':syst:bright 100')
        self.sensor_present()
        self.set_ave(ch=1, n_ave=1)
        self.set_ave(ch=2, n_ave=1)
        #self.set_autorange(ch=1)
        #self.set_autorange(ch=2)
        self.get_wl(ch=1)
        self.get_wl(ch=2)
        #self.session.write('init:conf:pow')
        #self.session.write('init:meas:pow')
        #self.autorange_on()
        #self.session.write('inp:pdi:filt:lpas 1')
        logger.info('%s initialized'%self.model)
    def get_sensor_sn(self, ch):
        self.sensor_sn[ch-1]=self.session.query_ascii_values(':sens%d:sernr?'%ch)
        return self.sensor_sn[ch-1]
    def sensor_present(self):
        #self.sensor_pres[0]=bool(len(self.get_sensor_sn(ch=1)))
        #self.sensor_pres[1]=bool(len(self.get_sensor_sn(ch=2)))
        self.sensor_pres[0]=True
        self.sensor_pres[1]=False
    def close(self):
        self.session.close()
        logger.info('Connection closed')
    def set_ave(self, ch, n_ave=1):
        self.session.write(':aver%d %d' %(ch, n_ave))
        logger.info('CH%s averaging set to %d'%( ch, self.get_ave(ch=ch)))
    def get_ave(self, ch):
        #self.n_ave=self.session.ask_for_values(':aver%d?'%ch)[0]
        self.n_ave=self.session.query_ascii_values(':aver%d?'%ch)[0]
        return self.n_ave
    def get_power(self, ch,n_pts=1, is_ave=False, wl=None):
        if wl!=None:
            self.set_wl(ch=ch, wl=wl)
        vals = []
        #vals = np.zeros(n_pts)
        for i in range(10*n_pts):
            if self.sensor_pres[ch-1]:
                #Sometime meter has timeout and returns empty. This ensures n_pts qcquired
                try:
                    vals.append(self.session.query_ascii_values(':pow%d:val?'%ch)[0])
                except:
                    continue
                    #problem acqiuiring data point from PM320E'. Try again
            else:
                sys.exit('No power meter sensor present on ch-%d' % ch)
            if len(vals) == n_pts:
                break
        vals = np.array(vals)
        if is_ave:
            return np.average(vals, axis=0)
        else:
            if len(vals)<n_pts:
                logger.error('Did not fill vals array in maximum time')
                return null
            return vals
    def set_wl(self, ch, wl):
        wl=np.round(wl,0)
        if not(abs(self.get_wl(ch=ch)-wl)>=0.5):
            return
        self.session.write(':wavel%d:val %d' %(ch, wl))
        logger.info('CH%s wavelength  set to %d'%( ch, self.get_wl(ch=ch)))
    def get_wl(self,ch):
        if self.sensor_pres[ch-1]:
            self.wl[ch-1]=self.session.query_ascii_values(':wavel%d:val?' %(ch))[0]
        else:
            logger.info('CH%d sensor not present.'%ch)
            self.wl[ch-1]=0
        return self.wl[ch-1]
    def set_autorange(self, ch):
        self.session.write(':prange%d auto' %(ch))
    def set_range(self,ch,rng):
        self.session.write(':prange%d %s' %(ch,rng))
        #self.session.write(':irange%d %s' %(ch,'R1MA'))
    def get_range(self, ch):
        return self.session.query_ascii_values(':prange%d?' %(ch))
        
    #def setzero(self):
    #    self.session.write('sens:corr:coll:zero:init')
    #    logger.info('Meter Zeroed')
    #def getzero(self):
    #    return self.session.ask_for_values('sens:corr:coll:zero:magn?')[0]
   

if __name__ == '__main__':
    #logging.basicConfig(level=logging.DEBUG)
   
    pm = PM320E()
    pm.set_wl(1,850)
    print pm.session.query_ascii_values(':AVER1?')
    #print pm.session.query_ascii_values(':PBANDW?')
    #for i in range(1000):
    #    print pm.get_power(1,is_ave=True)
    pm.close()
    #pm.power()


