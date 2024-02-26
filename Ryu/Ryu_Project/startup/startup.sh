#!/bin/bash
###
 # @Author: louis
 # @Date: 2023-05-23 10:30:30
 # @Connection: louis.yyj.dev@foxmail.com
 # @FilePath: \N5105_share\SDN_Project\startup\startup.sh
 # @Description: xxx

### 
### 
ryu-manager ../ryu_app/network_structure.py ../ryu_app/network_monitor.py ../ryu_app/network_calculate_path.py  ../utils/arp_utils.py ../ryu_app/host_get_msg.py ../ryu_app/host_multi_attr_decision_make.py startup.py --observe-links