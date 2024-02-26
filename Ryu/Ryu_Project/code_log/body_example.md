<!--
 * @Author: louis
 * @Date: 2023-04-26 15:58:47
 * @Connection: louis.yyj.dev@foxmail.com
 * @FilePath: /My_Ryu_Project/code_log/body_example.md
 * @Description: xxx
-->
port返回统计信息:
[OFPPortStats(port_no=5,rx_packets=0,tx_packets=43452,rx_bytes=0,tx_bytes=3293787,rx_dropped=0,tx_dropped=0,rx_errors=0,tx_errors=0,rx_frame_err=0,rx_over_err=0,rx_crc_err=0,collisions=0,duration_sec=82955,duration_nsec=784000000), 

OFPPortStats(port_no=4,rx_packets=0,tx_packets=0,rx_bytes=0,tx_bytes=0,rx_dropped=0,tx_dropped=0,rx_errors=0,tx_errors=0,rx_frame_err=0,rx_over_err=0,rx_crc_err=0,collisions=0,duration_sec=82955,duration_nsec=795000000), 

OFPPortStats(port_no=2,rx_packets=63670,tx_packets=61011,rx_bytes=3019129,tx_bytes=4268822,rx_dropped=0,tx_dropped=0,rx_errors=0,tx_errors=0,rx_frame_err=0,rx_over_err=0,rx_crc_err=0,collisions=0,duration_sec=82955,duration_nsec=790000000),

OFPPortStats(port_no=4294967294,rx_packets=105889,tx_packets=20337,rx_bytes=4971768,tx_bytes=1195254,rx_dropped=0,tx_dropped=0,rx_errors=0,tx_errors=0,rx_frame_err=0,rx_over_err=0,rx_crc_err=0,collisions=0,duration_sec=82955,duration_nsec=757000000),

OFPPortStats(port_no=6,rx_packets=0,tx_packets=43452,rx_bytes=0,tx_bytes=3293787,rx_dropped=0,tx_dropped=0,rx_errors=0,tx_errors=0,rx_frame_err=0,rx_over_err=0,rx_crc_err=0,collisions=0,duration_sec=82955,duration_nsec=772000000), 

OFPPortStats(port_no=3,rx_packets=78804,tx_packets=58929,rx_bytes=4121744,tx_bytes=3461725,rx_dropped=0,tx_dropped=0,rx_errors=0,tx_errors=0,rx_frame_err=0,rx_over_err=0,rx_crc_err=0,collisions=0,duration_sec=82955,duration_nsec=778000000)]


flow返回统计信息：
[OFPFlowStats(byte_count=35760,cookie=0,duration_nsec=505000000,duration_sec=376,flags=0,hard_timeout=0,idle_timeout=0,importance=0,instructions=[OFPInstructionActions(actions=[OFPActionOutput(len=16,max_len=65535,port=4294967293,type=0)],len=24,type=4)],length=96,match=OFPMatch(oxm_fields={'eth_dst': '01:80:c2:00:00:0e', 'eth_type': 35020}),packet_count=596,priority=65535,table_id=0), 

OFPFlowStats(byte_count=294,cookie=0,duration_nsec=147000000,duration_sec=4,flags=0,hard_timeout=30,idle_timeout=0,importance=0,instructions=[OFPInstructionActions(actions=[OFPActionOutput(len=16,max_len=65509,port=3,type=0)],len=24,type=4)],length=112,match=OFPMatch(oxm_fields={'in_port': 2, 'eth_type': 2048, 'ipv4_src': '169.254.38.77', 'ipv4_dst': '169.254.81.179'}),packet_count=3,priority=1,table_id=0), 

OFPFlowStats(byte_count=294,cookie=0,duration_nsec=146000000,duration_sec=4,flags=0,hard_timeout=30,idle_timeout=0,importance=0,instructions=[OFPInstructionActions(actions=[OFPActionOutput(len=16,max_len=65509,port=2,type=0)],len=24,type=4)],length=112,match=OFPMatch(oxm_fields={'in_port': 3, 'eth_type': 2048, 'ipv4_src': '169.254.81.179', 'ipv4_dst': '169.254.38.77'}),packet_count=3,priority=1,table_id=0), 

OFPFlowStats(byte_count=78000,cookie=0,duration_nsec=509000000,duration_sec=376,flags=0,hard_timeout=0,idle_timeout=0,importance=0,instructions=[OFPInstructionActions(actions=[OFPActionOutput(len=16,max_len=65535,port=4294967293,type=0)],len=24,type=4)],length=80,match=OFPMatch(oxm_fields={}),packet_count=1300,priority=0,table_id=0)]





