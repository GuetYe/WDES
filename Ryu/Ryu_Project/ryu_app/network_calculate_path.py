# '''
# Author: louis
# Date: 2023-05-03 17:27:45
# Connection: louis.yyj.dev@foxmail.com
# FilePath: \N5105_share\calculate_shortest_path.py
# Description:计算最短路径
# '''

from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller.handler import set_ev_cls, MAIN_DISPATCHER
from ryu.controller import ofp_event
from ryu.lib.packet import packet, arp, ipv4, ethernet
from ryu.lib.packet import ether_types
from ryu.lib import hub
import networkx as nx
import config.setting as setting

class NetworkShortestPath(app_manager.RyuApp):
    """测量链路的最短路径，并下发流表"""
    def __init__(self, *_args, **_kwargs):
        super(NetworkShortestPath, self).__init__(*_args, **_kwargs)
        self.name = "calculate_path"
        self.structure = lookup_service_brick("structure") # 通过ryu-app包可以直接通过名称导入另一个app类
        self.monitor = lookup_service_brick("monitor") # 通过ryu-app包可以直接通过名称导入另一个app类
        self.all_shortest_path = {}  # 保存所有交换机之间最短路径
        self.host_access_table = {}  # 主机对应交换机信息表，保存哪个交换机的哪个端口连接了主机，ip和mac是啥 {(dpid, in_port): (src_ip, src_mac)}
        if setting.DEBUG_SHORTEST_PATH:
            self.calculate_path_thread = hub.spawn(self.calculate_path_thread)  # 注册循环协程


    def according_to_hostIP_get_sw_dpid(self, host_ip):
        """
        # description: 通过主机ip，寻找连接该主机的交换机dpid与in_port
        # param {*} self-可传入类本身属性
        # param {*} host_ip-主机ip地址
        # return {*} None
        """
        for each_key in  self.host_access_table.keys():  # self.access_table{((dpid, in_port):(src_ip, src_mac)), ...}
            if  self.host_access_table[each_key][0] == host_ip:
                return each_key

        #self.logger.info("抱歉，找不到该host的位置，请检查host_access_table")
        return None

 
    def according_to_packet_ip_get_dpid(self, reported_sw_dpid, reported_sw_in_port, src_ip, dst_ip):
        """
        # description: 根据数据包使用get_protocol(IPv4)解出的数据，获取<源交换机dpid>和<目的交换机dpid>
        # param {*} self-可传入类本身属性
        # param {*} reported_sw_dpid-上报数据的交换机dpid
        # param {*} reported_sw_in_port-上报数据的交换机端口号
        # param {*} src_ip-数据包源ip
        # param {*} dst_ip-数据包目的ip
        # return {*}
        """
        # 其实该ip正确的应该是指主机的ip，但为了便于理解，也可以将ip说成是连接主机的那个交换机ip
        # 1.找到连接这两个主机的两个交换机，获取数据格式为：(dpid, in_port)
        src_sw = self.according_to_hostIP_get_sw_dpid(src_ip)
        dst_sw = self.according_to_hostIP_get_sw_dpid(dst_ip)

        # 2.必须要找到连接这两个主机的交换机信息
        if (src_sw != None) and (dst_sw != None):
            if reported_sw_in_port not in self.structure.not_use_sw_ports[reported_sw_dpid]: # 数据包来源的端口必须是接在未接到交换机的端口上
                # if (reported_sw_dpid, reported_sw_in_port) != src_sw: # 检查上报的交换机信息和已存储的交换机信息是否一致(废弃，更换WIFI会使得与保存信息不一致)
                self.logger.info("抱歉，上报数据的交换机与存储的信息不一致 in_port: %d", reported_sw_in_port)
                self.logger.info("not_use_sw_ports: %s", self.structure.not_use_sw_ports[reported_sw_dpid])
                return None
            if dst_sw[1] not in self.structure.not_use_sw_ports[dst_sw[0]]:  # 检查目的交换机的端口是否是连接到主机的端口
                self.logger.info("抱歉，寻找目的主机的交换机端口不在存储信息中")
                return None
        else:
            # self.logger.info("抱歉，获取源或目的交换机信息失败")
            return None

        # 3.检查完毕则返回源、目的交换机的dpid
        return src_sw[0], dst_sw[0]

    
    def calculate_weight(self, node_1, node_2, weight_dict):
        """
        # description: 计算该边的总权重,weight_dict字典是nx模块内置的，无法更改名称
        # param {*} self-可传入类本身属性
        # param {*} node_1-初始节点(没用到)
        # param {*} node_2-结尾节点(没用到)
        # param {*} weight_dict-权重因子的字典，在添加边的时候增加的
        # return {*} 总权重
        """
        if setting.SHOW_WEIGHT_PARAM:
            self.logger.info("权重参数：/n")
            self.logger.info('bw---%f', weight_dict['bw'])
            self.logger.info('delay--%f',weight_dict['delay'])
            self.logger.info('loss---%f',weight_dict['loss'])
            self.logger.info('load---%f',weight_dict['load'])
            self.logger.info('cpu_uti---%f',weight_dict['cpu_uti'])
            self.logger.info('memory_uti---%f',weight_dict['memory_uti'])
        return 1
        

    def calculate_shortest_path_between_two_sw(self, src_dpid, dst_dpid, weight):
        """
        # description: 计算两个交换机之间的最短路径并保存
        # param {*} self-可传入类本身属性
        # param {*} src_dpid-源交换机dpid
        # param {*} dst_dpid-目的交换机dpid
        # param {*} weight-权重
        # return {*} None
        """
        shortest_path = nx.shortest_path(self.structure.network_topology,  # 传入structure.py文件获取到的网络拓扑图
                                         src_dpid, dst_dpid, 
                                         weight=weight,
                                         method="dijkstra") 
        self.all_shortest_path.setdefault((src_dpid, dst_dpid), shortest_path) # 保存到表里
        return shortest_path


    def calculate_shortest_path(self, reported_sw_dpid, reported_sw_in_port, src_ip, dst_ip):
        """
        
        """
        # 1.找出源、目的交换机的dpid
        result = self.according_to_packet_ip_get_dpid(reported_sw_dpid, reported_sw_in_port, src_ip, dst_ip)
        if result == None: # 检查
            return None
        src_sw_dpid, dst_sw_dpid = result
        shortest_path = self.calculate_shortest_path_between_two_sw(src_sw_dpid, dst_sw_dpid, weight=self.calculate_weight) # 计算最短路径(迪杰斯特拉)
        return shortest_path

 
    def according_to_dpid_get_link_port(self, src_sw_dpid, dst_sw_dpid):
        """
        # description: 根据两个交换机的dpid，从表中寻找这两个交换机的连接端口，一一对应
        # param {*} self-可传入类本身属性
        # param {*} src_sw_dpid-源交换机的dpid
        # param {*} dst_sw_dpid-目的交换机的dpid
        # return {*} None
        """
        if (src_sw_dpid, dst_sw_dpid) in self.structure.all_sw_links: # 查找存储的连接信息
            src_sw_port_no, dst_sw_port_no = self.structure.all_sw_links[(src_sw_dpid, dst_sw_dpid)]
            return src_sw_port_no, dst_sw_port_no
        else:
            self.logger.warning("找不到这两个交换机对应的连接端口")
            return None

  
    def according_hostIP_get_host_port(self, input_host_ip):
        """
        # description: 根据输入的目标主机IP，获得连接该主机的交换机的端口号
        # param {*} self-可传入类本身属性
        # param {*} dst_host_ip-目标主机IP号
        # return {*} 连接该主机的交换机端口号
        """
        for host_connect_sw_info in self.host_access_table.keys():
            search_host_ip = self.host_access_table[host_connect_sw_info][0]
            if input_host_ip == search_host_ip: # 如果找到了该主机的信息
                host_connect_sw_port = host_connect_sw_info[1] # 取出目标主机连接交换的端口号
                return host_connect_sw_port
        return None

    def add_flow(self, datapath, src_ip, dst_ip, src_port, dst_port, eth_type, priority=1, buffer_id=None, hard_timeout=None):
        """
        # description: 流表下发函数
        # param {*} self-可传入类本身属性
        # param {*} datapath-交换机的datapath信息
        # param {*} src_port-匹配入口
        # param {*} dst_port-转发出口
        # param {*} src_ip-匹配IP包
        # param {*} dst_ip-匹配IP包
        # param {*} eth_type-ethernet协议
        # param {*} priority-流表优先级
        # param {*} buffer_id-缓冲区标记位
        # return {*} None
        """
        parser = datapath.ofproto_parser # 提取解析器
        ofproto = datapath.ofproto
        # 构造流表
        match = parser.OFPMatch(in_port=src_port, eth_type=eth_type, ipv4_src=src_ip, ipv4_dst=dst_ip) # 设定流表的匹配域：指定端口及IPv4包
        actions = [parser.OFPActionOutput(dst_port)] # 构造actions，转发数据包到指定交换机端口
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # 立即应用
        # 这里idle_timeout、hard_timeout决定了流表的到期时间 都设置为0代表流表永久有效
        # 这里我们为什么不永久有效呢？因为我们需要时不时根据网络状态计算最新的最短路径，如果流表永久有效，就无法更新最新的流表到交换机中
        if buffer_id: # 如果数据包被标记buffer_id
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst,
                                    idle_timeout=0, hard_timeout=hard_timeout) # 设置60秒的流表过期时间
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority, match=match, instructions=inst)

        datapath.send_msg(mod)
        return 

  
    def install_flow(self, shortest_path, eth_type, src_host_ip, dst_host_ip, in_port, buffer_id, data=None):
        """
        # description: 根据计算出的最短路径，下发流表
        # param {*} self-传入类本身属性
        # param {*} shortest_path-最短路径列表
        # param {*} eth_type-pkg_ethernet类型
        # param {*} src_host_ip-源主机IP
        # param {*} dst_host_ip-目标主机IP
        # param {*} in_port-数据包入端口
        # param {*} buffer_id-msg中的buffer_id 
        # param {*} data-msg.data数据
        # return {*} 下发情况:True=下发成功  False=下发失败
        """
        path_length = len(shortest_path) # 计算路径长度，长度=2和>2使用两个不同代码块下发流表
        last_sw_link_port = None # 记录最后一个交换机的入端口
        hard_timeout = setting.FLOW_EFFECTIVE_DURATION

        first_sw_datapath = self.structure.all_sw_datapaths[shortest_path[0]] # 取出最短路径的第一个交换机datapath信息
        last_sw_datapath = self.structure.all_sw_datapaths[shortest_path[-1]] # 取出最短路径的最后一个交换机datapath信息

        # 获取2个主机连接交换机的端口号
        src_host_connect_sw_port = self.according_hostIP_get_host_port(src_host_ip)
        dst_host_connect_sw_port = self.according_hostIP_get_host_port(dst_host_ip)

        # 1.当路径中只有1个交换机时，直接此交换机下发双向流表即可
        if path_length == 1:
            self.add_flow(first_sw_datapath, src_host_ip, dst_host_ip, src_host_connect_sw_port, dst_host_connect_sw_port,
                          eth_type, priority=setting.FLOW_PRIORITY, buffer_id=buffer_id, hard_timeout=hard_timeout) # 下发正向流表
            self.add_flow(first_sw_datapath, dst_host_ip, src_host_ip, dst_host_connect_sw_port, src_host_connect_sw_port,
                          eth_type, priority=setting.FLOW_PRIORITY, buffer_id=buffer_id, hard_timeout=hard_timeout) # 下发反向流表
            return True
            

        # 2.路径中交换机个数>=2时，可以先处理第一个交换机的流表下发，因为下发方式都一样
        # 第一个交换机的数据包入端口肯定是和主动发包的主机的端口一致，判断后下发第一个交换机的双向流表
        if src_host_connect_sw_port == in_port: 
            first_sw_link_port, two_sw_link_port = self.according_to_dpid_get_link_port(shortest_path[0], shortest_path[1]) # 查询sw1连接sw2的link端口信息
            self.add_flow(first_sw_datapath, src_host_ip, dst_host_ip, src_host_connect_sw_port, first_sw_link_port,
                          eth_type, priority=setting.FLOW_PRIORITY, buffer_id=buffer_id, hard_timeout=hard_timeout) # 下发正向流表
            self.add_flow(first_sw_datapath, dst_host_ip, src_host_ip, first_sw_link_port, src_host_connect_sw_port,
                          eth_type, priority=setting.FLOW_PRIORITY, buffer_id=buffer_id, hard_timeout=hard_timeout) # 下发反向流表
        else:
            self.logger.warning("数据包入端口与主机端口不一致")

        # 3.当最短路只含2个交换机
        if path_length == 2:
            last_sw_link_port = two_sw_link_port # 只有2个交换机的情况，那么只需要将sw2的link_port与目标主机连接的端口一起下发双向流表即可
            self.add_flow(last_sw_datapath, src_host_ip, dst_host_ip, last_sw_link_port, dst_host_connect_sw_port,
                          eth_type, priority=setting.FLOW_PRIORITY, buffer_id=buffer_id, hard_timeout=hard_timeout) # 下发正向流表
            self.add_flow(last_sw_datapath, dst_host_ip, src_host_ip, dst_host_connect_sw_port, last_sw_link_port,
                          eth_type, priority=setting.FLOW_PRIORITY, buffer_id=buffer_id, hard_timeout=hard_timeout) # 下发反向流表
            return True
        
        # 4.当最短路大于2个交换机时(端口比较复杂，自己画个图就搞清楚了)
        elif path_length > 2:
            for sw_num in range(1, path_length): # 从第二个交换机开始遍历
                each_dpid = shortest_path[sw_num] # 取出交换机dpid
                each_datapath = self.structure.all_sw_datapaths[each_dpid] # 取出该交换机的datapath
                # 找到 第 n-1 和 n 号交换机的link端口、以及第 n 和 n+1 号交换机的link端口
                pre_sw_out_port, now_sw_in_port = self.according_to_dpid_get_link_port(shortest_path[sw_num-1], shortest_path[sw_num])
                now_sw_out_port, next_sw_in_port = self.according_to_dpid_get_link_port(shortest_path[sw_num], shortest_path[sw_num+1])
                # 下发双向流表
                self.add_flow(each_datapath, src_host_ip, dst_host_ip, now_sw_in_port, now_sw_out_port,
                        eth_type, priority=setting.FLOW_PRIORITY, buffer_id=buffer_id, hard_timeout=hard_timeout) # 下发正向流表
                self.add_flow(each_datapath, dst_host_ip, src_host_ip, now_sw_out_port, now_sw_in_port,
                        eth_type, priority=setting.FLOW_PRIORITY, buffer_id=buffer_id, hard_timeout=hard_timeout) # 下发反向流表
                # 如果遍历到了倒数第二个交换机时，直接下发最后一个交换机的流表即可，然后跳出遍历
                if sw_num == (path_length - 2):
                    last_sw_dpid = shortest_path[-1]  # 取出最后一个交换机的dpid
                    last_sw_datapath = self.structure.all_sw_datapaths[last_sw_dpid]  # 取出最 后一个交换机的datapath
                    last_sw_link_port = next_sw_in_port  # 取出最后一个交换机与上一个交换机连接的端口
                    self.add_flow(last_sw_datapath, src_host_ip, dst_host_ip, last_sw_link_port, dst_host_connect_sw_port,
                            eth_type, priority=setting.FLOW_PRIORITY, buffer_id=buffer_id, hard_timeout=hard_timeout) # 下发正向流表
                    self.add_flow(last_sw_datapath, dst_host_ip, src_host_ip, dst_host_connect_sw_port, last_sw_link_port,
                            eth_type, priority=setting.FLOW_PRIORITY, buffer_id=buffer_id, hard_timeout=hard_timeout) # 下发反向流表
                    return True
        return False
                    

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        """
        # description: 收到交换机发送的数据包并处理
        # param {*} self-可传入类本身属性
        # param {*} ev-PacketIn事件携带的消息体
        # return {*} None
        """
        msg = ev.msg
        datapath = msg.datapath

        # 1.解包
        # ARP（Address Resolution Protocol）即地址解析协议，用于实现从IP地址到MAC地址的映射，即询问目标IP对应的MAC地址。
        # 例如：当H1需要ping H2时，我们仅输入了H2的ip地址，并未知道H2的MAC地址，此时会出发ARP_Request到H2，那么H2就会返回自己的MAC地址给H1
        in_port = msg.match['in_port'] # 取出数据包进入的交换机端口号
        pkt = packet.Packet(data=msg.data) # 取出数据主体

        arp_pkt = pkt.get_protocol(arp.arp) # 解析arp层(数据链路层，用户获取包的来源、MAC和IP)
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]  # 解析ethernet层(数据链路层，用于判断是否为LLDP报文)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4) # 解析IPv4层
        
        eth_type = eth_pkt.ethertype
        

        # 2.判断是否是LLDP报文的数据包，如果是则不处理该数据
        if eth_type == ether_types.ETH_TYPE_LLDP:
            #self.logger.info("检测到LLDP Packet...") # 忽略LLDP报文
            return

        # 3.解析arp内容，并存储主机的通路信息到host_access_table表中
        # 这里注意，当数据包查到流表可以转发时，不会触发该arp解析
        arp_src_ip = None
        arp_src_mac = None
        if isinstance(arp_pkt, arp.arp): # 判断解析arp是否成功
            arp_src_ip = arp_pkt.src_ip   # 获取数据包来源的ip地址
            arp_src_mac = arp_pkt.src_mac # 获取数据包来源的mac地址
            # 1.判断端口 
            if datapath.id not in self.structure.not_use_sw_ports: # 还未更新not_use_sw_ports，不解析
                return
            if in_port not in self.structure.not_use_sw_ports[datapath.id]: # 数据包来源端口必须是可以连接主机的端口
                # self.logger.info("不可使用的端口")
                return
            # 2.解决Windosw未设置IP时发arp包会出现src_ip=0.0.0.0的问题
            if arp_pkt.src_ip == "0.0.0.0":
                arp_src_ip = arp_pkt.dst_ip

            change_key = None # 该包的src_ip是否已知
            # 3.如果主机更换了WiFi或者有线接口，则需要覆盖原始的字典key(dpid, port_no)
            for key in self.host_access_table.keys():
                if arp_src_ip == self.host_access_table[key][0]: # 如果在已存储的主机信息表中找到了IP，则需要覆盖原始的key信息
                    change_key = key # 不能在字典遍历期间更改key，否则报错
                    break
            if change_key != None: # 更新key值
                self.host_access_table[(datapath.id, in_port)] = self.host_access_table.pop(change_key)
            else:
                # 4.存储
                if arp_src_ip != setting.CONTROLLER_IP: # 不存储控制器IP
                    self.host_access_table.setdefault((datapath.id, in_port), (arp_src_ip, arp_src_mac))

        # 5.必须解决arp回复问题(arp_handler.py 中处理了)，否则不会触发iperf或ping发送tcp的IP包
        if isinstance(ipv4_pkt, ipv4.ipv4):
            src_host_ip = ipv4_pkt.src
            dst_host_ip = ipv4_pkt.dst
            # 目的是交换机IP的包，多半是主机上传的状态包，此时不要下发流表，否则在流表有效期内会接收不到主机的状态更新
            if dst_host_ip == setting.CONTROLLER_IP:  
                return
            shortest_path = self.calculate_shortest_path(datapath.id, in_port, src_host_ip, dst_host_ip) # 计算最短路径
            
            # ------------------------------------------------
            # 下发流表
            if shortest_path != None: # 只有路径不为空时才能下发流表
                self.logger.info("<calculate_path.py> %s 对 %s 发起连接", src_host_ip, dst_host_ip)
                path_group = '[ '
                for each_path in shortest_path: # 处理数据，将dpid以16进制显示，
                    path_group += '{:01X} '.format(each_path)
                path_group += ']'
                self.logger.info("<calculate_path.py> 最短路径计算结果：%s", path_group)
                eth_type = ether_types.ETH_TYPE_IP
                result = self.install_flow(shortest_path, eth_type, src_host_ip, dst_host_ip, in_port, msg.buffer_id, msg.data)
                if result:
                    self.logger.info("<calculate_path.py> 完成路径流表下发！流表存在时间：%ds \n", setting.FLOW_EFFECTIVE_DURATION)
    

    def update_network_state(self):
        """
        description: 更新网络状态-剩余带宽、时延、丢包率
        param {*} self-传入类本身属性
        return {*} None
        """
        # 1.计算并更新图中边的带宽
        for src_dpid, dst_dpid in list(self.structure.all_sw_links.keys()):
            # 交换机的端口必须在已测好的带宽数据中，否则不更新带宽
            if src_dpid in self.monitor.all_port_remain_bandwidth.keys() and \
            dst_dpid in self.monitor.all_port_remain_bandwidth.keys():
                src_port = self.structure.all_sw_links[(src_dpid, dst_dpid)][0] # 取出一个交换机的连接端口
                dst_port = self.structure.all_sw_links[(src_dpid, dst_dpid)][1] # 取出另一个交换机的连接端口
                src_link_port_remain_bw = self.monitor.all_port_remain_bandwidth[src_dpid][src_port] # 取出monitor中更新的带宽值
                dst_link_port_remain_bw = self.monitor.all_port_remain_bandwidth[dst_dpid][dst_port]
                remain_bw = min(src_link_port_remain_bw, dst_link_port_remain_bw) # 二者取其最小，作为端口的剩余带宽
                self.structure.network_topology[src_dpid][dst_dpid]['bw'] = remain_bw # 更新图中边的带宽值

        # 2.计算并更新图中边的时延
        for src_dpid, dst_dpid in list(self.structure.all_sw_links.keys()):
            delay = self.monitor.calculate_delay(src_dpid, dst_dpid) #
            self.structure.network_topology[src_dpid][dst_dpid]['delay'] = delay # 更新图中边的延时

        # 3.计算并更新图中边的丢包率
        for (src_dpid, dst_dpid) in list(self.structure.all_sw_links.keys()):
            if self.structure.sw_change_flag: # 交换机更新中，不计算loss
                break
            if (src_dpid, dst_dpid) not in self.monitor.all_links_loss.keys():
                break
            loss_forward = self.monitor.all_links_loss[(src_dpid, dst_dpid)]
            loss_backward = self.monitor.all_links_loss[(dst_dpid, src_dpid)]
            if loss_forward == () or loss_backward == (): # 还未有loss值，不更新
                break
            loss = max(loss_forward, loss_backward) # 严格的策略
            self.structure.network_topology[src_dpid][dst_dpid]['loss'] = loss # 更新图中边的丢包率

        self.logger.info("<calculate_path.py> 完成链路<带宽、时延、丢包率>更新")


    # 单文件调试的协程
    def calculate_path_thread(self):
        """
        协程：循环更新网络拓扑
        """
        while True: # setting中设置是否开启structure
            self.update_network_state() # 主动刷新拓扑结构
            hub.sleep(5) # 让出权限