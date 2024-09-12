import json
import data_process
import random
import copy
import sys
import math
import time
from functools import reduce
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib
import pytz

#读json数据函数
def read_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

Q = 1000

#城市数（结点数）
city_num = 0

#距离矩阵D
D = []
#[[0   ，工时2，工时3，...]
# [工时1，0   ，工时3，...]
# [工时1,工时2，0，...]]

#换型矩阵
change_equipment = []
change_equipment_time = []

#时间需求矩阵
#记录每个工序需要的工时
time_needs = []

#准备工时
prepare_time = []

#作业工时
work_time = []

#后置工时矩阵
post_time = []

#资源需求矩阵
#存储着每个工序对应的资源需求
#[[工序1的资源需求],[工序2的资源需求],[工序3的资源需求]]
resources_need = []

#前置工序/工单矩阵
#每个工序的前置工序是否被完成
#用True和False表示
post_process = []

#用于在倒排中判断其后置工序是否完成
#用True和False表示
pre_process = []

#工单/物料/工序结点表
#存储着所有的工单物料工序
point_table = []

#每个工序是正排还是倒排
#用字典表示，键为每个工序的名字，值为该工序是正排还是倒排，正排True，倒排False
front_or_back = dict()

#正排工序的数量和倒排工序的数量
front_work = 0
reverse_work = 0

#已完成工序（后置工时也完成）列表
#记录工序是否已完成，用True和False表示
finish_work = []

#已被选择工序列表
#记录工序是否已被选择，用True和False表示
chooced_work = []

# 锁排程
# 存储被锁住的工序和对应的开始时间结束时间
locked_work = dict()

#迭代轮次n
epoch = 10
#蚂蚁个数m
ant_num = 30
#信息素矩阵
pheromone_graph = []
old_pheromone_graph = []
#可见度矩阵
see_graph = []
#信息素指数
ALPHA = 1.5
#可见度指数
BETA = 2.0
#挥发系数
RHO = 0.9
#搜索禁忌表
taboo_table = []
#倒排搜索禁忌表
taboo_table_reverse = []
#当前时间(年月日时分)
current_time = 0
#倒排的当前时间(年月日时分)
current_time_reverse = 0

#开始时间
start_time = 0

#结束时间
end_time = 0

#当前资源数量列表
#当前时间下所有资源的数量列表
current_resources_count = []

#当前可用资源列表
#当前时间下每个资源是否可用，用True和False来表示
resources_useful = []

#资源列表
#所有的资源列表
resources = []

#资源的开始时间及结束时间
#每个资源的开始时间和结束时间表[开始时间，结束时间]
resources_usetime = []

#资源数量列表
#每个资源的初始可用数量
resources_count = []

#用时最少的最后时间
min_current_time = 1000000000000

#用时最少的工序执行顺序
min_results = dict()

min_current_time_reverse = 0
min_results_reverse = dict()

#最终正排工序的执行字典
results = dict()

#最终倒排工序的执行字典
results_reverse = dict()

#用于处理设备换型的执行字典
results_for_change_equipment = dict()

#用于处理设备换型的倒排执行字典
results_for_change_equipment_reverse = dict()

# 结果矩阵
results_list = []

#迭代次数
iter_list = []

# 将最后结果转成json
def generate_json(result, resource_needs, point_table, file_path):
    output_list = []

    for key, value in result.items():
        order_id, material_id, process_id = key[:4], key[4:8], key[8:]
        process = order_id + material_id + process_id
        process_index = point_table.index(process)
        resources = resource_needs[process_index]
        
        if resources:
            for resource in resources:
                resource_type, resource_count = resource[:-1], resource[3:]
                output_list.append({
                    "工单编号": order_id,
                    "物料编号": material_id,
                    "工序": process_id,
                    "资源类型": resource_type,
                    "资源数量": resource_count,
                    "计划开始时间": value[0],
                    "计划结束时间": value[1]
                })
        else:
            output_list.append({
                "工单编号": order_id,
                "物料编号": material_id,
                "工序": process_id,
                "资源类型": "虚拟资源",
                "资源数量": "1",
                "计划开始时间": value[0],
                "计划结束时间": value[1]
            })



    # 将结果保存到JSON文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(output_list, f, ensure_ascii=False, indent=4)

# 初始化换型矩阵
def clean_change_equipment_array(data):
    if len(change_equipment) == 0:
        for job_info in data["设备换型"]:
            if job_info == "工序列表":
                for work in data["设备换型"][job_info]:
                    temp = ""
                    temp += work[0:4]
                    temp += work[5:]
                    change_equipment.append(temp)
            if job_info == "换型矩阵":
                for i in data["设备换型"][job_info]:
                    for j in range(0,len(i)):
                        i[j] = int(i[j])
                    change_equipment_time.append(i)

#初始化工单/物料/工序结点表
def change_point_table(data):
    if len(point_table) == 0:
        for job_info in data["工艺路线"].items():
            temp = ""
            temp += job_info[0]
            for job in job_info[1].items():
                temp += job[0]
                for work in job[1].items():
                    if work[0] == "工序列表":
                        for i in work[1]:
                            temp1 = temp
                            temp1 += i
                            point_table.append(temp1)
                            finish_work.append(False)
                            chooced_work.append(False)
    if len(time_needs) == 0:
        for job_info in data["工艺路线"].items():
            for job in job_info[1].items():
                for work in job[1].items():
                    if work[0] == "准备工时":
                        for time in work[1]:
                            prepare_time.append(time)
                    if work[0] == "作业工时":
                        for time in work[1]:
                            work_time.append(time)
                    if work[0] == "后置工时":
                        for time in work[1]:
                            post_time.append(time)
    print("工单/物料/工序结点表初始化完毕")

# 在全部工单中读取正倒排策略，若该工单为正排，将其留在point_table中；若其为倒排，将其取出，并放在point_table_post中
def change_front_back(data):
    global front_or_back
    global front_work
    global reverse_work
    if len(front_or_back) == 0:
        for job_info in data["全部工单"].items():
            temp = ""
            temp += job_info[0]
            for job in job_info[1].items():
                if job[0] == "物料编码":
                    temp += job[1]
                if job[0] == "排程策略" and job[1] == "正排":
                    for i in point_table:
                        if i[0:8] == temp:
                            front_or_back[i] = True
                            front_work += 1
                if job[0] == "排程策略" and job[1] == "倒排":
                    for i in point_table:
                        if i[0:8] == temp:
                            front_or_back[i] = False
                            reverse_work += 1