port_desc返回统计信息：
body------------ [
    OFPPort(config=0,hw_addr='d4:da:21:ac:71:61',length=72,name=b'phy0-ap0',port_no=5,properties=[OFPPortDescPropEthernet(advertised=0,curr=0,curr_speed=0,length=32,max_speed=0,peer=0,supported=0,type=0)],state=4), 

    OFPPort(config=0,hw_addr='d4:da:21:ac:71:60',length=72,name=b'lan4',port_no=4,properties=[OFPPortDescPropEthernet(advertised=59439,curr=10240,curr_speed=0,length=32,max_speed=1000000,peer=0,supported=59439,type=0)],state=1), 

    OFPPort(config=0,hw_addr='d4:da:21:ac:71:60',length=72,name=b'lan2',port_no=2,properties=[OFPPortDescPropEthernet(advertised=59439,curr=10272,curr_speed=1000000,length=32,max_speed=1000000,peer=0,supported=59439,type=0)],state=4), 

    OFPPort(config=0,hw_addr='d4:da:21:ac:71:60',length=72,name=b'br0',port_no=4294967294,properties=[OFPPortDescPropEthernet(advertised=0,curr=0,curr_speed=0,length=32,max_speed=0,peer=0,supported=0,type=0)],state=4), 

    OFPPort(config=0,hw_addr='d4:da:21:ac:71:62',length=72,name=b'phy1-ap0',port_no=6,properties=[OFPPortDescPropEthernet(advertised=0,curr=0,curr_speed=0,length=32,max_speed=0,peer=0,supported=0,type=0)],state=4), 
    
    OFPPort(config=0,hw_addr='d4:da:21:ac:71:60',length=72,name=b'lan3',port_no=3,properties=[OFPPortDescPropEthernet(advertised=59439,curr=10272,curr_speed=1000000,length=32,max_speed=1000000,peer=0,supported=59439,type=0)],state=4)]
有可能是这样:
OFPPort-------------- OFPPort(port_no=4,hw_addr='44:df:65:6d:01:55',name=b'lan4',config=0,state=1,curr=10240,advertised=59439,supported=59439,peer=0,curr_speed=0,max_speed=1000000)





OFPPC_PORT_DOWN = 1 << 0        # Port is administratively down.
OFPPC_NO_RECV = 1 << 2          # Drop all packets recieved by port.
OFPPC_NO_FWD = 1 << 5           # Drop packets forwarded to port.
OFPPC_NO_PACKET_IN = 1 << 6     # Do not send packet-in msgs for port.


OFPPS_LINK_DOWN = 1 << 0        # No physical link present.
OFPPS_BLOCKED = 1 << 1          # Port is blocked.
OFPPS_LIVE = 1 << 2             # Live for Fast Failover Group.


dpid------------ 1
body------------ [OFPPort(config=0,hw_addr='d4:da:21:ac:71:61',length=72,name=b'phy0-ap0',port_no=5,properties=[OFPPortDescPropEthernet(advertised=0,curr=0,curr_speed=0,length=32,max_speed=0,peer=0,supported=0,type=0)],state=4), OFPPort(config=0,hw_addr='d4:da:21:ac:71:60',length=72,name=b'lan4',port_no=4,properties=[OFPPortDescPropEthernet(advertised=59439,curr=10240,curr_speed=0,length=32,max_speed=1000000,peer=0,supported=59439,type=0)],state=1), OFPPort(config=0,hw_addr='d4:da:21:ac:71:60',length=72,name=b'lan2',port_no=2,properties=[OFPPortDescPropEthernet(advertised=59439,curr=10272,curr_speed=1000000,length=32,max_speed=1000000,peer=0,supported=59439,type=0)],state=4), OFPPort(config=0,hw_addr='d4:da:21:ac:71:60',length=72,name=b'br0',port_no=4294967294,properties=[OFPPortDescPropEthernet(advertised=0,curr=0,curr_speed=0,length=32,max_speed=0,peer=0,supported=0,type=0)],state=4), OFPPort(config=0,hw_addr='d4:da:21:ac:71:62',length=72,name=b'phy1-ap0',port_no=6,properties=[OFPPortDescPropEthernet(advertised=0,curr=0,curr_speed=0,length=32,max_speed=0,peer=0,supported=0,type=0)],state=4), OFPPort(config=0,hw_addr='d4:da:21:ac:71:60',length=72,name=b'lan3',port_no=3,properties=[OFPPortDescPropEthernet(advertised=59439,curr=10272,curr_speed=1000000,length=32,max_speed=1000000,peer=0,supported=59439,type=0)],state=4)]







