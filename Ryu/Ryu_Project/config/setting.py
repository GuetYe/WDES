# '''
# Author: louis
# Date: 2023-05-02 10:45:41
# Connection: louis.yyj.dev@foxmail.com
# FilePath: \N5105_share\setting.py
# Description: 配置参liu
# '''

MAIN_SCHEDULE_PERIOD = 3  # 总协程中的延时时间

WIRELESS_MAX_SPEED = 800000 # 单位kbps/s，无线传输的最大带宽(因为port desc不会展示无线网卡的speed)

HOST_FILE_PATH = r'../host_file/host_info.txt'

DEFAULT_HOST_USERNAME = 'louis'

DEFAULT_HOST_PASSWORD = '\''

DEFAULT_HOST_PORT = '445'

CONTROLLER_IP = '10.0.0.1'

CONTROLLER_MAC = '0a:0b:0c:0d:0e:0f'
# arp_handler.py--------------------------------------------------------------
DEBUG_ARP_HANDLER = False     # 单独调试network_structure.py(为False时，network_structure会在总协程中调用)

# arp_handler.py--------------------------------------------------------------


# network_structure.py--------------------------------------------------------------
DEBUG_STRUCTURE = False     # 单独调试network_structure.py(为False时，network_structure会在总协程中调用)

# network_structure.py--------------------------------------------------------------


# network_monitor.py--------------------------------------------------------------
DEBUG_MONITOR = False       # 单独调试network_monitor(为False时，network_monitor会在总协程中调用)

SHOW_SW_PORT = False         # 是否显示monitor模块中，请求交换机回复端口信息
 
SHOW_SW_FLOW = False        # 是否显示monitor模块中，请求交换机回复流表描述信息

SHOW_SW_PORT_DESC = False   # 是否显示monitor模块中，请求交换机回复端口状态信息

SAVE_PORT_STATS_COUNT = 2   # 保存端口多少次的历史stats数据(主要涉及端口流量)

SHOW_ALL_PORT_REMAIN_BANDWIDTH = False # 显示所有端口的剩余带宽

ECHO_SEND_DELAY = 0.2       # 测量链路时延时，发送echo报文的间隔时间
# network_monitor.py--------------------------------------------------------------


# host_state.py-----------------------------------------------------------
SHOW_HOST_MEMORY_UTILIZATION = True  # 显示每个主机获取到的内存使用率
# host_state.py-----------------------------------------------------------


# network_shortest_path.py----------------------------------------------
DEBUG_SHORTEST_PATH = False       # 单独调试shortest_path.py(为False时，network_shortest_path.py会在总协程中调用)

SHOW_WEIGHT_PARAM = False    # 显示权重参数

FLOW_EFFECTIVE_DURATION = 10 # 流表下发后，存在的有效时间

FLOW_PRIORITY = 300  # 下发的流表的优先级
# network_shortest_path.py----------------------------------------------

# host_multi_attr_decision_make.py----------------------------------------------
REMAIN_CAPACITY_LIMITATION = 0.05  # 存储节点的剩余容量的极限，超过该值则不会被选择为存储节点

LOAD_FACTOR = 0.4

CPU_UTI_FACTOR = 0.3

MEM_UTI_FACTOR = 0.2

CAPACITY_FACTOR = 0.1
# host_multi_attr_decision_make.py----------------------------------------------