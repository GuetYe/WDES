# '''
# Author: louis
# Date: 2023-05-04 10:05:16
# Connection: louis.yyj.dev@foxmail.com
# FilePath: \N5105_share\arp_handler.py
# Description: 处理arp包、回复、泛洪、阻止arp环路风暴
#    注意，无论是ping还是使用iperf3发流，在发送数据包并且匹配不到流表时，都会发送arp请求，用于获取对方的mac地址(已测试并确认)
# '''
import sys
sys.path.append('../') # 添加工作目录，使得VSCode能够导入其他目录的python文件
from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.base.app_manager import lookup_service_brick
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import packet
from ryu.lib.packet import arp, ethernet, ipv4
import config.setting as setting

ETHERNET_MULTICAST = "ff:ff:ff:ff:ff:ff"

class NetworkArpHandler(app_manager.RyuApp):
    """
    主要用于处理arp包的回复、记录，并且解决arp的广播风暴
    """

    OPF_VERSION = [ofproto_v1_3.OFP_VERSION] # 指定OpenFlow1.3版本

    def __init__(self, *_args, **_kwargs):
        super(NetworkArpHandler, self).__init__(*_args, **_kwargs)
        self.name = "arp_handler"
        self.arp_table = {}  # 保存发送arp请求的主机信息(key=arp_src_ip, value=arp_src_mac)
        self.arp_topo_storm = {} # 记录arp请求的相关信息{(datapath.id, eth_src, arp_dst_ip):in_port}
        self.structure = lookup_service_brick("structure") # 通过ryu-app包可以直接通过名称导入另一个app类
        self.calculate_path = lookup_service_brick("calculate_path") # 通过ryu-app包可以直接通过名称导入另一个app类


    def arp_handler(self, pkg_header, datapath, in_port):
        """
        1) 解决环路拓扑的arp广播风暴、减少网络中泛洪的ARP请求数据
        2) 借用控制器代理回复ARP请求
        """
        eth_src = pkg_header['ethernet'].src  # 这是一个MAC地址
        eth_dst = pkg_header['ethernet'].dst  #

        # 1.解决拓扑环路arp风暴
        if (eth_dst == ETHERNET_MULTICAST) and ('arp' in pkg_header): # 判断arp泛洪请求，ETHERNET_MULTICAST = "ff:ff:ff:ff:ff:ff"
            arp_dst_ip = pkg_header['arp'].dst_ip # 取出arp包中的请求IP(目的)
            if (datapath.id, eth_src, arp_dst_ip) not in self.arp_topo_storm.keys(): # 不在以"dpid、eth_src、arp_dst_ip"为key的字典里
                self.arp_topo_storm[(datapath.id, eth_src, arp_dst_ip)] = in_port # 保存本次arp泛洪请求的包的入端口记录
            else: # 当发现dst在保存的字典中时，阻止arp请求在网路中到处泛洪，即将这个包进行丢弃处理(actions=空)
                out = datapath.ofproto_parser.OFPPacketOut(
                    datapath=datapath,
                    buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                    in_port=in_port,
                    actions=[], data=None)
                datapath.send_msg(out)
                # self.logger.info("<包已被阻止泛洪>") # 打印消息
                return True
        
        # 2.代理回复ARP请求-(利用控制器获取全局信息的能力，代替传统交换机进行arp回复)
        if 'arp' in pkg_header:
            # 解析数据包
            hwtype = pkg_header['arp'].hwtype
            proto = pkg_header['arp'].proto
            hlen = pkg_header['arp'].hlen
            plen = pkg_header['arp'].plen
            opcode = pkg_header['arp'].opcode

            arp_src_ip = pkg_header['arp'].src_ip
            arp_dst_ip = pkg_header['arp'].dst_ip

            actions = []

            if opcode == arp.ARP_REQUEST: # 判断该arp包是否是arp请求包(opcode=1代表这个是arp请求包)
                if arp_dst_ip in self.arp_table: # 检查能否在已知主机表中找到目的IP以及MAC地址，有则触发arp回复
                    actions.append(datapath.ofproto_parser.OFPActionOutput(in_port)) # 查到IP后，从数据包输入端回复arp请求
                    ARP_Reply = packet.Packet() # 构造arp回复包
                    ARP_Reply.add_protocol(ethernet.ethernet(ethertype=2054,
                                                             dst=eth_src,
                                                             src=self.arp_table[arp_dst_ip]))
                    ARP_Reply.add_protocol(arp.arp(opcode=arp.ARP_REPLY,
                                                   src_mac=self.arp_table[arp_dst_ip],
                                                   src_ip=arp_dst_ip,
                                                   dst_mac=eth_src,
                                                   dst_ip=arp_src_ip))
                    ARP_Reply.serialize()
                    # 由控制器来回复发送arp请求的主机，已找到目标ip和mac地址(即代理回复)
                    out = datapath.ofproto_parser.OFPPacketOut(
                        datapath=datapath,
                        buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                        in_port=datapath.ofproto.OFPP_CONTROLLER,
                        actions=actions,
                        data=ARP_Reply.data)
                    datapath.send_msg(out)
                    # self.logger.info("<arp_handler.py>    控制器已代理回复ARP请求!") # 打印消息
                    return True
        return False


    def arp_flood(self, arp_pkt, msg_data):
        """
        description: 泛洪arp包
        param {*} self
        param {*} arp_pkt
        param {*} msg_data
        return {*}
        """
        if (not self.structure.all_switchs_dpid_list) or (not self.structure.all_sw_ports):
            return
        arp_dst_ip = arp_pkt.dst_ip # 取出arp包中的目的IP
        result = self.calculate_path.according_to_hostIP_get_sw_dpid(arp_dst_ip) # 尝试寻找对方主机所连接的交换机的<dpid, in_port>
        if result != None: # 找到了这个主机的位置(实质上是找到连接该主机的交换机位置)，直接转发数据到这个主机上
            dst_host_sw_dpid, dst_host_sw_port = result  # 取dpid、in_port
            datapath = self.structure.all_sw_datapaths[dst_host_sw_dpid] # 取出目的主机交换机的datapath信息
            actions = [datapath.ofproto_parser.OFPActionOutput(dst_host_sw_port)] # 动作-向这个目的交换机连接的主机的端口发数据，端口来源-控制器
            out = datapath.ofproto_parser.OFPPacketOut(datapath=datapath, buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                                                       in_port=datapath.ofproto.OFPP_CONTROLLER, 
                                                       data=msg_data, actions=actions)
            datapath.send_msg(out)
            # self.logger.info("<已找到目标主机位置>") # 打印消息
        else: # 泛洪-flooding
            # 遍历所有交换机的所有port(端口)，泛洪这个arp请求(注意：连接了主机的端口不必泛洪)
            for each_dpid in self.structure.all_switchs_dpid_list:
                # arp加载在建立topo之前，则结束此次循环，等待下次
                # if (not self.structure.all_sw_ports) or (each_dpid not in self.structure.all_sw_ports): 
                #     return
                for each_sw_port in self.structure.all_sw_ports[each_dpid]:
                    if (each_dpid, each_sw_port) not in self.calculate_path.host_access_table: # 保证泛洪的端口不含连接主机的端口
                        if msg_data != None: # Packet_in的数据不能为None
                            datapath = self.structure.all_sw_datapaths[each_dpid] # 取出该交换机的datapath信息
                            actions = [datapath.ofproto_parser.OFPActionOutput(each_sw_port)] # 构造actions
                            out = datapath.ofproto_parser.OFPPacketOut(datapath=datapath, buffer_id=datapath.ofproto.OFP_NO_BUFFER,
                                                        in_port=datapath.ofproto.OFPP_CONTROLLER, 
                                                        data=msg_data, actions=actions)
                            datapath.send_msg(out)
            # self.logger.info("<泛洪>") # 打印消息
    
                            

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath

        in_port = msg.match['in_port'] # 取出数据包进入的交换机端口号
        pkt = packet.Packet(data=msg.data) # 取出数据主体

        arp_pkt = pkt.get_protocol(arp.arp) # 解析arp层(数据链路层，用户获取包的来源、MAC和IP)
        
        # 1.解析并保存ping未知ip时发送的包的协议及数据
        pkg_header = {} # 保存数据包里包含的所有协议及内容(key=协议名，value=协议内容)
        for each_protocol in pkt.protocols:
            if type(each_protocol) != bytes: # 当2个已建立连接的主机，期间会发送数据包，protocol类型是bytes，所以这里只解析保存非bytes的包
                pkg_header.setdefault(each_protocol.protocol_name, each_protocol)
        # 2.处理arp
        if isinstance(arp_pkt, arp.arp):
            arp_src_ip = arp_pkt.src_ip
            arp_src_mac = arp_pkt.src_mac
            # 同calculate_shortest_path.py一样，解决Windosw未设置IP时发arp包会出现src_ip=0.0.0.0的问题
            if arp_src_ip == "0.0.0.0":
                arp_src_ip = arp_pkt.dst_ip

            # 存储arp信息
            self.arp_table.setdefault(arp_src_ip, arp_src_mac) # 保存发送arp请求的主机信息(此表其实就是host_access_table的value)
            if self.arp_handler(pkg_header, datapath, in_port): # 1:控制器代理回复 or 丢弃  |  0:arp数据包泛洪
                return None
            else:
                self.arp_flood(arp_pkt, msg.data) # 泛洪
    
    def show_arp_handler_msg(self):
        if not setting.DEBUG_ARP_HANDLER:
            self.logger.info("<arp_utils.py>      监测并处理<arp回复、arp风暴>")
        else:
            self.logger.info("<arp_utils.py>      arp_handler调试模式")