get_switch()
register Switch<dpid=1, 
Port<dpid=1, port_no=5, LIVE> 
Port<dpid=1, port_no=4, DOWN> 
Port<dpid=1, port_no=2, LIVE> 
Port<dpid=1, port_no=6, LIVE> 
Port<dpid=1, port_no=3, LIVE>>

register Switch<dpid=1, 
Port<dpid=1, port_no=5, LIVE> 
Port<dpid=1, port_no=4, DOWN> 
Port<dpid=1, port_no=2, LIVE> 
Port<dpid=1, port_no=6, LIVE> 
Port<dpid=1, port_no=3, DOWN>>

get_link():
{<ryu.topology.switches.Link object at 0x7f62d2d5bd90>: 1682606594.2301195, <ryu.topology.switches.Link object at 0x7f62d2d661f0>: 1682606594.2316015}
src:
Port<dpid=2, port_no=2, LIVE>
Port<dpid=1, port_no=3, LIVE>
dst:
Port<dpid=1, port_no=3, LIVE>
Port<dpid=2, port_no=2, LIVE>

(Linux)ping未知的ip(例如169.254.38.78)时，获得的packet.protocols
{'ethernet': ethernet(dst='ff:ff:ff:ff:ff:ff',ethertype=2054,src='b8:27:eb:6a:50:2f'), 'arp': arp(dst_ip='169.254.38.78',dst_mac='00:00:00:00:00:00',hlen=6,hwtype=1,opcode=1,plen=4,proto=2048,src_ip='169.254.38.77',src_mac='b8:27:eb:6a:50:2f')}

(Windows)ping未知的ip(例如169.254.38.78)时，获得的packet.protocols
{'ethernet': ethernet(dst='ff:ff:ff:ff:ff:ff',ethertype=2054,src='b8:27:eb:6a:50:2f'), 'arp': arp(dst_ip='169.254.38.77',dst_mac='00:00:00:00:00:00',hlen=6,hwtype=1,opcode=1,plen=4,proto=2048,src_ip='0.0.0.0',src_mac='b8:27:eb:6a:50:2f')}




cat /proc/meminfo
MemTotal:         931432 kB
MemFree:          131240 kB
MemAvailable:     520756 kB
Buffers:           12544 kB
Cached:           411888 kB
SwapCached:            0 kB
Active:           559248 kB
Inactive:         127068 kB
Active(anon):     269856 kB
Inactive(anon):     1860 kB
Active(file):     289392 kB
Inactive(file):   125208 kB
Unevictable:          16 kB
Mlocked:              16 kB
SwapTotal:        102396 kB
SwapFree:         102396 kB
Zswap:                 0 kB
Zswapped:              0 kB
Dirty:               316 kB
Writeback:             0 kB
AnonPages:        262028 kB
Mapped:           175756 kB
Shmem:              9824 kB
KReclaimable:      39940 kB
Slab:              69560 kB
SReclaimable:      39940 kB
SUnreclaim:        29620 kB
KernelStack:        4928 kB
PageTables:         9112 kB
SecPageTables:         0 kB
NFS_Unstable:          0 kB
Bounce:                0 kB
WritebackTmp:          0 kB
CommitLimit:      568112 kB
Committed_AS:    1365764 kB
VmallocTotal:   259653632 kB
VmallocUsed:       12284 kB
VmallocChunk:          0 kB
Percpu:              704 kB
CmaTotal:         262144 kB
CmaFree:           95444 kB