#初始化前置工序矩阵
def change_post_process(data):
    #首先全部默认为True
    if len(post_process) == 0:
        for i in range(0, len(point_table)):
            post_process.append(True)
    post_process_gongdan = []
    for i in range(0, len(point_table)):
            post_process_gongdan.append(True)
    post_process_gongxu = []
    for i in range(0, len(point_table)):
            post_process_gongxu.append(True)
    #接着判断前置工序
    for job_info in data["工艺路线"].items():
        for job in job_info[1].items():
            for information in job[1].items():
                if information[0] == "前置工序":
                    for i in information[1]:
                        for j in range(1,len(post_process)):
                            if point_table[j - 1][0:4] == job_info[0] and point_table[j - 1][4:8] == job[0] and point_table[j - 1][8:] == i and finish_work[j - 1] == False:
                                post_process_gongxu[j] = False
                            elif point_table[j - 1][0:4] == job_info[0] and point_table[j - 1][4:8] == job[0] and point_table[j - 1][8:] == i and finish_work[j - 1] == True:
                                post_process_gongxu[j] = True
    #接着检验前置工单
    for job_info in data["全部工单"].items():
        temp = ""
        for job in job_info[1].items():
            if job[0] == "工单编号":
                temp += job[1]
            if job[0] == "物料编码":
                temp += job[1]
            if job[0] == "前置工单" and job[1] != "/":
                #所有含前置工单的工单，且其前置工单未完成，初始化为False
                for i in range(0, len(post_process)):
                    if point_table[i][0:4] == job[1] and finish_work[i] == False:
                        for j in range(0, len(point_table)):
                            if point_table[j][0:8] == temp:
                                post_process_gongdan[j] = False
                    elif point_table[i][0:4] == job[1] and finish_work[i] == True:
                        for j in range(0, len(point_table)):
                            if point_table[j][0:8] == temp:
                                post_process_gongdan[j] = True
    for i in range(0, len(post_process)):
        if post_process_gongdan[i] and post_process_gongxu[i]:
            post_process[i] = True
        else:
            post_process[i] = False
    print("前置工序调整完毕")

#初始化倒排用到的前置工序矩阵
def change_pre_process(data):
    #首先全部默认为True
    if len(pre_process) == 0:
        for i in range(0, len(point_table)):
            pre_process.append(True)
    pre_process_gongdan = []
    for i in range(0, len(point_table)):
            pre_process_gongdan.append(True)
    pre_process_gongxu = []
    for i in range(0, len(point_table)):
            pre_process_gongxu.append(True)
    #接着判断前置工序
    for job_info in data["工艺路线"].items():
        temp = ""
        work_list = []
        temp += job_info[0]
        for job in job_info[1].items():
            temp += job[0]
            for information in job[1].items():
                if information[0] == "工序列表":
                    work_list = information[1][:]
                if information[0] == "前置工序":
                    # 所有含前置工序的工序，若该工序未完成，则其前置工序为false
                    for i in range(0, len(information[1])):
                        if information[1][i] != '/':
                            temp_now = temp + work_list[i]
                            temp_post = temp + information[1][i]
                            if finish_work[point_table.index(temp_now)] == False:
                                pre_process_gongxu[point_table.index(temp_post)] = False
                            elif finish_work[point_table.index(temp_now)] == True:
                                pre_process_gongxu[point_table.index(temp_post)] = True
   #接着检验前置工单
    for job_info in data["全部工单"].items():
        temp = ""
        for job in job_info[1].items():
            if job[0] == "工单编号":
                temp += job[1]
            if job[0] == "物料编码":
                temp += job[1]
            if job[0] == "前置工单" and job[1] != "/":
                #所有含前置工单的工单，且该工单未完成，初始化前置工单为False
                for i in range(0, len(post_process)):
                    #该工单未完成
                    if point_table[i][0:4] == temp and finish_work[i] == False:
                        for j in range(0, len(point_table)):
                            if point_table[j][0:8] == temp:
                                pre_process_gongdan[j] = False
                    #该工单完成
                    elif point_table[i][0:4] == job[1] and finish_work[i] == True:
                        for j in range(0, len(point_table)):
                            if point_table[j][0:8] == temp:
                                pre_process_gongdan[j] = True
    for i in range(0, len(post_process)):
        if pre_process_gongdan[i] and pre_process_gongxu[i]:
            pre_process[i] = True
        else:
            pre_process[i] = False
    print("倒排所需前置工单初始化完成")

#根据准备工时，作业工时，后置工时和需要的工单数量来生成对应的总工时
def change_time_needs(data):
    global time_needs
    count_list = []
    if len(time_needs) == 0:
        for job_info in data["全部工单"].items():
            temp = ""
            for job in job_info[1].items():
                count = 0
                if job[0] == "工单编号":
                    temp += job[1]
                if job[0] == "物料编码":
                    temp += job[1]
                if job[0] == "数量":
                    count = job[1]
                for i in range(0, len(point_table)):
                    if point_table[i][0:8] == temp and count != 0:
                        count_list.append(count)
        for job_info in data["工艺路线"].items():
            temp = ""
            temp += job_info[0]
            for job in job_info[1].items():
                temp += job[0]
                for work in job[1].items():
                    if work[0] == "工序列表":
                        for name in work[1]:
                            temp_name = temp
                            temp_name += name
                            for i in range(0, len(point_table)):
                                if point_table[i] == temp_name:
                                    time_needs.append(prepare_time[i] + work_time[i] * count_list[i] + post_time[i])


#根据输入的数据来初始化距离矩阵D
def changeD(data):
    global D
    D = []
    for i in range(0, len(point_table)):
        #对temp进行浅拷贝，从而改变的时候不会涉及temp
        D.append(time_needs[:])
    for i in range(0, len(time_needs)):
        D[i][i] = 0
    print("距离矩阵D初始化完成")

