
import sys
sys.path.append('../') # 添加工作目录，使得VSCode能够导入其他目录的python文件

from host_app.get_state import Host_Utils
from host_app.report_state import PacketSelfState
import time


if __name__ == "__main__":
    host_utils = Host_Utils()
    host_ip = host_utils.get_host_IP() # 获取主机IP
    report = PacketSelfState(host_ip=host_ip) # 实例化上报
    print("my host ip is:", host_ip)
    while True:
        IO_load = host_utils.get_host_IO_load()
        Cpu_Uti = host_utils.get_host_cpu_utilization()
        Mem_uti = host_utils.get_host_memory_utilization()
        Remain_Capacity = host_utils.get_host_Disk_remaining_capacity()
        report.report_state(IO_load=IO_load, Cpu_Uti=Cpu_Uti, Mem_uti=Mem_uti, Remain_Capacity=Remain_Capacity)
        time.sleep(1) # 一秒上传一次
