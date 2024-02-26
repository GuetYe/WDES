# '''
# Author: louis
# Date: 2023-06-01 17:43:51
# Connection: louis.yyj.dev@foxmail.com
# FilePath: \N5105_share\SDN_Project\ryu_app\host_get_state.py
# Description: xxx
# '''
import sys
sys.path.append('../') # 添加工作目录，使得VSCode能够导入其他目录的python文件
from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import packet, ipv4, ethernet, tcp, arp
from ryu.lib.packet import ether_types
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
import config.setting as setting
import re
import time

class Host_Get_MSG(app_manager.RyuApp):
    def __init__(self, *_args, **_kwargs):
        super(Host_Get_MSG, self).__init__(*_args, **_kwargs)
        self.name = 'host_get_msg'
        self.structure = lookup_service_brick("structure") #导入其他RYU APP
        self.calculate_path = lookup_service_brick("calculate_path") 
        self.MADM = lookup_service_brick("MADM") 
        self.search_stats_method = re.compile(r'.+HostStats\(IO_load=(?P<IO_load>\d+.\d+?),Cpu_Uti=(?P<Cpu_Uti>\d+.\d+?),Mem_uti=(?P<Mem_uti>\d+.\d+?),Remain_Capacity=(?P<Remain_Capacity>\d+.\d+?)\)\]')
        self.search_request_method = re.compile(r'.+ClientRequest\(file_name=(?P<file_name>\S+.\S+?),file_size=(?P<file_size>\d+?)\)\]')
        self.all_host_stats = {} # 记录所有主机的当前状态{host_ip:[IO_load, Cpu_Uti, Mem_uti, Remain_Capacity], ...}


    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        original_data = ev.msg.data
        data_str = str(original_data)

        # 解析IPv4层
        pkt = packet.Packet(data=original_data)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
        if ipv4_pkt == None: # 其他消息，不进行下一步操作
            return
        src_host_ip = ipv4_pkt.src # 取出上报的主机IP
        known_host_list = [host_ip[0] for host_ip in self.calculate_path.host_access_table.values()]
        if src_host_ip not in known_host_list: # 非已知主机消息
            return

        if self.search_stats_method.search(data_str) != None: # 检测是否是主机上报的状态数据
            IO_load = round(float(self.search_stats_method.search(data_str).group('IO_load')), 2)
            Cpu_Uti = round(float(self.search_stats_method.search(data_str).group('Cpu_Uti')), 2)
            Mem_uti = round(float(self.search_stats_method.search(data_str).group('Mem_uti')), 2)
            Remain_Capacity = round(float(self.search_stats_method.search(data_str).group('Remain_Capacity')), 2)

            # 解析IPv4层
            pkt = packet.Packet(data=original_data)
            ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
            src_host_ip = ipv4_pkt.src # 取出上报状态的主机IP

            # 存储主机的状态信息
            self.all_host_stats[src_host_ip] = [IO_load, Cpu_Uti, Mem_uti, Remain_Capacity]

        elif self.search_request_method.search(data_str) != None: # 检测是否是Client的存储文件请求
            # print("文件请求!")
            
            if self.MADM is None:
                self.MADM = lookup_service_brick("MADM") 
            # 1.取出上报的文件信息
            file_name = self.search_request_method.search(data_str).group('file_name')
            file_size = self.search_request_method.search(data_str).group('file_size')

            # 2.解析IPv4层
            pkt = packet.Packet(data=original_data)
            ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
            src_host_ip = ipv4_pkt.src # 取出上报状态的主机IP

            # 3.检查该主机连接的交换机和端口是否已知，未知则不处理
            datapath = None
            port = None
            host_mac = None
            # 找到主机的信息
            for host_key, host_value in self.calculate_path.host_access_table.items():
                if src_host_ip == host_value[0]:
                    datapath = self.structure.all_sw_datapaths[host_key[0]] # 取出连接主机的交换机的datapath
                    port = host_key[1]
                    host_mac = host_value[1]
                    break
            
            if datapath == None:
                print("找不到已知主机的交换机datapath信息")
                return
            print("\n★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★")
            print("<host_get_msg.py>   客户端发送文件传输请求！")

            # 运行多属性决策算法，计算分割文件结果
            split_result = self.MADM.calculate(host_ip=src_host_ip, file_name=file_name, file_size=file_size)
            if split_result:
                # 转发到申请的交换机的主机上
                ofproto = datapath.ofproto
                parser = datapath.ofproto_parser

                # 构造ARP回复包，附带结果数据，有控制器执行packet_out，返回到申请的主机上
                pkt = packet.Packet()
                pkt.add_protocol(ethernet.ethernet(ethertype=ether_types.ETH_TYPE_ARP,
                                                dst=host_mac,
                                                src=setting.CONTROLLER_MAC)) # 这里的mac随意写，只是用作构造ARP包
                pkt.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                        src_mac=setting.CONTROLLER_MAC,
                                        src_ip=setting.CONTROLLER_IP,
                                        dst_mac=host_mac,
                                        dst_ip=src_host_ip))
                
                pkt.serialize()
                my_data = '[SplitResult(split_result=%s)]' %split_result
                data = pkt.data + bytearray(my_data.encode())
                actions = [parser.OFPActionOutput(port)]
                out = parser.OFPPacketOut(datapath=datapath,
                                        buffer_id=ofproto.OFP_NO_BUFFER,
                                        in_port=ofproto.OFPP_CONTROLLER,
                                        actions=actions,
                                        data=data)
                
                time.sleep(3) # 延迟一段时间，等待主机方启动完监听回复ARP包
                datapath.send_msg(out)
                print("<host_get_msg.py>   计算结果已返回主机 %s" %src_host_ip)
                print("★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★ ★\n")
                
            
            

            