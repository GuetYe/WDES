# '''
# Author: louis
# Date: 2023-05-11 10:13:21
# Connection: louis.yyj.dev@foxmail.com
# FilePath: \N5105_share\utils\host_utils.py
# Description: 主机工具，获取CPU使用率，磁盘容量，等等...
# '''


import paramiko
import re
import os

class Host_Utils(object):
    """
    主机工具，获取主机的一些状态
    """
    def __init__(self, host_file_path):
        self.host_file_path = host_file_path
        self.all_host = {}
        self.get_host_id_method = re.compile(r'\'id\':(?P<id>.*?)(.\s)')
        self.get_host_ip_method = re.compile(r'\'ip\':(?P<ip>.*?)(.\s)')
        self.get_host_port_method = re.compile(r'\'port\':(?P<port>.*?)(.\s)') 
        self.get_host_username_method = re.compile(r'\'username\':(?P<username>.*?)(.\s)')
        self.get_host_password_method = re.compile(r'\'password\':(?P<password>.*?)}')
        self.get_host_total_memory_method = re.compile(r'MemTotal:\s+(?P<MemTotal>\d*?)\s')
        self.get_host_free_memory_method = re.compile(r'MemFree:\s+(?P<MemFree>\d*?)\s')
        self.get_host_cpu_free_util_method = re.compile(r'%Cpu(.+)ni,\s(?P<CpuFreeUtil>.*?)(\s)id,')
        self.get_host_io_load_method = re.compile(r'sda\s+(\d+.\d+\s+){21}(?P<Load>\d+.\d+?)\n')
        self.get_host_Disk_remain_capa_method = re.compile(r'\/dev\/sda.+\s(\d+\s+){3}(?P<RemainCapacity>\d+?)\%')


    def show_host_file_path(self):
        """
        description: 显示主机文件路径
        param {*} self-传入类本身属性
        """
        print(self.host_file_path)
        return self.host_file_path
    

    def get_host_in_file(self):
        """
        description: 通过文件获取所有已存储的主机信息
        param {*} self-传入类本身属性
        return {*} 所有主机列表，字典形式
        """
        host_id = None
        host_ip = None
        host_port = None
        host_username = None
        host_password = None

        with open(self.host_file_path) as host_file:
            content = host_file.readlines()
            for each_host in content: # 逐行读取每个交换机信息
                host_id =  self.get_host_id_method.search(each_host).group('id')
                host_ip =  self.get_host_ip_method.search(each_host).group('ip')
                host_port =  self.get_host_port_method.search(each_host).group('port')
                host_username =  self.get_host_username_method.search(each_host).group('username')
                host_password =  self.get_host_password_method.search(each_host).group('password')
                self.all_host[host_id] = (host_ip, host_port, host_username, host_password)
            host_file.close
        return self.all_host
    

    def save_host_to_file(self, host_ip, host_port, host_username, host_password):
        """
        # description: 根据IP存储主机信息到文件中
        # param {*} self-传入类本身属性
        # param {*} host_ip-需要存储的主机IP
        # return {*} None
        """
        id = 1 # id从1开始 
        with open(self.host_file_path, 'a+') as host_file:
            host_file.seek(0) # 只有把光标移至文件起始位置，才能在a+模式下读取到内容
            content = host_file.readlines()
            for each_line in content: # 根据已有信息，计算id号
                id += 1
            host_file.write("{'id':%d, 'ip':%s, 'port':%s, 'username':%s, 'password':%s}\n" \
                                 %(id, host_ip, host_port, host_username, host_password))
            host_file.close()
            

    def file_is_empty(self):
        size = os.path.getsize(self.host_file_path)
        if size == 0:
            return True
        else:
            return False

  
    def clear_host_file(self):
        """
        # description: 清除host文件中的内容
        # param {*} self-传入类本身属性
        # return {*} None
        """
        with open(self.host_file_path, 'w') as host_file:
            host_file.truncate()
            host_file.close()

    def get_host_IO_load(self, host_ip, host_port, host_username, host_password):
        """
        description: 获取远程主机的磁盘IO负载情况，注意，默认读取磁盘号为sda的磁盘
        param {*} self-传入类本身属性
        param {*} host_ip-主机ip
        param {*} host_port-主机端口
        param {*} host_username-主机用户名
        param {*} host_password-主机密码
        return {*} 主机磁盘IO负载率(浮点型)
        """
        ssh_client = paramiko.SSHClient() # 新建一个SSH客户端对象
        ssh_client.set_missing_host_key_policy(policy=paramiko.AutoAddPolicy()) # 设置接受没有密钥的主机可以进行ssh连接
        ssh_client.connect(hostname=host_ip, port=host_port, username=host_username, password=host_password) # 连接主机
        std_in, std_out, std_error = ssh_client.exec_command('iostat -x 1 -t 3') # 远程执行获取
        std_out = std_out.read().decode()
        std_error = std_error.read().decode()
        ssh_client.close

        if std_error != "": # 如果指令命令出错，则跳过这次读取
            print("<host_utils.py>     远程执行主机命令出错，error_tips = %s", std_error)
            return
        # 1991意思是从第1991个位置开始搜索，因为我程序里设置了读取三次信息，会有三次测量的消息返回
        # 必须测量1次以上，通过iostat才能计算出IO的负载情况
        IO_load = round(float(self.get_host_io_load_method.search(std_out, pos=1991).group('Load')), 2)

        return IO_load
    

    def get_host_cpu_utilization(self, host_ip, host_port, host_username, host_password):
        """
        description: 获取远程主机的cpu使用率
        param {*} self-传入类本身属性
        param {*} host_ip-主机ip
        param {*} host_port-主机端口
        param {*} host_username-主机用户名
        param {*} host_password-主机密码
        return {*} 主机cpu使用率(浮点型)
        """
        ssh_client = paramiko.SSHClient() # 新建一个SSH客户端对象
        ssh_client.set_missing_host_key_policy(policy=paramiko.AutoAddPolicy()) # 设置接受没有密钥的主机可以进行ssh连接
        ssh_client.connect(hostname=host_ip, port=host_port, username=host_username, password=host_password) # 连接主机
        std_in, std_out, std_error = ssh_client.exec_command('top -bn 1 -i -c') # 远程执行获取
        std_out = std_out.read().decode()
        std_error = std_error.read().decode()
        ssh_client.close

        if std_error != "": # 如果指令命令出错，则跳过这次读取
            print("<host_utils.py>     远程执行主机命令出错，error_tips = %s", std_error)
            return
        Cpu_Free_Util = self.get_host_cpu_free_util_method.search(std_out).group('CpuFreeUtil') # 获得CPU空闲百分比
        cpu_uti = round(1.0 - (float(Cpu_Free_Util) * 0.01), 2)

        return cpu_uti


    def get_host_memory_utilization(self, host_ip, host_port, host_username, host_password):
        """
        description: 获取远程主机的内存使用率
        param {*} self-传入类本身属性
        param {*} host_ip-主机ip
        param {*} host_port-主机端口
        param {*} host_username-主机用户名
        param {*} host_password-主机密码
        return {*} 主机内存使用率(浮点型)
        """
        ssh_client = paramiko.SSHClient() # 新建一个SSH客户端对象
        ssh_client.set_missing_host_key_policy(policy=paramiko.AutoAddPolicy()) # 设置接受没有密钥的主机可以进行ssh连接
        ssh_client.connect(hostname=host_ip, port=host_port, username=host_username, password=host_password) # 连接主机
        std_in, std_out, std_error = ssh_client.exec_command('cat /proc/meminfo') # 远程执行获取
        std_out = std_out.read().decode()
        std_error = std_error.read().decode()
        ssh_client.close

        if std_error != "": # 如果指令命令出错，则跳过这次读取
            print("<host_utils.py>     远程执行主机命令出错，error_tips = %s", std_error)
            return
        MemTota = self.get_host_total_memory_method.search(std_out).group('MemTotal')
        MemFree = self.get_host_free_memory_method.search(std_out).group('MemFree')
        Mem_uti = round((float(MemTota) - float(MemFree)) / float(MemTota), 2) # 使用率 = (总大小 - 空闲) / 总大小

        return Mem_uti
    
    def get_host_Disk_remaining_capacity(self, host_ip, host_port, host_username, host_password):
        """
        description: 获取远程主机的剩余磁盘容量(共享的NAS盘)
        param {*} self-传入类本身属性
        param {*} host_ip-主机ip
        param {*} host_port-主机端口
        param {*} host_username-主机用户名
        param {*} host_password-主机密码
        return {*} 主机剩余磁盘容量(浮点型)
        """
        ssh_client = paramiko.SSHClient() # 新建一个SSH客户端对象
        ssh_client.set_missing_host_key_policy(policy=paramiko.AutoAddPolicy()) # 设置接受没有密钥的主机可以进行ssh连接
        ssh_client.connect(hostname=host_ip, port=host_port, username=host_username, password=host_password) # 连接主机
        std_in, std_out, std_error = ssh_client.exec_command('df -lm') # 远程执行获取
        std_out = std_out.read().decode()
        std_error = std_error.read().decode()
        ssh_client.close

        if std_error != "": # 如果指令命令出错，则跳过这次读取
            print("<host_utils.py>     远程执行主机命令出错，error_tips = %s", std_error)
            return
        remaining_capacity = float(self.get_host_Disk_remain_capa_method.search(std_out).group('RemainCapacity')) * 0.01
        print(remaining_capacity)
        
        return remaining_capacity