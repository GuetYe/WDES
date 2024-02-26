# '''
# Author: louis
# Date: 2023-06-05 11:50:46
# Connection: louis.yyj.dev@foxmail.com
# FilePath: \N5105_share\SDN_Project\ryu_app\host_calculate_.py
# Description: xxx
#    算法考虑的因素：
#    1) Remain_Capacity 作为主要的先决因素，当剩余容量占比达到95%以上时，不考虑再将文件存储到该节点
#    2) 
# '''
from ryu.base import app_manager
from ryu.base.app_manager import lookup_service_brick
import config.setting as setting
import numpy as np

class MutiAttribute_DecisionMaking(app_manager.RyuApp):
    def __init__(self, *_args, **_kwargs):
        super(MutiAttribute_DecisionMaking, self).__init__(*_args, **_kwargs)
        self.name = 'MADM'
        self.host_ip = None
        self.file_name = None
        self.file_size = None
        self.host_get_msg = lookup_service_brick("host_get_msg")
        self.calculate_path = lookup_service_brick("calculate_path") 

    def calculate(self, host_ip, file_name, file_size):
        self.host_ip = host_ip
        self.file_name = file_name
        self.file_size = int(file_size)
        
        if (self.host_get_msg is None) or (self.calculate_path is None):
            self.host_get_msg = lookup_service_brick("host_get_msg")
            self.calculate_path = lookup_service_brick("calculate_path") 

        if not self.host_get_msg.all_host_stats:
            print("<host_MADM.py>      主机状态为空，请等待主机上报状态后再次请求！")
            return 
        
        # 构造除请求存储文件的主机以外的存储主机节点IP列表
        host_nodes_list = []
        for each_values in self.calculate_path.host_access_table.values():
            each_host_ip = each_values[0]
            host_nodes_list.append(each_host_ip)
        host_nodes_list.pop(host_nodes_list.index(host_ip)) # 移除发起请求的主机IP
        # 检查是否有状态信息
        for each_host_ip in host_nodes_list:
            if each_host_ip not in self.host_get_msg.all_host_stats:
                print("<host_MADM.py>      主机 %s 没有状态上报，请检查"  %each_host_ip)
                return 

        # 检查存储节点的剩余容量是否超过阈值，如果超过则剔除
        for num in range(len(host_nodes_list)):
            hsot_ip = host_nodes_list[num] # 取每个IP
            host_stats = self.host_get_msg.all_host_stats[hsot_ip] # 取每个主机节点的状态列表
            host_remain_capacity = host_stats[3] # 取剩余容量
            if host_remain_capacity < setting.REMAIN_CAPACITY_LIMITATION: # 如果小于阈值
                del host_nodes_list[num]  # 剔除该节点，不作为存储节点
        print("<host_MADM.py>      参与存储的主机为:%s" %host_nodes_list)

        # 如果只有1个节点参与存储，那么无需进行多属性决策计算，直接返回结果，由该主机存储所有的文件
        if len(host_nodes_list) == 1:
            split_result = {}
            split_result[host_nodes_list[0]] = self.file_size
            return split_result

        # 构造决策矩阵
        decision_matrix = []
        for each_host in host_nodes_list:
            host_stats = self.host_get_msg.all_host_stats[each_host]
            decision_matrix.append(host_stats) # 存入每个主机的状态
        decision_matrix = np.array(decision_matrix) # 转化成numpy的矩阵形式
        
        # 归一化决策矩阵(范数)
        load_norma = 0.0
        cpu_uti_norma = 0.0
        mem_uti_norma = 0.0
        remain_capa_norma = 0.0
        # 平方求和
        for each_host_stats in decision_matrix:
            load_norma += ((-each_host_stats[0]) ** 2)     # 负载越小越好
            cpu_uti_norma += ((-each_host_stats[1]) ** 2)  # CPU使用率越小越好
            mem_uti_norma += ((-each_host_stats[2]) ** 2)     # MEM使用率越小越好
            remain_capa_norma += (each_host_stats[3] ** 2) # 剩余容量越大越好
        # 开根号
        load_norma = pow(load_norma, 0.5)
        cpu_uti_norma = pow(cpu_uti_norma, 0.5)
        mem_uti_norma = pow(mem_uti_norma, 0.5)
        remain_capa_norma = pow(remain_capa_norma, 0.5)
        # 完成构造权重因子决策矩阵 以及 加权决策矩阵
        
        load_list = []
        cpu_uti_list = []
        mem_uti_list = []
        remain_capa_list = []
        for step, each_host_stats in enumerate(decision_matrix):
            if load_norma != 0.0: # 分母不能为0，否则为无穷大
                load_ = ((-each_host_stats[0]) / load_norma) * setting.LOAD_FACTOR
            else:
                load_ = 0.0

            if cpu_uti_norma != 0.0:
                cpu_uti_ = ((-each_host_stats[1]) / cpu_uti_norma) * setting.CPU_UTI_FACTOR
            else:
                cpu_uti_ = 0.0

            if mem_uti_norma != 0.0:
                mem_uti_ = ((-each_host_stats[2]) / mem_uti_norma) * setting.MEM_UTI_FACTOR
            else:
                mem_uti_ = 0.0
            
            if remain_capa_norma != 0.0:
                remain_capa_ = (each_host_stats[3] / remain_capa_norma) * setting.CAPACITY_FACTOR
            else:
                remain_capa_ = 0.0
            decision_matrix[step] = [load_, cpu_uti_, mem_uti_, remain_capa_] # 保存新的归一化数据
            # 构造过程中顺便保存，便于计算每个因素的正负理想解
            load_list.append(load_)
            cpu_uti_list.append(cpu_uti_)
            mem_uti_list.append(mem_uti_)
            remain_capa_list.append(remain_capa_)
        
        # 计算4个因子的正负理想解，记录值和索引
        Z_load_best = max(load_list)        # IO负载，越靠近0越大，负载越小越好
        Z_load_worst = min(load_list)
        
        Z_cpu_uti_best = max(cpu_uti_list)  # CPU使用率，越靠近0越大，CPU使用率越小越好
        Z_cpu_uti_worst = min(cpu_uti_list)

        Z_mem_uti_best = max(mem_uti_list)  # RAM使用率，越靠近0越大，RAM使用率越小越好
        Z_mem_uti_worst = min(mem_uti_list)

        Z_remain_capa_best = max(remain_capa_list) # 磁盘剩余容量，越大越好
        Z_remain_capa_worst = min(remain_capa_list)
        

        # 计算每个节点的4个状态到正理想解和负理想解的距离D+ D-，并计算相对贴进度
        relative_closeness = []  # 保存每个主机与最优主机状态的相对贴近度
        for step, each_host_stats in enumerate(decision_matrix):
            load = each_host_stats[0]
            cpu_uti = each_host_stats[1]
            mem_uti = each_host_stats[2]
            remain_capa = each_host_stats[3]
            # 计算该主机到正理想解的距离
            best_distance = pow(((load - Z_load_best) ** 2) + \
                            ((cpu_uti - Z_cpu_uti_best) ** 2) + \
                            ((mem_uti - Z_mem_uti_best) ** 2) + \
                            ((remain_capa - Z_remain_capa_best) ** 2), 0.5)

            # 计算该主机到负理想解的距离
            worst_distance = pow(((load - Z_load_worst) ** 2) + \
                            ((cpu_uti - Z_cpu_uti_worst) ** 2) + \
                            ((mem_uti - Z_mem_uti_worst) ** 2) + \
                            ((remain_capa - Z_remain_capa_worst) ** 2), 0.5)
            
            # 计算该主机与最优状态的相对贴近度
            r_c = round(worst_distance / (best_distance + worst_distance), 3)
            if r_c == 0.0:
                r_c = 0.1 # 保持最小的值不为0
            relative_closeness.append(r_c)

        # 根据相对贴近度，计算每个节点应该存储的占比，总大小为1.0
        sum = 0
        proportion_list = []
        for each in relative_closeness:
            sum += each
        for step, each in enumerate(relative_closeness):
            if (step + 1) != len(relative_closeness): # 遍历最后一个之前的数
                each_proportion = round(each / sum, 2)
            else:
                each_proportion = round(1.0 - np.sum(proportion_list), 2)
            proportion_list.append(each_proportion)
        if np.sum(proportion_list) != 1.0:
            print("综合占比不为1.0 ，请检查")
        
        # 计算每一份的文件分别分割成多大
        split_result = {}
        sum_count = 0
        for step, (each_host_ip, each_proportion) in enumerate(zip(host_nodes_list, proportion_list)):
            if (step + 1) != len(proportion_list): # 防止最后一个不为整数
                size = int(self.file_size * each_proportion) # 计算分割后的文件大小，并取整
                sum_count += size
            else:
                size = self.file_size - sum_count

            split_result[each_host_ip] = size # 对应host_ip保存

        sum = 0
        for value in split_result.values():
            sum += int(value)
        if sum != self.file_size:
            print("文件大小计算错误，请检查!")
            print('左', sum, type(sum))
            print('右', self.file_size, type(self.file_size))
            return None
        else:
            print("<host_MADM.py>      文件总大小:%s" %self.file_size)
            print("<host_MADM.py>      分割结果为:%s" %split_result)
            return split_result
        
        

        


        
        