#初始化时间
def clean_time(data):
    global start_time
    for job_info in data["全部工单"].items():
        for information in job_info[1].items():
            if information[0] == "计划开始时间":
                time = int(information[1][0:4])*100000000 + int(information[1][5:7])*1000000 + int(information[1][8:])*10000
                if start_time > time or start_time == 0:
                    start_time = time
    print("开始时间初始化完成")
    return start_time

#初始化倒排的时间
def clean_time_reverse(data):
    global end_time
    for job_info in data["全部工单"].items():
        temp = False
        for information in job_info[1].items():
            if information[0] == "排程策略":
                if information[1] == "倒排":
                    temp = True
            if information[0] == "计划完工时间" and temp:
                time = int(information[1][0:4])*100000000 + int(information[1][5:7])*1000000 + (int(information[1][8:]))*10000 + 2359
                if end_time < time or end_time == 0:
                    end_time = time
    print("开始时间初始化完成")
    return end_time

#初始化资源列表及资源/时间列表
def clean_resources(data):
    if len(current_resources_count) == 0:
        begin_time = 0
        end_time = 0
        for job_info in data["资源日历"].items():
            for information in job_info[1].items():
                if information[0] == "资源名称":
                    resources.append(information[1])
                if information[0] == "资源数量":
                    resources_count.append(information[1])
                    current_resources_count.append(information[1])
                if information[0] == "开始日期":
                    begin_time = int(information[1][0:4])*100000000 + int(information[1][5:7])*1000000 + int(information[1][8:])*10000
                if information[0] == "结束日期":
                    end_time = int(information[1][0:4])*100000000 + int(information[1][5:7])*1000000 + int(information[1][8:])*10000
                if information[0] == "开始时间":
                    begin_time += int(information[1][0:2])*100 + int(information[1][3:])
                if information[0] == "结束时间":
                    end_time += int(information[1][0:2])*100 + int(information[1][3:])
            resources_usetime.append([begin_time, end_time])
            begin_time, end_time = (0, 0)
    print("资源列表及资源/时间列表初始化完成")

#生成资源需求矩阵
def create_resources_need(data):
    if len(resources_need) == 0:
        for job_info in data["工艺路线"].items():
            for job in job_info[1].items():
                for needs in job[1]["资源需求"]:
                    resources_need.append(needs[:])
    print("资源需求矩阵初始化完成")

#根据当前时间和当前资源数量表，来生成当前可用资源表
#要求当前时间处于资源可利用时间，且当前资源数量大于0
def create_resources_useful(current_time, current_resources_count, resources, resources_usetime):
    if len(resources_useful) == 0:
        for i in range(0, len(resources)):
            resources_useful.append(True)
        print("当前可用资源表初始化完成")
    else:
        for i in range(0, len(resources)):
            if current_time >= resources_usetime[i][0] and current_time <= resources_usetime[i][1] and current_resources_count[i] != 0:
                resources_useful[i] = True
            else:
                resources_useful[i] = False

#根据现在的时间和资源数量来决定搜索禁忌表
#如果当前的可用资源表中不含有该工序所需的所有资源或资源数目不够，则其不可以被搜索
#如果该工序的前置工序没有被完成，则该工序不可以被搜索
def change_taboo_table(resources_need, resources_useful, current_resources_count):
    global results_for_change_equipment
    global taboo_table
    taboo_table = []
    for i in range(0, len(point_table)):
        #首先判断该工序是否被选择
        if chooced_work[i] and point_table[i] not in taboo_table:
            taboo_table.append(point_table[i])
        #接着判断该工序的前置工序是否完成
        #若前置工序没有完成，则post_progress中对应下标的值为False，此时将其放入禁忌搜索表中
        if not post_process[i] and point_table[i] not in taboo_table:
            taboo_table.append(point_table[i])
        #接着判断当前的可用资源表中是否含有该工序所需的所有资源
        for j in range(0, len(resources_need[i])):
            for k in resources:
                if k == resources_need[i][j][0:3]:
                    if (not resources_useful[j]) or int(resources_need[i][j][3]) > current_resources_count[j]:
                        if point_table[i] not in taboo_table:
                            taboo_table.append(point_table[i])
        #接着判断换型矩阵
        if point_table[i][4:] in change_equipment and chooced_work[i] == True and len(results_for_change_equipment[point_table[i]]) > 1:
            for j in range(0, len(point_table)):
                if point_table[j][4:] in change_equipment and finish_work[j] == False:
                    if subtime(current_time, results_for_change_equipment[point_table[i]][1]) <= change_equipment_time[change_equipment.index(point_table[j][4:])][change_equipment.index(point_table[i][4:])]:
                        if point_table[j] not in taboo_table:
                            taboo_table.append(point_table[j])
        # 接着考虑锁排程
        if point_table[i] in locked_work and point_table[i] not in taboo_table:
            taboo_table.append(point_table[i])
        for work in locked_work:
            # 该锁排程需要的资源列表
            resources_need_lockedwork = resources_need[point_table.index(work)]
            locked_work_starttime = locked_work[work][0]
            locked_work_endtime = locked_work[work][1]
            # 该工序需要的时间和资源
            pass_time = time_needs[i] - post_time[i]
            if point_table[i][4:] in change_equipment:
                pass_time += change_equipment_time[change_equipment.index(work[4:])][change_equipment.index(point_table[i][4:])]
            resources_need_work = resources_need[i]
            # 当前时间加上该工序所需时间
            temp_time = change_current_time(current_time, pass_time, True)
            temp_resources_count = current_resources_count[:]
            # 若当前时间加上该工序所需时间在锁排程时间范围内
            if current_time <= locked_work_endtime and temp_time >= locked_work_starttime:
                # 且其资源在使用后不足以支撑锁排程进行
                # 当前资源数量减去该工序所需的资源数量
                for j in range(0,len(resources)):
                    for k in resources_need_work:
                        if resources[j] == k[0:3]:
                            temp_resources_count[j] -= int(k[3:])
                for j in range(0, len(resources)):
                    for k in resources_need_lockedwork:
                        if (resources[j] == k[0:3] and temp_resources_count[j] < int(k[3:])):
                            if point_table[i] not in taboo_table:
                                taboo_table.append(point_table[i])
        #接着考虑正倒排, 该程序处理正排
        if front_or_back[point_table[i]] == False and point_table[i] not in taboo_table:
            taboo_table.append(point_table[i])
    print("搜索禁忌表修改完成")

