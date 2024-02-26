<!--
 * @Author: louis
 * @Date: 2023-04-28 11:51:12
 * @Connection: louis.yyj.dev@foxmail.com
 * @FilePath: \N5105_share\SDN_Project\code_log\develop_logger.md
 * @Description: xxx
-->
# logger
### 1.data:2023.5.3 - 代码优化，host_access转移到calculate_shortest.py下
### 2.data:2023.5.3 - 代码优化，原weight、calculate_path函数集中到calculate_shortest.py下
### 3.data:2023.5.4 - 代码优化，三个packet_in_handler被合并成了2个
### 4.data:2023.5.6 - 解决bug，当一个主机从一个wifi切换到另一个wifi时显示端口不一致，无法下发流表问题
### 5.data:2023.5.7 - 解决bug，仅有1个交换机时，下发流表出现问题
### 6.data:2023.5.8 - 解决bug，host1(Windows) - host2(Linux)可通，但反过来不可通，原因是Windows的防火墙未关闭
### 7.data:2023.5.20 - 代码优化，保存端口历史流量数据从5个变为3个
### 8.data:2023.5.21 - 解决bug，增加无线端口的最大速率识别
### 9.data:2023.5.21 - 代码优化，去除monitor中flow测速部分
### 10.data:2023.5.22 - 代码优化，所有协程统一用startup文件启动
### 11.data:2023.5.24 - 解决bug，有时port_desc返回的信息中，curr_speed与max_speed是不在properties里的
### 12.data:2023.5.25 - 项目结构优化，分为:Ryu、utils、config、startup、log结构
### 13.data:2023.5.26 - 适配硬件交换机，解决硬件中存在先后上线的交换机，导致端口统计流量计算loss不准确问题
### 13.data:2023.6.8 - 代码优化， 新增IPv4包的dst为控制器IP的判断，防止主机上报状态被下发的流表转发，上报不到控制器


# discover shortage：
### 1.交换机如果拔掉网线，是不会触发EventOFPStateChange事件然后记录交换机下线
### 2.Windows在不手动设置完整IP信息时，连接SDN交换机会出现arp.src_ip = 0.0.0.0，arp.dst_ip才是被SDN交换机分配的Ip(已解决)
### 3.Linux ping Windows出现下发流表成功但无法ping通，反过来可以，Linux互ping无问题(已解决)
### 4.当两个host连接同一个WiFi时，会相互覆盖host_access表数据的问题(需要重新建立非字典式的容器记录host ip)
### 5.交换机的网关有时会被当做主机IP加入到主机列表当中
