这个python(2.7)监控程序是用来保证twemproxy高可用的，他会从Sentinel那里获取到最新的主redis的ip和端口，然后跟twmproxy配置文件作对比，如果发现不一致，就自动更新twemproxy配置文件，并重启twemproxy，当然会报警给dba。
![redis架构图](./tmac_monitor_twem.png)