#根据现在的时间和资源数量来决定倒排搜索禁忌表
#如果当前的可用资源表中不含有该工序所需的所有资源或资源数目不够，则其不可以被搜索
#如果该工序的后置工序没有被完成，则该工序不可以被搜索
def change_taboo_table_reverse(resources_need, resources_useful, current_resources_count):
    global results_for_change_equipment
    global taboo_table_reverse
    taboo_table_reverse = []
    for i in range(0, len(point_table)):
        #首先判断该工序是否被选择
        if chooced_work[i] and point_table[i] not in taboo_table_reverse:
            taboo_table_reverse.append(point_table[i])
        #接着判断该工序的后置工序是否完成
        #若后置工序没有完成，则pre_progress中对应下标的值为False，此时将其放入禁忌搜索表中
        if not pre_process[i] and point_table[i] not in taboo_table_reverse:
            taboo_table_reverse.append(point_table[i])
        #接着判断当前的可用资源表中是否含有该工序所需的所有资源
        for j in range(0, len(resources_need[i])):
            for k in resources:
                if k == resources_need[i][j][0:3]:
                    if (not resources_useful[j]) or int(resources_need[i][j][3]) > current_resources_count[j]:
                        if point_table[i] not in taboo_table_reverse:
                            taboo_table_reverse.append(point_table[i])
        #接着判断换型矩阵
        if point_table[i] in results_for_change_equipment_reverse:
            if point_table[i][4:] in change_equipment and chooced_work[i] == True and results_for_change_equipment_reverse[point_table[i]][0] != 0:
                for j in range(0, len(point_table)):
                    if point_table[j][4:] in change_equipment and finish_work[j] == False:
                        if subtime(results_for_change_equipment_reverse[point_table[i]][0], current_time_reverse) < change_equipment_time[change_equipment.index(point_table[j][4:])][change_equipment.index(point_table[i][4:])]:
                            if point_table[j] not in taboo_table_reverse:
                                taboo_table_reverse.append(point_table[j])
        # 接着考虑锁排程
        if point_table[i] in locked_work and point_table[i] not in taboo_table_reverse:
            taboo_table_reverse.append(point_table[i])
        for work in locked_work:
            # 该锁排程需要的资源列表
            resources_need_lockedwork = resources_need[point_table.index(work)]
            locked_work_starttime = locked_work[work][0]
            locked_work_endtime = locked_work[work][1]
            # 该工序需要的时间和资源
            pass_time = time_needs[i] - post_time[i]
            if point_table[i][4:] in change_equipment:
                pass_time += change_equipment_time[change_equipment.index(work[4:])][change_equipment.index(point_table[i][4:])]
            resources_need_work = resources_need[i]
            # 当前时间加上该工序所需时间
            temp_time = change_current_time(current_time, pass_time, True)
            temp_resources_count = current_resources_count[:]
            # 若当前时间加上该工序所需时间在锁排程时间范围内
            if current_time <= locked_work_endtime and temp_time >= locked_work_starttime:
                # 且其资源在使用后不足以支撑锁排程进行
                # 当前资源数量减去该工序所需的资源数量
                for j in range(0,len(resources)):
                    for k in resources_need_work:
                        if resources[j] == k[0:3]:
                            temp_resources_count[j] -= int(k[3:])
                for j in range(0, len(resources)):
                    for k in resources_need_lockedwork:
                        if (resources[j] == k[0:3] and temp_resources_count[j] < int(k[3:])):
                            if point_table[i] not in taboo_table_reverse:
                                taboo_table_reverse.append(point_table[i])
        #接着考虑正倒排, 该程序处理倒排
        if front_or_back[point_table[i]] == True and point_table[i] not in taboo_table_reverse:
            taboo_table_reverse.append(point_table[i])
    print("倒排搜索禁忌表修改完成")

#根据输入的city_index，和状态（state = True，说明是取出资源；state = False，说明是放回资源）调整当前的资源数量
def set_current_resources_count(data, city_index, state):
    for job_info in data["工艺路线"].items():
        if job_info[0] == point_table[city_index][0:4]:
            for job in job_info[1].items():
                if job[0] == point_table[city_index][4:8]:
                    temp = 0
                    for informstion in job[1].items():
                        if informstion[0] == "工序列表":
                            for work in informstion[1]:
                                if work == point_table[city_index][8:]:
                                    break
                                temp += 1 
                        if informstion[0] == "资源需求":
                            for i in informstion[1][temp]:
                                for resource in range(0,len(resources)):
                                    if i[0:3] == resources[resource]:
                                        if state:
                                            current_resources_count[resource] -= int(i[-1])
                                        else:
                                            current_resources_count[resource] += int(i[-1])
    print("当前资源数量调整完成")

# 初始化锁排程
def clean_locked_work(data):
    global locked_work
    if len(locked_work) == 0:
        for job_info in data["锁排程"].items():
            temp = ""
            temp += job_info[0]
            for job in job_info[1].items():
                temp += job[0]
                for work in job[1].items():
                    if work[0] == "工序":
                        temp += work[1]
                        locked_work[temp] = []
                    if work[0] == "开始时间":
                        time = 0
                        time = int(work[1][0][0][0:4])*100000000 + int(work[1][0][0][5:7])*1000000 + int(work[1][0][0][8:10])*10000 + int(work[1][0][0][11:13])*100 + int(work[1][0][0][14:])
                        locked_work[temp].append(time)
                    if work[0] == "结束时间":
                        time = 0
                        time = int(work[1][0][0][0:4])*100000000 + int(work[1][0][0][5:7])*1000000 + int(work[1][0][0][8:10])*10000 + int(work[1][0][0][11:13])*100 + int(work[1][0][0][14:])
                        locked_work[temp].append(time)

#由于时间的特殊。需要添加一个处理时间的函数
#True表示相加， False表示相减
def change_current_time(time1, time2, state):
    year = int(str(time1)[0:4])
    month = int(str(time1)[4:6])
    day = int(str(time1)[6:8])
    hour = int(str(time1)[8:10])
    minute = int(str(time1)[10:])

    temp_time = datetime(year, month, day, hour, minute)
    change_minute = timedelta(minutes = time2)
    if state == True:
        temp_time = temp_time + change_minute
    else:
        temp_time = temp_time - change_minute
    years = temp_time.year
    months = temp_time.month
    days = temp_time.day
    hours = temp_time.hour
    minutes = temp_time.minute
    time1 = years * 100000000 + months * 1000000 + days * 10000 + hours * 100 + minutes
    return time1

