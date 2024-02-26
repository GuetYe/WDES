# '''
# Author: louis
# Date: 2023-04-28 21:39:25
# Connection: louis.yyj.dev@foxmail.com
# FilePath: \N5105_share\monitor.py
# Description: xxx
# '''

from operator import attrgetter
import time
from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
from ryu.controller.handler import set_ev_cls
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller import ofp_event
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
from ryu.lib.packet import packet, ethernet, ether_types
from ryu.topology.switches import LLDPPacket, Switches
import config.setting as setting

OFPPC_UP = 0 # 新增port_config状态"0"

class NetworkMonitor(app_manager.RyuApp):
    """
    发送请求，并测量带宽、时延、丢包率
    ev的内容是随时变化的，跟随监听的事件不同而变化
    """
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'switches': Switches} # 实例化一个Switches类，后续用于LLDP测量时延
    def __init__(self, *_args, **_kwargs) -> None:
        """
        -> None:增加代码可读性，告诉你这里返回的是一个None数据
        这是mypy团队要求的，目前非硬性要求，可用可不用。
        """
        super(NetworkMonitor, self).__init__(*_args, **_kwargs)
        self.name = "monitor"
        self.structure = lookup_service_brick("structure")
        # switches中的PortData类记录交换机的端口信息，self.timestamp为LLDP包在发送时被打上的时间戳，用于测量时延
        self.switches = lookup_service_brick('switches') 
        self.all_sw_datapaths = {}
        # 详细解释见ryu->ryu->ofproto->ofproto_v1_3.py文件
        self.port_config_dict = {ofproto_v1_3.OFPPC_PORT_DOWN: 'Port Down',
                                 ofproto_v1_3.OFPPC_NO_RECV: 'No Recv',
                                 ofproto_v1_3.OFPPC_NO_FWD: 'No Forward',
                                 ofproto_v1_3.OFPPC_NO_PACKET_IN: 'No Pakcet-In',
                                 OFPPC_UP: 'UP'} # 交换机端口config描述信息定义
        self.port_state_dict = {ofproto_v1_3.OFPPS_LINK_DOWN: "Link Down",
                                ofproto_v1_3.OFPPS_BLOCKED: "Blocked",
                                ofproto_v1_3.OFPPS_LIVE: "Live"} # 交换机端口state描述信息定义
        self.all_port_features = {}  # {dpid: {port_no:(config, state, curr_speed, max_speed), ...}}
        self.all_port_stats = {} # {(dpid, port_no): [(tx_bytes, rx_bytes, rx_errors,duration_sec, duration_nsec), .....]}
        self.all_port_remain_bandwidth = {} # {dpid:{port_no1:1000Mbit/s, port_no2:800Mbit/s...}...}

        self.all_sw_echo_delay = {}  # {dpid: ryu_to_sw_delay...}
        self.all_sw_lldp_delay = {}  # {src_dpid: {dst_dpid: delay, ...} ...} 存储所有的相邻交换机的lldp延时(c -> sw1 -> sw2 -> c)
        self.all_sw_to_sw_delay = {}  # {dpid: {dst_dpid1: delay, dst_dpid2: delay}} # 存储最终相邻交换机的时延(sw1 -> sw2)
        self.all_links_loss = {} # {(src_dpid, dst_dpid): loss, ...}

        # 仅单独调试monitor文件时，才注册协程单独运行
        if setting.DEBUG_MONITOR:
            self.monitor_thread = hub.spawn(self.monitor_thread)  # 注册循环协程
 
 
    def save_port_history_stats(self, port_stats_dict, key, value, set_count):
        """
        # description: 保存端口历史stats数据，并保持最多存在count个历史数据
        # param {*} self-可传入类本身属性
        # param {*} port_stats_dict-保存所有端口state的字典
        # param {*} key-当前需要保存的端口的key信息
        # param {*} value-当前需要保存的端口的value(stats)信息
        # param {*} count-最多保存count个历史数据
        # return {*} None
        """
        if key not in port_stats_dict.keys(): # 检测到该端口第一次被检测，加入到总字典中
            port_stats_dict[key] = []
            port_stats_dict[key].append(value)
        else:
            port_stats_dict[key].append(value) # 已有该端口记号，直接保存数据

        now_count = len(port_stats_dict[key]) # 当前该端口已保存的历史stats数据计数
        if now_count > set_count:
            port_stats_dict[key].pop(0) # 超过set_count个数据，则删除最旧的数据
    
 
    def statistical_time_difference(self, pre_duration_sec, pre_duration_nsec, now_duration_sec, now_duration_nsec):
        """
        # description: 计算两个历史统计消息的时间节点的差，即两个历史统计消息总持续时间
        # duration_sec和duration_nsec其实是把一个时间点拆分为整数部分和小数部分
        # param {*} self-可传入类本身属性
        # param {*} pre_duration_sec-前一个数据统计的时间点整数部分
        # param {*} pre_duration_nsec-前一个数据统计的时间点小数部分(ns)
        # param {*} now_duration_sec-后一个数据统计的时间点整数部分
        # param {*} now_duration_nsec-后一个数据统计的时间点小数部分(ns)
        # return {*} 两个统计消息的时间节点的时间差(单位:秒)
        """
        pre_duration = pre_duration_sec + (pre_duration_nsec / 10 ** 9) # 1s = 10^9 ns
        now_duration = now_duration_sec + (now_duration_nsec / 10 ** 9)
        time_difference = abs(pre_duration - now_duration) # 相减计算绝对值
        return time_difference


    def calculate_port_remain_bandwidth(self, dpid, port_no, used_bandwidth):
        """
        # description: xxx
        # param {*} self-可传入类本身属性
        # param {*} dpid-交换机的dpid
        # param {*} port_no-该dpid下的某个需要计算的端口号
        # param {*} flow_speed-该端口计算出的流量速度(bit/s)
        # return {*} None
        """
        now_port_feature = self.all_port_features.get(dpid).get(port_no)
        now_port_max_bandwidth = now_port_feature[3] # 取出该端口的最大带宽
        remain_bandwidt = max(0, now_port_max_bandwidth / 1000 - used_bandwidth / 1000) # 结果用Mbit/s
        self.all_port_remain_bandwidth.setdefault(dpid, {}) # 保存(这个操作不会清空原始数据)
        self.all_port_remain_bandwidth[dpid][port_no] = remain_bandwidt
    

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def sw_state_change_handler(self, ev):
        """
        监听交换机状态改变事件
        """
        self.structure.sw_change_flag = True # 标记sw状态改变中，不允许其他程序遍历某些正在变化的变量
        if setting.DEBUG_MONITOR:  # debug模式才进入这个if
            datapath = ev.datapath
            if ev.state == MAIN_DISPATCHER:   # 交换机注册
                if datapath.id not in self.all_sw_datapaths:
                    self.all_sw_datapaths[datapath.id] = datapath
                    self.all_port_features.setdefault(datapath.id, {}) # 初始化一些属性
                    self.logger.info("<monitor.py>        交换机 %016x 上线了", datapath.id)
            elif ev.state == DEAD_DISPATCHER: # 交换反机注册
                if datapath.id in self.all_sw_datapaths:
                    del self.all_sw_datapaths[datapath.id]
                    self.logger.info("<monitor.py>        交换机 %016x 下线了", datapath.id)
        else:
            # 如果不是调试模式，则配合总协程顺序运行
            self.all_sw_datapaths = self.structure.all_sw_datapaths
            for each_sw_dpid in self.all_sw_datapaths.keys():
                self.all_port_features.setdefault(each_sw_dpid, {}) # 初始化端口的features字典
        self.structure.sw_change_flag = False
    

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_change_handler(self, ev):
        """
        该处理函数只用作端口改变时显示信息
        """
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto

        if msg.reason == ofp.OFPPR_ADD:
            reason = '增加'
        elif msg.reason == ofp.OFPPR_DELETE:
            reason = '删除'
        elif msg.reason == ofp.OFPPR_MODIFY:
            reason = '修改'
        else:
            reason = '未知'

        self.logger.info('监测到交换机 <%d> 端口变化，原因：%s', msg.datapath.id, reason)


    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_state_reply_handler(self, ev):
        """
        监听并处理交换机上报的流表信息
        """
        body = ev.msg.body  # 取出交换机回复的内容消息体
        if setting.SHOW_SW_FLOW:
            self.logger.info('~~~~~ Flow table ~~~~~') 
            self.logger.info('datapath            '
                            'priority      table_id      '
                            'in_port      out_port')
            self.logger.info('----------------    '
                            '--------      --------      '
                            '--------     ----------------------')
        for stat in body:
            dpid = ev.msg.datapath.id
            priority = stat.priority
            table_id = stat.table_id
            in_port = stat.match.get('in_port')
            out_port = ''
            # 打印
            if (in_port == None):
                in_port = 'None'
            elif (in_port == ofproto_v1_3.OFPP_LOCAL):
                in_port = 'LOCAL'
            else:
                in_port = str(in_port)
            for each_port in stat.instructions[0].actions:  # 遍历所有端口，防止搜索不到，类型为None
                if (each_port.port == ofproto_v1_3.OFPP_LOCAL):
                    out_port = out_port + 'LOCAL' + '、'
                elif (each_port.port == ofproto_v1_3.OFPP_ALL):
                    out_port = out_port + 'ALL' + '、'
                elif (each_port.port == ofproto_v1_3.OFPP_CONTROLLER):
                    out_port = out_port + 'CONTROLLER' + '、'
                elif (each_port.port == None):
                    out_port = out_port + 'None' + '、'
                else:
                    out_port = out_port + str(each_port.port) + '、'
            if setting.SHOW_SW_FLOW:
                self.logger.info("%016x       %5d         %5d    %10s     %10s", 
                                dpid, priority, table_id, in_port, out_port)
        if setting.SHOW_SW_FLOW:
            self.logger.info('\n')
        

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, ev):
        """
        监听并处理交换机上报的端口描述信息
        """
        msg = ev.msg
        body = msg.body  # 取出交换机回复的内容消息体
        dpid = msg.datapath.id
        # 打印-setting.py中修改标志位
        if setting.SHOW_SW_PORT_DESC:
            self.logger.info('~~~~~ Port desc info table ~~~~~')
            self.logger.info('datapath            '
                            'port_no       '
                            'config       state         curr_speed     max_speed')
            self.logger.info('----------------    '
                            '----------    '
                            '---------    ---------     -----------    ----------')
            
        for each_OFPPort in body:
            if each_OFPPort.port_no != ofproto_v1_3.OFPP_LOCAL:  # 0xfffffffe 4294967294 - 排除LOCAL端口
                port_no = each_OFPPort.port_no
                config_str = self.port_config_dict[each_OFPPort.config] # 判断这个端口的config状态
                state_str = self.port_state_dict[each_OFPPort.state] # 判断这个端口的state状态
                try:
                    curr_speed_value = each_OFPPort.curr_speed  # 当前端口速度，单位：kb/s
                    max_speed_value = each_OFPPort.max_speed # 最大端口速度
                except: # 有时是放在properties里的，因此要判断
                    curr_speed_value = each_OFPPort.properties[0].curr_speed  # 当前端口速度，单位：kb/s
                    max_speed_value = each_OFPPort.properties[0].max_speed # 最大端口速度

                if max_speed_value == 0:  # 无线的情况，port_desc中不会给出无线网卡的最大带宽，自行预设
                    max_speed_value = setting.WIRELESS_MAX_SPEED
                self.all_port_features[dpid][each_OFPPort.port_no] = (config_str, state_str, curr_speed_value, max_speed_value)
                # 打印-setting.py中修改标志位
                if setting.SHOW_SW_PORT_DESC: 
                    self.logger.info("%016x    %2d            %3s          %9s     %7d        %7d", 
                                    dpid, port_no, config_str, state_str, curr_speed_value, max_speed_value)
        if setting.SHOW_SW_PORT_DESC:
            self.logger.info('\n')


    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_state_reply_handler(self, ev):
        """
        监听并处理交换机上报的端口状态信息，通过该信息可测量带宽
        """
        body = ev.msg.body  # 每个回复的消息都称为一个消息体
        dpid = ev.msg.datapath.id

        if setting.SHOW_SW_PORT:
            port_no = ''
            self.logger.info('~~~~~ Port info table ~~~~~')
            self.logger.info('datapath            '
                            'port          '
                            'rx-bytes      rx-errors      '
                            'tx-bytes      tx-errors     '
                            'duration_sec  duration_nsec ')
            self.logger.info('----------------    '
                            '----------    '
                            '----------    ----------    -----------    '
                            '----------    ----------    -----------    ')
        for each_port_stat in sorted(body, key=attrgetter('port_no')):
            # 1.打印信息
            if (each_port_stat.port_no == ofproto_v1_3.OFPP_LOCAL):
                port_no = 'LOCAL'
            else:
                port_no = str(each_port_stat.port_no)
            if setting.SHOW_SW_PORT:
                self.logger.info('%016d    '
                                '%10s    '
                                '%10d    %10d     %10d    '
                                '%10d    %10d     %10d    ',
                                ev.msg.datapath.id, port_no,
                                each_port_stat.rx_bytes, each_port_stat.rx_errors,
                                each_port_stat.tx_bytes, each_port_stat.tx_errors, each_port_stat.duration_sec, each_port_stat.duration_nsec)
            
            if each_port_stat.port_no != ofproto_v1_3.OFPP_LOCAL: # 存储该交换机的所有端口状态信息，本地回环端口不处理
                key = (dpid, each_port_stat.port_no)
                value = (each_port_stat.tx_bytes, each_port_stat.rx_bytes, 
                         each_port_stat.rx_errors, each_port_stat.duration_sec, each_port_stat.duration_nsec, 
                         each_port_stat.tx_packets, each_port_stat.rx_packets,)
                self.save_port_history_stats(self.all_port_stats, key=key, value=value, set_count=setting.SAVE_PORT_STATS_COUNT)
            
            # 3.计算链路剩余带宽
            self.calculate_bw(dpid=dpid, stat=each_port_stat)

        # 2.计算链路丢包率
            self.calculate_loss(dpid=dpid, stat=each_port_stat)

        if setting.SHOW_SW_PORT:
                self.logger.info('\n')


    #=========================================== 交换机带宽测量 ===========================================#
    # <带宽>计算方法：
    # 把两个不同时间的统计消息的字节数相减，再除以两个消息差也即统计时间差则可以得到一小段时间的流量速度。
    # 剩余带宽则用端口最大带宽减去当前流量带宽，则得端口剩余带宽。
    def calculate_bw(self, dpid, stat):
        """
        # description: 计算链路剩余带宽
        # param {*} self
        # param {*} dpid
        # param {*} stat
        # return {*}
        """
        if stat.port_no != ofproto_v1_3.OFPP_LOCAL: # 本地回环端口不处理
            this_port_all_history_stats = self.all_port_stats[(dpid, stat.port_no)] # 取出该端口的所有历史stats信息

            pre_bytes = 0 # 倒数第二个历史统计消息的收发字节总数
            now_bytes = 0 # 最后一个(最新)历史统计消息的收发字节总数
            
            if len(this_port_all_history_stats) > 1: # 有2次及以上的历史信息才开始计算带宽
                # 该端口倒数第二个历史数据中：发送的字节数 + 接收的字节数
                pre_bytes = this_port_all_history_stats[-2][0] + this_port_all_history_stats[-2][1]
                now_bytes = this_port_all_history_stats[-1][0] + this_port_all_history_stats[-1][1]
                pre_duration_sec = this_port_all_history_stats[-2][3]
                pre_duration_nsec = this_port_all_history_stats[-2][4]
                now_duration_sec = this_port_all_history_stats[-1][3]
                now_duration_nsec = this_port_all_history_stats[-1][4]
                # 计算两时间点期间，收发数据的总合
                all_rece_send_byte = now_bytes - pre_bytes
                all_rece_send_kbit =  (all_rece_send_byte * 8) / 1000 # 转化为千比特(kbit)，方便后面计算(1byte=8bit)
                # 计算两次统计的时间节点的时间差
                time = self.statistical_time_difference(pre_duration_sec, pre_duration_nsec, now_duration_sec, now_duration_nsec)
                # 计算该端口流量速度，有点类似-> 速度 = 路程 / 时间，这里的路程就是总收发数据字节数，时间就是两个统计时间节点的时间差
                used_bandwidth = abs(all_rece_send_kbit / time) # kbit/s
                self.calculate_port_remain_bandwidth(dpid, stat.port_no, used_bandwidth) # 计算该端口的剩余带宽
                if setting.SHOW_ALL_PORT_REMAIN_BANDWIDTH:
                    self.logger.info("dpid %d | 端口 %d | 剩余带宽 %d Mbit/s | 剩余百分比%f%%",
                                        dpid, stat.port_no, self.all_port_remain_bandwidth[dpid][stat.port_no],
                                        float(self.all_port_remain_bandwidth[dpid][stat.port_no]) / 
                                        (self.all_port_features[dpid][stat.port_no][3] / 1000) * 100)
    #=====================================================================================================#


    #=========================================== 交换机时延测量 ===========================================#
    # <时延>测量方法示意图(2台为例)：
    # ①controller先对每个sw发送一个带"当前时间戳"的echo报文，sw收到后会回复一个响应报文
    # 该响应报文的数据内容就是发送时携带的时间戳，取出该时间后，与当前接收到响应报文的时刻相减
    # 即可得到controller与该交换机之间往返一次数据的时延，注意这里是往返，不是单向
    # 如此即可得到controller与sw1和sw1之间往返一次数据的延时时间，记为Tc1、Tc2
    #                                                             
    #                   ________________
    #                  |   controller   |
    #                    |            |
    #                    |            |
    #               Tc1 ↓|↑          ↓|↑ Tc2
    #                    |            |
    #                 ___|___      ___|___
    #                |  sw1  |    |  sw2  |
    #
    #         
    # ②LLDP报文负责发现交换机邻居，这里假设LLDP包由controller发出，
    # 首先发送给sw1，sw1接收到后，通过与sw2连接的端口转发给sw2,此时sw2接收到了这个LLDP包，无法匹配，
    # 这个时候将这个包上传至controller，此时controller接收到了该LLDP包并记录接收的时刻
    # 然后将LLDP中的发送时间戳取出，与接收时刻相减，就是controller -> sw1 -> sw2 -> 回到controller的时延，记为T_forward
    # 然后再将一个新的LLDP包从sw2发出，经过与上述内容相同的操作，得到controller -> sw2 -> sw1 -> 回到controller的时延，记为T_backward
    # 
    #                 T_forward流程：↓              T_backward流程：↓
    #                 ________________              ________________
    #                |   controller   |            |   controller   |
    #                       / \                           / \
    #                      /   \                         /   \
    #                   ↓ /     \ ↑                   ↑ /     \ ↓
    #                    /       \                     /       \
    #                   /         \                   /         \
    #               ___/___  →   __\____          ___/___  ←   __\____
    #              |  sw1  |----|  sw2  |        |  sw1  |----|  sw2  |
    #
    # 
    # ③我们最终的结果是想要得到sw1 -> sw2(或者反过来说sw2 -> sw1都一样)的时延，这就很简单了，将三者看成一个三角形,如上图
    # 知道了三角形的2倍周长(T_forward + T_backward)，以及2个斜边的2倍长度(Tc1和Tc2)，
    # 底边的2倍长度 = (T_forward + T_backward - Tc1 - Tc2)，再除以2即可得到底边的长度——即sw1 -> sw2(or sw2 -> sw1)的传输时延

    def send_echo_request(self):
        # 遍历所有交换机
        # self.logger.info("对 %s 交换机发送echo报文中...", self.structure.all_sw_datapaths.keys())
        for each_dpid in list(self.structure.all_sw_datapaths.keys()): # list可以解决字典在迭代过程中被改变导致错误的问题
            datapath = self.structure.all_sw_datapaths[each_dpid] # 取出交换机的datapath
            parser = datapath.ofproto_parser # 解释器
            request_time = time.time() # 记录发送时间
            data = bytes("%.12f" % request_time, encoding="utf8") # 构造echo数据内容
            echo_req = parser.OFPEchoRequest(datapath, data=data)  # 构造echo对象
            datapath.send_msg(echo_req) # 控制器向交换机发送echo数据
            # !!!!必须要延时一定时间，防止响应报文同时到达控制器，出现大量响应报文卡死
            hub.sleep(setting.ECHO_SEND_DELAY)
            if self.structure.sw_change_flag: # 交换机正在上线，跳出此次发送
                break
        # self.logger.info("echo报文发送完毕...")
    
    @set_ev_cls(ofp_event.EventOFPEchoReply, MAIN_DISPATCHER)
    def echo_reply_handler(self, ev):
        """
        处理交换机回复的echo报文
        """
        receive_time = time.time()       # 记录接收时间
        try:
            request_time = eval(ev.msg.data) # 取出发送时间 
            dpid = ev.msg.datapath.id  # 取出回复echo报文的交换机dpid
            sw_echo_delay = receive_time - request_time  # 计算时间差
            self.all_sw_echo_delay[dpid] = sw_echo_delay # 存储
        except Exception as error:
            self.logger.warning("<monitor.py>        读取echo报文出错，原因:%s", error)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):  # 处理到达的LLDP报文，从而获得LLDP时延
        """
        # description: 处理到达的LLDP报文，从而获得LLDP时延
        # param {*} self
        # param {*} ev
        # return {*}
        """
        receive_time = time.time()       # 记录接收时间
        data = ev.msg.data # 取出原始数据
        pkt = packet.Packet(data=ev.msg.data) # 取出数据包
        
        eth_pkt = pkt.get_protocols(ethernet.ethernet)[0]  # 解析ethernet层(数据链路层，用于判断是否为LLDP报文)

        # 该packet_in_handler函数主要处理LLDP数据包，并利用LLDP测量链路时延所需的部分参数
        # 因此非LLDP报文则退出此handler函数
        if eth_pkt.ethertype != ether_types.ETH_TYPE_LLDP:
            return
        try:
            src_dpid, src_out_port = LLDPPacket.lldp_parse(data)  # 解析发送LLDP报文的交换机dpid和发送端口
            dpid = ev.msg.datapath.id  # 取出接收该LLDP报文的交换机dpid

            # self.switch_module保存着所有交换机端口的信息
            for port in self.switches.ports.keys():  # 开始获取对应交换机端口的发送时间戳
                if src_dpid == port.dpid and src_out_port == port.port_no:  # 匹配该LLDP包的发送的交换机与发送端口
                    # 获取满足key条件的values值PortData实例，内部保存了发送LLDP报文时的timestamp信息，即LLDP包在发送时被打上的时间戳
                    send_timestamp = self.switches.ports[port].timestamp # 取出LLDP发送时间戳
                    if send_timestamp:
                        lldp_delay = receive_time - send_timestamp # 计算时间差
                    else:
                        lldp_delay = 0

                    self.all_sw_lldp_delay.setdefault(src_dpid, {}) # 构造字典，尽量存储多的lldp时延数据
                    self.all_sw_lldp_delay[src_dpid][dpid] = lldp_delay  # 将时延信息存起来
        except LLDPPacket.LLDPUnknownFormat as error:
            print("<monitor.py>        解析LLDP延时出错，原因:%s", error)
            return
    

    def calculate_delay(self, sw1_dpid, sw2_dpid):
        """
        # description: 计算最终2个相邻交换机的时延
        # param {*} self-传入类本身属性
        # param {*} sw1_dpid-其中一个交换机
        # param {*} sw2_dpid-另一个交换机
        # return {*} None
        """
        if (sw1_dpid not in self.all_sw_echo_delay) or (sw2_dpid not in self.all_sw_echo_delay):
            return
        Tc1 = self.all_sw_echo_delay[sw1_dpid]
        Tc2 = self.all_sw_echo_delay[sw2_dpid]
        T_forward = self.all_sw_lldp_delay[sw1_dpid][sw2_dpid]
        T_backward = self.all_sw_lldp_delay[sw2_dpid][sw1_dpid]

        delay = (T_forward + T_backward - Tc1 - Tc2) / 2 # 计算
        self.all_sw_to_sw_delay.setdefault(sw1_dpid, {}) # 存储
        self.all_sw_to_sw_delay.setdefault(sw2_dpid, {})
        self.all_sw_to_sw_delay[sw1_dpid][sw2_dpid] = delay
        self.all_sw_to_sw_delay[sw2_dpid][sw1_dpid] = delay
        return delay
    #=====================================================================================================#
    

    #=========================================== 交换机丢包率测量 ===========================================#
    # <丢包率>测计算方法示意图(2台为例)：
    # sw1与sw2仅有一根线相连，记连接的端口为port1和port2，那么以sw1为第一视角，假设丢包率为0，则有：
    # port1所有发送的数据(TX1)应当被port2全部接收(RX2)，即TX1 = RX2，同理反过来TX2 = RX1
    # 那么丢包率不为0时，则有 取出相应的数据，即可。注意丢包率要用tx_packet、rx_packet数据，不要用字节
    # 
    #
    #                   ____TX1             TX2____
    #         _________|                           |_________
    #        |   sw1   |port1-----------------port2|   sw2   |
    #        |_________|                           |_________|         
    #                  |____RX1             RX2____|
    #
    # {(src_sw_dpid, dst_sw_dpid):(src_sw_port_no, dst_sw_port_no)}
    def calculate_loss(self, dpid, stat):
        # 更新最新的links信息到loss表中(setdefault方法不会覆盖原有的value数据)
        for (src_dpid, dst_dpid) in list(self.structure.all_sw_links.keys()):
            self.all_links_loss.setdefault((src_dpid, dst_dpid), ())

        # 遍历链路信息，计算loss
        for src_dpid, dst_dpid in list(self.structure.all_sw_links.keys()):
            src_port = self.structure.all_sw_links[(src_dpid, dst_dpid)][0] # 取出src_port
            dst_port = self.structure.all_sw_links[(src_dpid, dst_dpid)][1] # 取出dst_port
            # 判断该交换机以及端口是否有历史测量数据
            if ((src_dpid, src_port) not in self.all_port_stats) or ((dst_dpid, dst_port) not in self.all_port_stats):
                return
            # 取出这两个端口的历史统计信息
            src_port_stats = self.all_port_stats[(src_dpid, src_port)]
            dst_port_stats = self.all_port_stats[(dst_dpid, dst_port)]
            if len(src_port_stats) > 1 and len(dst_port_stats) > 1: # 必须两个端口的历史统计消息都要在2个以上才能计算loss
                src_tx = src_port_stats[-1][5] - src_port_stats[-2][5] # 两个历史统计消息的差值就是这段时间内的变化
                src_rx = src_port_stats[-1][6] - src_port_stats[-2][6]
                dst_tx = dst_port_stats[-1][5] - dst_port_stats[-2][5]
                dst_rx = dst_port_stats[-1][6] - dst_port_stats[-2][6]
                # loss (输入(TX) - 输出(RX)) / 输入(TX)
                loss_forward = ((src_tx - dst_rx) / src_tx) if ((src_tx - dst_rx) / src_tx) > 0 else 0.0  # 正向loss
                loss_backward = ((dst_tx - src_rx) / dst_tx) if ((dst_tx - src_rx) / dst_tx) > 0 else 0.0 # 反向loss
                self.all_links_loss[(src_dpid, dst_dpid)] = round(loss_forward, 3) # 保留3位小数
                self.all_links_loss[(dst_dpid, src_dpid)] = round(loss_backward, 3)
    #=======================================================================================================#


             
    def request_all_sw_state(self):
        """
        description: 主动发送请求，获取交换机的端口及流表信息
        param {*} self-传入类本身属性
        return {*} None
        """
        all_sw_dpid = []
        for each_sw_dpid in self.all_sw_datapaths:
            if self.structure.sw_change_flag: # 当触发交换机更改事件时，此时不应再继续遍历，否则会报dict错误
                return
            all_sw_dpid.append(each_sw_dpid) # 这里使用主要是为了最后打印
            each_sw_datapath = self.all_sw_datapaths[each_sw_dpid] # 取出该交换机的datapath
            ofproto = each_sw_datapath.ofproto       # OpenFlow版本信息
            parser = each_sw_datapath.ofproto_parser # 解析器

            # 发送交换机端口状态请求
            req = parser.OFPPortStatsRequest(each_sw_datapath, 0, ofproto.OFPP_ANY)
            each_sw_datapath.send_msg(req)

            # 发送交换机流表信息请求
            req = parser.OFPFlowStatsRequest(each_sw_datapath, 0)
            each_sw_datapath.send_msg(req)

            # 发送交换机端描述述请求
            req = parser.OFPPortDescStatsRequest(each_sw_datapath, 0)
            each_sw_datapath.send_msg(req)

        self.send_echo_request()  # 发送echo报文，获得控制器与交换机之间时延

        all_sw_dpid.sort() # 排序
        if all_sw_dpid: # 列表中有元素时才打印
            dpid_group = '[ '
            for each_dpid in all_sw_dpid: # 处理数据，将dpid以16进制显示，
                dpid_group += '{:01X} '.format(each_dpid)
            dpid_group += ']'
            self.logger.info("<monitor.py>        已对交换机 %s 发送统计请求并计算<带宽、时延、丢包率>", dpid_group)

    # 单文件调试的协程
    def monitor_thread(self):
        """
        debug_monitor时的单独协程
        """
        while True:
            self.logger.info("DEBUG-network_monitor.py 模式")
            self.request_all_sw_state() # 发送统计请求
            self.send_echo_request()    # 发送echo，测量延时
            hub.sleep(5) # 延迟让出权限