cat /proc/cpuinfo(不可获得CPU使用率，弃用)
processor       : 0
BogoMIPS        : 38.40
Features        : fp asimd evtstrm crc32 cpuid
CPU implementer : 0x41
CPU architecture: 8
CPU variant     : 0x0
CPU part        : 0xd03
CPU revision    : 4

processor       : 1
BogoMIPS        : 38.40
Features        : fp asimd evtstrm crc32 cpuid
CPU implementer : 0x41
CPU architecture: 8
CPU variant     : 0x0
CPU part        : 0xd03
CPU revision    : 4

processor       : 2
BogoMIPS        : 38.40
Features        : fp asimd evtstrm crc32 cpuid
CPU implementer : 0x41
CPU architecture: 8
CPU variant     : 0x0
CPU part        : 0xd03
CPU revision    : 4

processor       : 3
BogoMIPS        : 38.40
Serial          : 000000000c3f057a
Model           : Raspberry Pi 3 Model B Plus Rev 1.3



top -bn 1 -i -c(可以获得CPU使用率)
top - 15:15:55 up 2 days, 23:04,  2 users,  load average: 0.08, 0.02, 0.01
任务: 220 total,   1 running, 178 sleeping,  41 stopped,   0 zombie
%Cpu(s):  6.3 us,  7.9 sy,  0.0 ni, 85.7 id,  0.0 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :    909.6 total,    124.1 free,    330.4 used,    455.1 buff/cache
MiB Swap:    100.0 total,    100.0 free,      0.0 used.    506.0 avail Mem 

 进程号 USER      PR  NI    VIRT    RES    SHR    %CPU  %MEM     TIME+ COMMAND
   9233 louis     20   0   10232   3428   2744 R  29.2   0.4   0:00.20 top -bn+



iostat -x (获取磁盘的IO负载情况，需要贪婪匹配) 需要安装 sudo apt install sysstat
Device            r/s     rkB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wkB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dkB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
mmcblk0          0.11      4.76     0.04  28.47    7.59    44.33    0.22      3.60     0.20  47.68   70.89    16.04    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.02   0.11
sda              0.00      0.01     0.00   2.69   15.00    17.61    0.22     25.62     0.00   1.20    7.40   116.20    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.17
sdb              0.42     26.54     0.00   0.74    6.23    63.84    0.00      0.00     0.00  50.00    4.00     1.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.14


2023年05月11日 20时24分33秒
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           0.81    0.00   22.64   31.54    0.00   45.01

Device            r/s     rkB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wkB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dkB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
mmcblk0          0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00
sda              0.00      0.00     0.00   0.00    0.00     0.00  132.00  15340.00     0.00   0.00    7.49   116.21    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.99 100.40
sdb            264.00  16896.00     0.00   0.00    6.32    64.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    1.67  92.40


2023年05月11日 20时24分34秒
avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           0.27    0.00   20.69   27.85    0.00   51.19

Device            r/s     rkB/s   rrqm/s  %rrqm r_await rareq-sz     w/s     wkB/s   wrqm/s  %wrqm w_await wareq-sz     d/s     dkB/s   drqm/s  %drqm d_await dareq-sz     f/s f_await  aqu-sz  %util
mmcblk0          0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    0.00   0.00
sda              0.00      0.00     0.00   0.00    0.00     0.00  138.00  16324.00     0.00   0.00    7.24   118.29    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    1.00 100.00
sdb            254.00  16256.00     0.00   0.00    6.72    64.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00      0.00     0.00   0.00    0.00     0.00    0.00    0.00    1.71  94.00




louis@raspberrypi:~ $ df -lm
文件系统       1M-块  已用  可用 已用% 挂载点
/dev/root      14627  3854 10123   28% /
devtmpfs         325     0   325    0% /dev
tmpfs            455     0   455    0% /dev/shm
tmpfs            182     3   180    2% /run
tmpfs              5     1     5    1% /run/lock
/dev/sda1      59789     1 56721    1% /share
/dev/mmcblk0p1   255    31   225   13% /boot
tmpfs             91     1    91    1% /run/user/1000
/dev/sdb1      14970  8983  5988   61% /media/louis/Ventoy




{(1, 2): (3, 2), (2, 1): (2, 3), (3, 2): (2, 3), (2, 3): (3, 2), (3, 4): (3, 2), (4, 3): (2, 3), (5, 4): (2, 3), (4, 5): (3, 2)}