#实现两个时间相减
def subtime(time1, time2):
    time1 = str(time1)
    time2 = str(time2)
    while len(time2) < 12:
        time2 = "0" + time2
    time1_str = ""
    time1_str += time1[0:4]
    time1_str += '-'
    time1_str += time1[4:6]
    time1_str += '-'
    time1_str += time1[6:8]
    time1_str += ' '
    time1_str += time1[8:10]
    time1_str += ':'
    time1_str += time1[10:]
    time1_str += ":"
    time1_str += "00"
    time2_str = ""
    time2_str += time2[0:4]
    time2_str += '-'
    time2_str += time2[4:6]
    time2_str += '-'
    time2_str += time2[6:8]
    time2_str += ' '
    time2_str += time2[8:10]
    time2_str += ':'
    time2_str += time2[10:]
    time2_str += ':'
    time2_str += "00"
    start_time = datetime.strptime(time1_str, "%Y-%m-%d %H:%M:%S")
    endtime = datetime.strptime(time2_str, "%Y-%m-%d %H:%M:%S")
    time_diff = start_time - endtime
    days = time_diff.days
    hours = time_diff.seconds // 3600
    minutes = (time_diff.seconds // 60) % 60 + hours * 60 + days * 1440
    return minutes

def draw_gantt_chart(json_file_path):
    # 设置matplotlib支持中文显示
    matplotlib.rcParams['font.family'] = 'SimHei'  # 设置字体为SimHei支持中文
    matplotlib.rcParams['axes.unicode_minus'] = False  # 正确显示负号

    # 读取JSON文件
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # 准备数据结构
    tasks = {}
    fig, ax = plt.subplots(figsize=(200, 200))

    # 设置日期格式
    ax.xaxis_date()
    plt.setp(ax.get_xticklabels(), rotation=30, ha='right')

    # 设置图表标题和标签
    plt.title('甘特图')
    plt.xlabel('时间')
    plt.ylabel('资源类型')

    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=2))  # 调整为每2小时一个刻度
    ax.xaxis.set_minor_formatter(mdates.DateFormatter('%H:%M'))
    ax.xaxis.set_major_locator(mdates.DayLocator())  # 设置次要刻度为每天
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))  # 定义次要刻度的显示格式为年-月-日

    plt.setp(ax.xaxis.get_minorticklabels(), rotation=90, ha='right', fontsize=10)
    plt.xticks(rotation=90)

    # 解析数据，填充tasks
    for item in data:
        start_time = datetime.strptime(str(item["计划开始时间"]), "%Y%m%d%H%M")
        end_time = datetime.strptime(str(item["计划结束时间"]), "%Y%m%d%H%M")

        duration = (end_time - start_time).total_seconds() / 3600
        label = f"{item['工单编号']} {item['工序']}"
        if item['资源类型'] not in tasks:
            tasks[item['资源类型']] = []
        tasks[item['资源类型']].append((label, start_time, duration))

    # 找到所有任务的最早开始时间和最晚结束时间
    all_start_times = [task[1] for resource_type in tasks for task in tasks[resource_type]]
    all_durations = [task[2] for resource_type in tasks for task in tasks[resource_type]]
    all_end_times = [start_time + timedelta(hours=duration) for start_time, duration in zip(all_start_times, all_durations)]

    min_start_time = min(all_start_times)
    max_end_time = max(all_end_times)

    plt.xlim(mdates.date2num(min_start_time), mdates.date2num(max_end_time + timedelta(hours=2)))

    # 创建一个唯一的任务列表，以便为每个任务分配一个颜色
    colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple', 'tab:brown', 'tab:pink', 'tab:gray', 'tab:olive', 'tab:cyan']
    unique_tasks = []
    for resource_type in tasks:
        for task in tasks[resource_type]:
            if task[0] not in unique_tasks:
                unique_tasks.append(task[0])

    # 创建资源类型到y坐标的映射
    resource_types = list(tasks.keys())
    resource_y_coords = {resource: i * 10 for i, resource in enumerate(resource_types)}

    # 为每个工序创建子坐标并绘制甘特图
    for resource_type, tasks_list in tasks.items():
        base_y_coord = resource_y_coords[resource_type]
        for i, task in enumerate(tasks_list):
            task_index = unique_tasks.index(task[0])
            sub_y_coord = base_y_coord + i
            start_time_num = mdates.date2num(task[1])
            bar = ax.barh(sub_y_coord, task[2] / 24, left=start_time_num, color=colors[task_index % len(colors)], edgecolor='black')
            text_x_num = start_time_num + (task[2] / 24.0) / 2
            text_x = mdates.num2date(text_x_num)
            ax.text(text_x, sub_y_coord, task[0], ha='center', va='center', color='white', fontsize=7)

    ax.set_yticks([y + 5 for y in resource_y_coords.values()])
    ax.set_yticklabels(resource_types)

    plt.show()

