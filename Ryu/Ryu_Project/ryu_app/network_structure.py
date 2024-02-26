# '''
# Author: louis
# Date: 2023-04-29 10:33:17
# Connection: louis.yyj.dev@foxmail.com
# FilePath: \N5105_share\structure.py
# Description: 
# '''
import sys
sys.path.append('../') # 添加工作目录，使得VSCode能够导入其他目录的python文件

from ryu.base import app_manager      # 继承基本的Ryu App类
from ryu.base.app_manager import lookup_service_brick
from ryu.ofproto import ofproto_v1_3  # 导入OpenFlow1.3版本
from ryu.topology import event        # topology.event与controller.ofp_event有什么不同?
from ryu.controller.handler import set_ev_cls, CONFIG_DISPATCHER
from ryu.topology.api import get_switch, get_link
from ryu.controller import ofp_event
from ryu.lib import hub
import networkx as nx
import config.setting as setting

class NetworkStructure(app_manager.RyuApp):
    """
    发现并保存网络拓扑
    """
    OPF_VERSION = [ofproto_v1_3.OFP_VERSION]  # 设置OpenFlow版本
    event = [event.EventSwitchEnter, event.EventSwitchLeave, event.EventSwitchReconnected,
                      event.EventPortAdd, event.EventPortDelete, event.EventPortModify,
                      event.EventLinkAdd, event.EventLinkDelete] # 构造事件列表，用于监听
    
    def __init__(self, *_args, **_kwargs):
        super(NetworkStructure, self).__init__(*_args, **_kwargs)
        self.name = "structure"
        self.monitor = None # 初始运行这里是找不到monitor的，因为structure最先运行，所以放在函数里查找
        self.get_topo_app = self # 传入获取交换机的形参get_switch()
        self.all_sw_datapaths = {} # 保存所有交换机的datapath信息 {dpid_1:datapath_1, ...}
        self.all_sw_ports = {}  # 保存每个交换机对应的所有端口 {dpid:set(port1、port2...)}
        self.all_sw_links = {}  # 保存每个交换机之间对应的连接端口信息 {(src_sw_dpid, dst_sw_dpid):(src_sw_port_no, dst_sw_port_no)}
        self.used_sw_ports = {} # 保存每个交换机对应的已使用的端口，已使用的端口代表接入的是交换机或者控制器
        self.not_use_sw_ports = {} # 保存每个交换机对应的未使用的端口，未使用的端口代表主机会接到这些端口中
        self.all_switchs_dpid_list = [] # 保存所有交换机的dpid
        self.network_topology = nx.Graph() # 构建一个无向图，保存拓扑结构
        self.first_establish = True # 首次建图中(此时还未能完全测量完带宽、时延、丢包率)
        self.sw_change_flag = False # 标记交换机正在改变中，不允许其他一些字典、列表等继续迭代，否则报错
        if setting.DEBUG_STRUCTURE:
            self.structure_thread = hub.spawn(self.structure_thread)  # 注册循环协程，单独调试时使用


    def add_flow(self, datapath, priority, match, actions):
        """
        # description: 流表下发函数
        # param {*} self-可传入类本身属性
        # param {*} datapath-交换机的datapath
        # param {*} priority-流表优先级
        # param {*} match-流表匹配域
        # param {*} actions-流表指令域
        # return {*} 无
        """
        inst = [datapath.ofproto_parser.OFPInstructionActions(
             datapath.ofproto.OFPIT_APPLY_ACTIONS, actions)] # OFPIT_APPLY_ACTIONS表立即应用该actions
        mod = datapath.ofproto_parser.OFPFlowMod(datapath=datapath, 
                                                 priority=priority,
                                                 match=match,
                                                 instructions=inst)
        datapath.send_msg(mod)


    def establish_complete_network_topology(self, bw=0.0, delay=0.0, loss=0.0, load=0.0, cpu_uti=0.0, memory_uti=0.0, remain_capacity=0.0):
        """
        # description: 使用networkx包构建完整的交换机网络拓扑图，并为边增加相应属性。网络拓扑不含主机、控制器
        # param {*} self-可传入类本身属性
        # param {*} bw-带宽
        # param {*} delay-时延
        # param {*} loss-丢包率
        # param {*} load-IO负载
        # param {*} cpu_uti-CPU利用率
        # param {*} memory_uti-内存利用率
        # return {*}
        """

        if self.monitor == None: # monitor app未找到时代表是初次运行，先跳过此次拓扑建立
            self.monitor = lookup_service_brick("monitor") # 从第二次开始即可找到，找到后可使用最新测量的网络状态数据
            return
        # 遍历所有链路的和节点
        for src_dpid, dst_dpid in list(self.all_sw_links.keys()):

            # 1.先将节点添加到图中(新增 or 覆盖)
            self.network_topology.add_node(src_dpid)
            self.network_topology.add_node(dst_dpid)

            # 2.尝试获取最新测量的带宽数据
            if (src_dpid in self.monitor.all_port_remain_bandwidth) and (dst_dpid in self.monitor.all_port_remain_bandwidth):
                src_port_bw = self.monitor.all_port_remain_bandwidth[src_dpid][self.all_sw_links[src_dpid, dst_dpid][0]] # 链路左端口bw
                dst_port_bw = self.monitor.all_port_remain_bandwidth[dst_dpid][self.all_sw_links[src_dpid, dst_dpid][1]] # 链路右端口bw
                bw = min(src_port_bw, dst_port_bw) # 带宽以最小值为准
                self.first_establish = False
            else:
                self.first_establish = True

            # 2.尝试获取最新测量的时延数据
            if (src_dpid in self.monitor.all_sw_to_sw_delay) and (dst_dpid in self.monitor.all_sw_to_sw_delay):
                src_to_dst_delay = self.monitor.all_sw_to_sw_delay[src_dpid][dst_dpid]
                dst_to_src_delay = self.monitor.all_sw_to_sw_delay[dst_dpid][src_dpid]
                delay = max(src_to_dst_delay, dst_to_src_delay) # 时延以最大值为准
                self.first_establish = False
            else:
                self.first_establish = True

            # 3.尝试获取最新测量的丢包率数据
            if ((src_dpid, dst_dpid) in self.monitor.all_links_loss) and \
               ((dst_dpid, src_dpid) in self.monitor.all_links_loss):
                src_to_dst_loss = self.monitor.all_links_loss[(src_dpid, dst_dpid)]
                dst_to_src_loss = self.monitor.all_links_loss[(dst_dpid, src_dpid)]
                loss = max(src_to_dst_loss, dst_to_src_loss) # 丢包率以最大值为准
                self.first_establish = False
            else:
                self.first_establish = True

            self.network_topology.add_edge(src_dpid, dst_dpid, bw=bw, delay=delay, loss=loss, 
                                           load=load, cpu_uti=cpu_uti, memory_uti=memory_uti, remain_capacity=remain_capacity)


    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def sw_features_handler(self, ev):
        """
        # description: 
        #     监听SwitchFeatures事件——发送功能请求阶段
        #     用于下发交换机缺省流表，消息寻不到流表时不丢弃，而是上报控制器
        # param {*} self-可传入类本身属性
        # param {*} ev-SwitchFeatures事件携带的消息体
        # return {*} None
        """
        self.sw_change_flag = True # 标记sw状态改变中，不允许其他程序遍历某些正在变化的变量
        # 1.获取EventOFPSwitchFeatures事件中传入的ev消息体主要内容
        # 这里与EventOFPStateChange获取datapath的方式不一样，但本质都是获取了datapath
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        self.all_sw_datapaths.setdefault(datapath.id, datapath)
        self.all_switchs_dpid_list.append(datapath.id)

        self.logger.info("<structure.py>      交换机 %016x <连接>", datapath.id) # 打印消息

        # 2.设定缺省流表的相关配置，并下发流表
        match = parser.OFPMatch() # 设定流表的匹配域：任何域
        # 设定流表的指令域：上报至控制器、且不进行数据缓冲，整个数据包将发送到控制器
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]

        # 3.下发流表
        self.add_flow(datapath, priority=0, match=match, actions=actions)
        self.logger.info("<structure.py>      交换机 %016x <下发缺省流表>", datapath.id) # 打印消息
        self.sw_change_flag = False # 标记sw状态改变中，不允许其他程序遍历某些正在变化的变量
 
    @set_ev_cls(event) # 监听事件列表里的事件
    def get_topology(self, ev, active=0):
        """
        # description: 拓扑获取
        # param {*} active-触发方式，0为被动触发，1为主动触发
        # return {*} None
        """
        if not self.all_switchs_dpid_list: # 还未有交换机时，无需更新拓扑
            self.logger.info("<structure.py>      未检测到交换机加入，等待中...")
            return
        
        all_switchs = get_switch(self.get_topo_app, None) # 获得所有交换机
        all_links = get_link(self.get_topo_app, None) # 获得所有交换机的链路信息

        # 1.保存每个交换机的端口(port)信息
        for each_sw in all_switchs:
            each_dpid = each_sw.dp.id # 取出每个交换机的dpid
            # self.all_switchs_dpid_list.append(each_dpid) # 保存一份总dpid列表
            self.all_sw_ports.setdefault(each_dpid, set()) # key=dpid, value=端口的集合，set()是集合，防止端口重复
            self.used_sw_ports.setdefault(each_dpid, set()) # 先建立已使用端口的字典，后续统计links信息后才作划分
            self.not_use_sw_ports.setdefault(each_dpid, set()) # 先建立未使用端口的字典，后续统计links信息后才作划分
            # 取出该交换机的每个端口进行对应保存
            for each_ports in each_sw.ports:
                self.all_sw_ports[each_dpid].add(each_ports.port_no)

        # 2.保存交换机之间的链路(link)信息
        for each_link in all_links:
            src = each_link.src # 取出源链路信息
            dst = each_link.dst # 取出目标链路信息
            # 字典形式将源和目标的dpid与port_no一一对应存储，这里保存的port_no肯定就是已被使用了的端口
            self.all_sw_links.setdefault((src.dpid, dst.dpid), (src.port_no, dst.port_no))

            # 统计已使用的端口
            if src.dpid in self.all_switchs_dpid_list: # 判断当前交换机是否已在总交换机列表里，是则加入端口到已使用字典
                self.used_sw_ports[src.dpid].add(src.port_no)
            if dst.dpid in self.all_switchs_dpid_list: # 判断当前交换机是否已在总交换机列表里，是则加入端口到已使用字典
                self.used_sw_ports[dst.dpid].add(dst.port_no)

        # 3.统计未使用的端口(未使用的端口代表着这些端口可能连接着主机)
        for dpid, all_ports, used_port in zip(self.all_sw_ports.keys(), self.all_sw_ports.values(), self.used_sw_ports.values()):
            not_use_port = all_ports - used_port # 用集合计算该交换机下未使用的端口
            self.not_use_sw_ports[dpid] = not_use_port

        for each_value in self.used_sw_ports.values():
            if(not each_value):
                return # 如果有一个交换机对应的已使用端口为空，则代表端口统计还未完成(注意是在交换机串联模式下，多线模式下可能会存在单个交换机独立情况)

        # 4.建立新的网络拓扑结构图(带宽、时延、丢包率此时还未确定)
        self.establish_complete_network_topology()

        if(active):
            self.logger.info("<structure.py>      <主动> 更新网络拓扑") # 主动方式为协程触发
        else:
            self.logger.info("<structure.py>      <被动> 更新网络拓扑") # 被动方式为监听事件触发


    # 单文件调试时使用的协程
    def structure_thread(self):
        """
        协程：循环更新网络拓扑
        """
        while True: # setting中设置是否开启structure
            self.get_topology(ev=None, active=1) # 主动刷新拓扑结构
            hub.sleep(5)  # 让出权限
