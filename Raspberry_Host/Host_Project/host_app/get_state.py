# '''
# Author: louis
# Date: 2023-05-11 10:13:21
# Connection: louis.yyj.dev@foxmail.com
# FilePath: \N5105_share\utils\host_utils.py
# Description: 主机工具，获取CPU使用率，磁盘容量，等等...
#     请在系统中安装sysstat工具：sudo apt install sysstat
# '''
import sys
sys.path.append('../') # 添加工作目录，使得VSCode能够导入其他目录的python文件
import re
import subprocess
import config.setting as setting

class Host_Utils(object):
    """
    获取主机的磁盘IO、CPU使用率、内存使用率、磁盘剩余容量状态
    """
    def __init__(self):
        # 正则表达式寻找关键字符
        if setting.RASPBERRY:
            self.get_host_io_load_method = re.compile(r'sda(.)+sda(\s+\d+.\d+){21}\s+(?P<Load>\d+.\d+?)\n', re.S)
        elif setting.TINKERBOARD:
            self.get_host_io_load_method = re.compile(r'sda(.)+sda(\s+\d+.\d+){14}\s+(?P<Load>\d+.\d+?)\n', re.S)
        self.get_host_total_memory_method = re.compile(r'MemTotal:\s+(?P<MemTotal>\d*?)\s')
        self.get_host_free_memory_method = re.compile(r'MemFree:\s+(?P<MemFree>\d*?)\s')
        self.get_host_cpu_free_util_method = re.compile(r'%Cpu(.+)ni,\s(?P<CpuFreeUtil>.*?)(\s)id,')
        self.get_host_Disk_remain_capa_method = re.compile(r'\/dev\/sda.+\s(\d+\s+){3}(?P<RemainCapacity>\d+?)\%')


    @staticmethod
    def get_host_IP():
        """
        # description: 获取主机的IP
        # param {*} self-传入类本身属性
        # return {*} 主机IP
        """
        original_data = subprocess.check_output("hostname -I", shell=True).decode('utf-8')
        host_ip = re.search('\d+.\d+.\d+.\d+', original_data).group(0)

        return host_ip


    def get_host_IO_load(self):
        """
        # description: 获取主机的磁盘IO负载情况，注意，默认读取磁盘号为sda的磁盘
        # param {*} self-传入类本身属性
        # return {*} 主机磁盘IO负载率(浮点型，保留2位小数)
        """
        # 调用subprocess模块，将命令放到shell终端中执行，返回结果即是终端的执行结果
        original_data = subprocess.check_output("iostat -x 1 -t 3", shell=True).decode('utf-8')
        # # 1991意思是从第1991个位置开始搜索，因为命令设置了读取三次信息，会有三次测量的消息返回
        # # 必须测量1次以上，通过iostat才能计算出IO的实时负载情况
        IO_load = round(float(self.get_host_io_load_method.search(original_data).group('Load')), 2)

        return IO_load
    

    def get_host_cpu_utilization(self):
        """
        # description: 获取主机的cpu使用率
        # param {*} self-传入类本身属性
        # return {*} 主机cpu使用率(浮点型，保留2位小数)
        """
        original_data = subprocess.check_output("top -bn 1 -i -c", shell=True).decode('utf-8')
        Cpu_Free_Util = self.get_host_cpu_free_util_method.search(original_data).group('CpuFreeUtil') # 获得CPU空闲百分比
        Cpu_Uti = round(1.0 - (float(Cpu_Free_Util) * 0.01), 2)

        return Cpu_Uti


    def get_host_memory_utilization(self):
        """
        description: 获取主机的内存使用率
        param {*} self-传入类本身属性
        return {*} 主机内存使用率(浮点型，保留2位小数)
        """
        original_data = subprocess.check_output("cat /proc/meminfo", shell=True).decode('utf-8')
        MemTota = self.get_host_total_memory_method.search(original_data).group('MemTotal')
        MemFree = self.get_host_free_memory_method.search(original_data).group('MemFree')
        Mem_uti = round((float(MemTota) - float(MemFree)) / float(MemTota), 2) # 使用率 = (总大小 - 空闲) / 总大小

        return Mem_uti
    

    def get_host_Disk_remaining_capacity(self):
        """
        description: 获取远程主机的剩余磁盘容量(共享的NAS盘)
        param {*} self-传入类本身属性
        return {*} 主机剩余磁盘容量(浮点型)
        """
        original_data = subprocess.check_output("df -lm", shell=True).decode('utf-8')
        Remain_Capacity = 1.0 - (float(self.get_host_Disk_remain_capa_method.search(original_data).group('RemainCapacity')) * 0.01)
        
        return Remain_Capacity
    
    
if __name__ == '__main__':
    host = Host_Utils()
    print("IO---", host.get_host_IO_load())
    print("CPU---", host.get_host_cpu_utilization()) 
    print("MEM---", host.get_host_memory_utilization()) 
    print("Disk---", host.get_host_Disk_remaining_capacity()) 