# 每当遍历一个节点，需要处理：
# 1. 当前时间: current_time
# 2. 完成工序矩阵：finish_work
# 3. 前置工序矩阵：change_post_process
# 4. 当前资源数量表： current_resources_count
# 5. 搜索禁忌表：taboo_table
class Ant(object):

    # 初始化
    def __init__(self, ID):
        self.ID = ID
        self.__clean_data()
    
    # 初始数据
    def __clean_data(self):
        global current_time
        global current_time_reverse
        current_time = clean_time(data) #初始化当前时间
        current_time_reverse = clean_time_reverse(data) 
        clean_resources(data)           #初始化资源表
        create_resources_need(data)     #初始化资源需求矩阵
        change_point_table(data)        #初始化工单/物料/工序结点表
        change_front_back(data)
        change_post_process(data)       #初始化前置工单表
        change_pre_process(data)
        change_time_needs(data)
        changeD(data)
        clean_locked_work(data)
        #初始化可用资源列表
        create_resources_useful(current_time, current_resources_count, resources, resources_usetime)
        #初始化换型矩阵
        clean_change_equipment_array(data)
        #初始化禁忌搜索表
        change_taboo_table(resources_need, resources_useful, current_resources_count)
        global city_num
        city_num = len(point_table)
        self.path = []              #当前蚂蚁的路径
        self.total_distance = 0.0   #当前路径的总距离
        self.move_count = 0         #移动次数
        self.current_city = -1      #当前停留的城市
        # 初始城市之间的距离和信息素
        global pheromone_graph
        pheromone_graph = [ [1.0 for col in range(city_num)] for raw in range(city_num)]

    # 选择下一个城市
    def choice_next_city(self, taboo_table):

        next_city = -1
        select_citys_prob = [0.0 for i in range(city_num)]  #存储去下个城市的概率
        total_prob = 0.0

        # 获取去下一个城市的概率
        for i in range(city_num):
            # 若该城市不在禁忌搜索表中
            if point_table[i] not in taboo_table and D[self.current_city][i] != 0:
                try:
                    # 计算概率：与信息素浓度成正比，与距离成反比
                    select_citys_prob[i] = pow(pheromone_graph[self.current_city][i], ALPHA) * pow(1.0/D[self.current_city][i], BETA)
                    total_prob += select_citys_prob[i]
                except ZeroDivisionError as e:
                    print ('Ant ID: {ID}, current city: {current}, target city: {target}'.format(ID = self.ID, current = self.current_city, target = i))
                    sys.exit(1)

        #轮盘选择城市
        if total_prob > 0.0:
            # 产生一个随机概率，0.0-total_prob
            temp_prob = random.uniform(0.0, total_prob)
            for i in range(city_num):
                # 若该城市不在禁忌搜索表中
                if point_table[i] not in taboo_table:
                    # 轮次相减
                    temp_prob -= select_citys_prob[i]
                    if temp_prob < 0.0:
                        next_city = i
                        break
        
        if(next_city == -1):
            next_city = random.randint(0, city_num - 1)
            while(point_table[next_city] in taboo_table):
                next_city = random.randint(0, city_num - 1)
        
        #返回下一个城市序号
        return next_city
    
    #计算路径总距离
    def cal_total_distance(self):

        temp_distance = 0.0

        for i in range(1, city_num):
            start, end = self.path[i], self.path[i-1]
            temp_distance += D[start][end]

        #回路
        end = self.path[0]
        temp_distance += D[start][end]
        self.total_distance = temp_distance

    # 移动操作
    def move(self, next_city):

        self.path.append(next_city)
        self.total_distance += D[self.current_city][next_city]
        self.current_city = next_city
        self.move_count += 1

#----------- SSP问题(Shop scheduling problem) -----------

