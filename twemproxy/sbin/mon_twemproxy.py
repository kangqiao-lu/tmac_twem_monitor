#!/usr/bin/python
#coding=utf-8
import urllib2
import json
import socket
twem_url = 'http://192.168.129.209:22222'
failed_times = 1
while True:
        try:
                res = urllib2.urlopen(twem_url)
                content = res.read()
        except socket.error:
                failed_times += 1
                if failed_times > 5:
                        exit(88)
                continue
        break
all_dic = json.loads(content)
all_twem_ser = all_dic.keys()[5:]
for twem_ser in all_twem_ser:
        twem_dic = all_dic[twem_ser]
        twem_arr = twem_dic.keys()
        twem_arr.sort()
        twem_arr.reverse()
        print "This is: %s" % twem_ser
        for i in twem_arr[0:6]:
                print '%s:%s' % (i,twem_dic[i])
        print
        print "Here are all redis servers:"
        print
        for redis_ser in twem_arr[6:]:
                redis_ser_dic =  twem_dic[redis_ser]
                print redis_ser
                for i in redis_ser_dic.keys():
                        print '%s:%s' % (i,redis_ser_dic[i])
                print '\033[1;31m##########################################\033[0m'
