#!/usr/bin/python
#coding=utf-8
import os,sys
import yaml
import commands
from redis.sentinel import Sentinel
import time
import logging
import SendMsg

BaseConfigFile = '/usr/local/tmac_twemproxy_monitor/conf/tmac_twem.yml'

class TmacTwem(object):
        def __init__(self):
                self.config_file = BaseConfigFile
                self.send_msg = SendMsg.SendMsg()

        #加载TmacTwem的配置文件,返回一个字典
        def load_tmactwem_config(self):
                if os.path.isfile(self.config_file):
                        config_fd = open(self.config_file,'r')
                        tmactwem_config = yaml.load(config_fd)
                        config_fd.close()
                        return tmactwem_config
                else:
                        print '%s is not exists,now exit....' % self.config_file
                        exit(1)

        def Logger(self,log_level,log_msg):
                config = self.load_tmactwem_config()
                log_file = config['global']['log_file']
                logging.basicConfig(level=logging.DEBUG,
                                format='%(asctime)s [%(levelname)s] %(message)s',
                                datefmt='%Y-%m-%d %X',
                                filename=log_file,
                                filemode='a')
                if log_level == 'd':
                        logging.debug(log_msg)
                elif log_level == 'i':
                        logging.info(log_msg)
                elif log_level == 'w':
                        logging.warning(log_msg)
                elif log_level == 'e':
                        logging.error(log_msg)
                elif log_level == 'c':
                        logging.critical(log_msg)

        #返回相应模块的twemproxy的配置文件,以字典的形式,tw_sn必须唯一
        def load_twem_config(self,tw_sn):
                config = self.load_tmactwem_config()
                twem_config_file = config['tw_module'][tw_sn]['twem_config']
                if os.path.isfile(twem_config_file):
                        twem_config_fd = open(twem_config_file,'r')
                        twem_config = yaml.load(twem_config_fd)
                        return twem_config
                else:
                        log_msg = 'twemproxy file %s is not exists,now exit....' % twem_config_file
                        self.Logger('e',log_msg)
                        exit(1)

        def get_twem_file(self,tw_sn):
                config = self.load_tmactwem_config()
                twem_config_file = config['tw_module'][tw_sn]['twem_config']
                if os.path.isfile(twem_config_file):
                        return twem_config_file
                else:
                        log_msg = 'twemproxy file %s is not exists,now exit....' % twem_config_file
                        self.Logger('e',log_msg)
                        exit(1)

        def get_sentinels(self,tw_sn):
                config = self.load_tmactwem_config()
                all_sentinel = config['tw_module'][tw_sn]['sentinels']
                return all_sentinel

        def connect_sentinel(self,host,port):
                _failed_times = 0
                while True:
                        try:
                                sentinel = Sentinel([(host,port)],socket_timeout=1)
                                return sentinel
                        except:
                                _failed_times += 1
                                if _failed_times > 3:
                                        log_msg = "Cannot connect to sentinel %s:%s" % (host,port)
                                        self.Logger('e',log_msg)
                                        self.send_msg.send_sms_mail(log_msg)
                                        raise
                                continue
                        break

        #以数组的形式返回:['192.168.117.111:6379','192.168.117.222:6379']
        def get_twemconfig_master(self,tw_sn):
                twem_config = self.load_twem_config(tw_sn)
                try:
                        twem_masters = twem_config[tw_sn]['servers']
                except:
                        log_msg = 'Cannot find %s in twemproxy config file' % tw_sn
                        self.Logger('e',log_msg)
                        return False
                tmp_masters = []
                for i in twem_masters:
                        tmp_host = i.split(':')[0]
                        tmp_port = i.split(':')[1]
                        tmp_master = tmp_host + ':' + tmp_port
                        tmp_masters.append(tmp_master)
                return tmp_masters

        #sentinel配置里面也必须用my_master,不能修改
        def get_sentinel_master(self,host,port):
                sentinel = self.connect_sentinel(host,port)
                try:
                        master_tunlp = sentinel.discover_master('mymaster')
                        sentinel_master = master_tunlp[0] + ':' + str(master_tunlp[1])
                        return sentinel_master
                except:
                        log_msg = 'sentinel %s:%s cannot find masters' % (host,port)
                        self.Logger('e',log_msg)
                        self.send_msg.send_sms_mail(log_msg)
                        return False


        #以数组形式返回:['192.168.117.111:6379','192.168.117.222:6379']
        def get_allsentinel_masters(self,tw_sn):
                all_sentinels = self.get_sentinels(tw_sn)
                sentinel_masters = []
                for sentinel_str in all_sentinels:
                        #host,port = sentinel_str.split(':')
                        host = sentinel_str.split(':')[0]
                        port = int(sentinel_str.split(':')[1])
                        sentinel_master = self.get_sentinel_master(host,port)
                        if sentinel_master is False:
                                return False
                        else:
                                sentinel_masters.append(sentinel_master)
                return sentinel_masters

        #判断两个数组的包含关系
        def Contain(self,a,b):
                for i in a:
                        if i in b:
                                continue
                        else:
                                return False
                return True
        #比较两个数组
        def Compare(self,a,b):
                if len(a) != len(b):
                        return False
                else:
                        if self.Contain(a,b) and self.Contain(b,a):
                                return True
                        else:
                                return False

        #判断master是否改变,变了返回False,没变返回True,如果没有获取到sentinel_master,就不修改twemproxy配置文件
        def is_master_change(self,tw_sn):
                sentinel_masters = self.get_allsentinel_masters(tw_sn)
                twem_masters = self.get_twemconfig_master(tw_sn)
                if sentinel_masters is False:
                        return  True
                if twem_masters is False:
                        return  True

                if self.Compare(sentinel_masters,twem_masters):
                        return True
                else:
                        log_msg = '%s twemprioxy masters from %s change to %s' % (tw_sn,twem_masters,sentinel_masters)
                        self.Logger('w',log_msg)
                        self.send_msg.send_sms_mail(log_msg)
                        return False

        def restart_twem(self,tw_sn):
                config = self.load_tmactwem_config()
                restart_cmd = config['tw_module'][tw_sn]['twem_cmd']
                status,output = commands.getstatusoutput(restart_cmd)
                if status == 1:
                        log_msg = 'restart %s twemproxy failed...error msg:%s' % (tw_sn,output)
                        self.Logger('e',log_msg)
                        self.send_msg.send_sms_mail(log_msg)
                        return False
                else:
                        log_msg = 'restart %s twemproxy successed..' % tw_sn
                        self.Logger('w',log_msg)
                        self.send_msg.send_sms_mail(log_msg)
                        return True

        def update_twem_config(self,tw_sn):
                twem_file = self.get_twem_file(tw_sn)
                new_servers = []
                sentinel_masters = self.get_allsentinel_masters(tw_sn)
                if sentinel_masters is False:
                        return 
                for i in sentinel_masters:
                        new_server = i + ':' + '1'
                        new_servers.append(new_server)
                twem_config = self.load_twem_config(tw_sn)
                twem_config[tw_sn]['servers'] = new_servers
                fd_w = open(twem_file,'w')
                yaml.dump(twem_config,fd_w,allow_unicode=True,default_flow_style=False)
                log_msg = '%s masters has changed...' % tw_sn
                self.Logger('w',log_msg)

        def start_mon_twem(self,tw_sn):
                master_status = self.is_master_change(tw_sn)
                if master_status is False:
                        self.update_twem_config(tw_sn)
                        self.restart_twem(tw_sn)

if __name__ == '__main__':
        while True:
                tmac_tw = TmacTwem()
                config = tmac_tw.load_tmactwem_config()
                all_tw_sn = config['tw_module'].keys()
                loop_time = int(config['global']['delay_loop'])
                for tw_sn in all_tw_sn:
                        tmac_tw.start_mon_twem(tw_sn)

                time.sleep(loop_time)