class SSP(object):

    def __init__(self):

        self.new()
        #初始化城市之间的距离
        changeD(data)

    def new(self):

        self.ants = [Ant(ID) for ID in range(ant_num)]  # 初始蚁群
        self.best_ant = Ant(-1)                          # 初始最优解
        self.best_ant.total_distance = 1 << 31           # 初始最大距离
        city_num = len(point_table)
        for i in range(city_num):
            for j in range(city_num):
                pheromone_graph[i][j] = 1.0
        old_pheromone_graph = pheromone_graph

    # 开始搜索正排
    def search_path_front(self, epoch):
        global current_time
        global results
        global results_for_change_equipment
        #一共迭代epoch轮
        for iter in range(0, epoch):
            results = {}
            results_for_change_equipment = {}
            for i in range(0, len(finish_work)):
                if front_or_back[point_table[i]] == True:
                    finish_work[i] = False
                    chooced_work[i] = False
            #初始化
            self.new()
            #生成当前的资源和工序
            change_post_process(data)
            create_resources_useful(current_time, current_resources_count, resources, resources_usetime)

            #根据初始的资源和时间来设置搜索禁忌表
            change_taboo_table(resources_need, resources_useful, current_resources_count)
            
            while(1):
                #选取多个节点
                for ant in self.ants:
                    #如果搜索禁忌表包含所有节点，直接结束
                    i = 0
                    next_city = -1
                    # 处理锁排程
                    if len(locked_work) != 0:
                        for work in locked_work:
                            if front_or_back[work] == True:
                                if change_current_time(current_time, 1, False) == locked_work[work][0] and work not in results:
                                    next_city = point_table.index(work)
                    for i in range(0, len(point_table)):
                        if front_or_back[point_table[i]] == True:
                            if point_table[i] not in taboo_table:
                                break
                    if i == len(point_table) - 1 and len(taboo_table) == len(point_table) and next_city == -1:
                        break
                    #选择下一个结点
                    #说明该结点正排
                    while next_city == -1 or front_or_back[point_table[next_city]] == False :
                        next_city = ant.choice_next_city(taboo_table)
                    chooced_work[next_city] = True
                    ant.move(next_city)
                    #根据所选结点设置消耗资源
                    set_current_resources_count(data, next_city, True)
                    #更新可用资源
                    create_resources_useful(current_time, current_resources_count, resources, resources_usetime)
                    #将当前添加节点的开始时间记录下来
                    if current_time != start_time:
                        results[point_table[next_city]] = [change_current_time(current_time, 1, False)]
                        results_for_change_equipment[point_table[next_city]] = [change_current_time(current_time, 1, False)]
                    else:
                        results[point_table[next_city]] = [current_time]
                        results_for_change_equipment[point_table[next_city]] = [current_time]
                    #更新搜索禁忌表
                    change_taboo_table(resources_need, resources_useful, current_resources_count)

                #根据当前时间更新可用资源
                create_resources_useful(current_time, current_resources_count, resources, resources_usetime)
                for i in results:
                    # 说明该工序被完成
                    if len(results[i]) == 1:
                        #距离该工序的开始时间已经过去的时间
                        pass_time = subtime(current_time, results[i][0])
                        #当前工序已完成，但还没完成后置工时，此时该工序未完全完成，但已经可以把资源放回
                        if pass_time == time_needs[point_table.index(i)] - post_time[point_table.index(i)] and len(results_for_change_equipment[i]) == 1:
                            results_for_change_equipment[i].append(current_time)
                            #放回资源
                            set_current_resources_count(data, point_table.index(i), False)
                            #更新可用资源
                            create_resources_useful(current_time, current_resources_count, resources, resources_usetime)
                            #更新搜索禁忌表
                            change_taboo_table(resources_need, resources_useful, current_resources_count)

                        #当前工序已完全完成，可以更新前置工序表
                        if subtime(current_time, results[i][0]) == time_needs[point_table.index(i)] and len(results[i]) == 1:
                            finish_work[point_table.index(i)] = True
                            # 记录结束时间
                            results[i].append(change_current_time(current_time, post_time[point_table.index(i)], False))
                            #更新前置工序表
                            change_post_process(data)
                            #更新搜索禁忌表
                            change_taboo_table(resources_need, resources_useful, current_resources_count)

                        for work in locked_work:
                            if front_or_back[work] == True:
                                if i == work:
                                    if current_time == locked_work[work][1] and len(results_for_change_equipment[i]) == 1:
                                        results_for_change_equipment[i].append(current_time)
                                        #放回资源
                                        set_current_resources_count(data, point_table.index(i), False)
                                        #更新可用资源
                                        create_resources_useful(current_time, current_resources_count, resources, resources_usetime)
                                        #更新搜索禁忌表
                                        change_taboo_table(resources_need, resources_useful, current_resources_count)
                                if i == work and len(results_for_change_equipment[i]) == 2:
                                    if subtime(current_time, results_for_change_equipment[i][1]) == post_time[point_table.index(i)] and len(results[i]) == 1:
                                        finish_work[point_table.index(i)] = True
                                        finish_work[point_table.index(i)] = True
                                        # 记录结束时间
                                        results[i].append(change_current_time(current_time, post_time[point_table.index(i)], False))
                                        #更新前置工序表
                                        change_post_process(data)
                                        #更新搜索禁忌表
                                        change_taboo_table(resources_need, resources_useful, current_resources_count)


                # 更新当前时间
                current_time = change_current_time(current_time, 1, True)
                #更新搜索禁忌表
                change_taboo_table(resources_need, resources_useful, current_resources_count)
                print(current_time)

                i = 0
                j = 0
                num = 0
                temp = 0
                final_work = ""
                for i in front_or_back:
                    if front_or_back[i] == True:
                        num += 1
                        final_work = i
                        if finish_work[point_table.index(i)] == False:
                            break
                for j in results:
                    temp += 1
                    if len(results[j]) == 1:
                        break
                #所有正排工序都已经被完成了，继续下一个epoch
                if num == front_work  and temp == len(results):
                    if final_work == "":
                        break
                    elif finish_work[point_table.index(final_work)] != False:
                        break
            
            #更新信息素
            self.__update_pheromone_graph(pheromone_graph)

            latest_time = 0
            for work in results:
                if results[work][1] > latest_time:
                    latest_time = results[work][1]

            # 最后将results中最晚完成的时间作为结果时间
            current_time = latest_time
            # 此时的current_time为完成此次遍历的current_time
            global min_current_time, min_results
            if current_time < min_current_time:
                min_current_time = current_time
                min_results = results
            
            results_list.append(min_current_time)
            iter_list.append(iter)
            print("迭代次数：", iter, "正排最佳完成时间", min_current_time)
    
    # 开始搜索倒排
    def search_path_reverse(self, epoch):
        global current_time_reverse
        global results_reverse
        global results_for_change_equipment_reverse
        #一共迭代epoch轮
        for iter in range(0, epoch):
            if reverse_work == 0:
                break
            results_reverse = {}
            results_for_change_equipment_reverse = {}
            for i in range(0, len(finish_work)):
                if front_or_back[point_table[i]] == False:
                    finish_work[i] = False
                    chooced_work[i] = False
            #初始化
            self.new()
            #生成当前的资源和工序
            change_pre_process(data)
            create_resources_useful(current_time_reverse, current_resources_count, resources, resources_usetime)

            #根据初始的资源和时间来设置搜索禁忌表
            change_taboo_table_reverse(resources_need, resources_useful, current_resources_count)
            
            while(1):
                #选取多个节点
                for ant in self.ants:
                    #如果搜索禁忌表包含所有节点，直接结束
                    i = 0
                    next_city = -1
                    # 处理锁排程
                    if len(locked_work) != 0:
                        for work in locked_work:
                            if front_or_back[work] == False:
                                if change_current_time(current_time_reverse, 1, False) == locked_work[work][0] and work not in results_reverse:
                                    next_city = point_table.index(work)
                    for i in range(0, len(point_table)):
                        if front_or_back[point_table[i]] == False:
                            if point_table[i] not in taboo_table_reverse:
                                break
                    if i == len(point_table) - 1 and len(taboo_table_reverse) == len(point_table) and next_city == -1:
                        break
                    #选择下一个结点
                    #说明该结点倒排
                    while next_city == -1 or front_or_back[point_table[next_city]] == True :
                        next_city = ant.choice_next_city(taboo_table_reverse)
                    chooced_work[next_city] = True
                    ant.move(next_city)
                    #根据所选结点设置消耗资源
                    set_current_resources_count(data, next_city, True)
                    #更新可用资源
                    create_resources_useful(current_time_reverse, current_resources_count, resources, resources_usetime)
                    #将当前添加节点的结束时间记录下来
                    if current_time_reverse != end_time:
                        results_reverse[point_table[next_city]] = [0, change_current_time(change_current_time(current_time_reverse, 1, True), post_time[next_city], False)]
                        results_for_change_equipment_reverse[point_table[next_city]] = [0, change_current_time(change_current_time(current_time_reverse, 1, True), post_time[next_city], False)]
                    else:
                        results_reverse[point_table[next_city]] = [0, change_current_time(current_time_reverse, post_time[next_city], False)]
                        results_for_change_equipment_reverse[point_table[next_city]] = [0, change_current_time(current_time_reverse, post_time[next_city], False)]
                    #更新搜索禁忌表
                    change_taboo_table_reverse(resources_need, resources_useful, current_resources_count)

                #根据当前时间更新可用资源
                create_resources_useful(current_time_reverse, current_resources_count, resources, resources_usetime)
                for i in results_reverse:
                    # 说明该工序被完成
                    if results_reverse[i][0] == 0:
                        #距离该工序的结束时间已经过去的时间
                        pass_time = subtime(current_time_reverse, results_reverse[i][1])
                        #当前工序已完成，但还没完成后置工时，此时该工序未完全完成，但已经可以把资源放回
                        #if pass_time == time_needs[point_table.index(i)] - post_time[point_table.index(i)] and len(results_for_change_equipment[i]) == 1:
                        #    results_for_change_equipment[i].append(current_time)
                        #    #放回资源
                        #    set_current_resources_count(data, point_table.index(i), False)
                        #    #更新可用资源
                        #    create_resources_useful(current_time, current_resources_count, resources, resources_usetime)
                        #   #更新搜索禁忌表
                        #    change_taboo_table(resources_need, resources_useful, current_resources_count)

                        #当前工序已完全完成，可以更新后置工序表和资源
                        if subtime(results_reverse[i][1], current_time_reverse) == time_needs[point_table.index(i)] and results_reverse[i][0] == 0:
                            finish_work[point_table.index(i)] = True
                            # 记录开始时间
                            results_reverse[i][0] = current_time_reverse
                            results_for_change_equipment_reverse[i][0] = current_time_reverse
                            #更新后置工序表
                            change_pre_process(data)
                            #放回资源
                            set_current_resources_count(data, point_table.index(i), False)
                            #更新可用资源
                            create_resources_useful(current_time_reverse, current_resources_count, resources, resources_usetime)
                            #更新搜索禁忌表
                            change_taboo_table_reverse(resources_need, resources_useful, current_resources_count)

                        for work in locked_work:
                            if front_or_back[work] == False:
                                if i == work:
                                    if current_time_reverse == locked_work[work][0] and results_for_change_equipment_reverse[i][0] == 0:
                                        finish_work[point_table.index(i)] = True
                                        results_reverse[i][0] = current_time_reverse
                                        results_for_change_equipment_reverse[i][0] = current_time_reverse
                                        #放回资源
                                        set_current_resources_count(data, point_table.index(i), False)
                                        #更新可用资源
                                        create_resources_useful(current_time_reverse, current_resources_count, resources, resources_usetime)
                                        #更新后置工序表
                                        change_pre_process(data)
                                        #更新搜索禁忌表
                                        change_taboo_table_reverse(resources_need, resources_useful, current_resources_count)
                                #if i == work and results_for_change_equipment[i][0] != 0:
                                #    if subtime(results_for_change_equipment_reverse[i][1], current_time_reverse) == post_time[point_table.index(i)] and len(results[i]) == 1:
                                #        finish_work[point_table.index(i)] = True
                                #        finish_work[point_table.index(i)] = True
                                #        # 记录结束时间
                                #        results[i].append(change_current_time(current_time, post_time[point_table.index(i)], False))
                                #        #更新前置工序表
                                #        change_pre_process(data)
                                #        #更新搜索禁忌表
                                #        change_taboo_table(resources_need, resources_useful, current_resources_count)


                # 更新当前时间
                current_time_reverse = change_current_time(current_time_reverse, 1, False)
                #更新搜索禁忌表
                change_taboo_table_reverse(resources_need, resources_useful, current_resources_count)
                print(current_time_reverse)

                i = 0
                j = 0
                num = 0
                temp = 0
                final_work = ""
                for i in front_or_back:
                    if front_or_back[i] == False:
                        final_work = i
                        num += 1
                        if finish_work[point_table.index(i)] == False:
                            break
                for j in results_reverse:
                    temp += 1
                    if results_reverse[j][0] == 0:
                        break
                #所有倒排工序都已经被完成了，继续下一个epoch
                if num == reverse_work  and temp == len(results_reverse):
                    if final_work == "":
                        break
                    elif finish_work[point_table.index(final_work)] != False:
                        break
            
            #更新信息素
            self.__update_pheromone_graph(pheromone_graph)

            earliest_time = 0
            for work in results_reverse:
                if results_reverse[work][0] > earliest_time:
                    earliest_time = results_reverse[work][0]

            # 最后将results中最晚完成的时间作为结果时间
            current_time_reverse = earliest_time
            # 此时的current_time为完成此次遍历的current_time
            global min_current_time_reverse, min_results_reverse
            if current_time_reverse > min_current_time_reverse:
                min_current_time_reverse = current_time_reverse
                min_results_reverse = results_reverse
            
            print("迭代次数：", iter, "倒排最佳完成时间", min_current_time_reverse)

    # 更新信息素
    def __update_pheromone_graph(self, old_pheromone_graph):
        global pheromone_graph
        # 获取每只蚂蚁在其路径上留下的信息素
        temp_pheromone = [[0.0 for col in range(city_num)] for raw in range(city_num)]
        for ant in self.ants:
            for i in range(1,len(ant.path)):
                start, end = ant.path[i-1], ant.path[i]
                # 在路径上的每两个相邻城市间留下信息素，与路径总距离反比
                temp_pheromone[start][end] += Q / ant.total_distance
                temp_pheromone[end][start] = temp_pheromone[start][end]

        # 更新所有城市之间的信息素，旧信息素衰减加上新迭代信息素
        for i in range(city_num):
            for j in range(city_num):
                pheromone_graph[i][j] = old_pheromone_graph[i][j] * RHO + pheromone_graph[i][j]

       

if __name__ == '__main__':
 
    #读excel数据
    converter = data_process.ExcelToJsonConverter("s\s\ss_0.xlsx", "output.json")
    converter.convert()
    converter.convert_workline()
    converter.convert_sourcetime()
    converter.convert_lockedwork()
    converter.convert_machinechange()
    converter.convert_scheduling_strategy()
    converter.write_json()
    data = read_data("output.json")
    print (u""" 
--------------------------------------------------------
    程序：蚁群算法解决SSP问题程序 
-------------------------------------------------------- 
    """)

    SSP().search_path_front(epoch)
    SSP().search_path_reverse(epoch)
    print(min_results)
    print(min_results_reverse)
    min_results.update(min_results_reverse)
    generate_json(min_results, resources_need, point_table, "answer.json")
    print("完成")

    # 设置字体
    plt.rcParams['font.family']='Times New Roman, SimSun'
    # 绘制折线图
    #plt.plot(iter_list, results_list)

    # 添加标题和坐标轴标签
    #plt.title('result_graph')
    #plt.xlabel('iter')
    #plt.ylabel('min_result')

    # 显示图形
    #plt.show()
    draw_gantt_chart('answer.json')