from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import os, sys
import re
import copy
import csv
# from fuzzywuzzy import fuzz, process

o_path = os.getcwd()
sys.path.append(o_path)

import myconfig as cfg

temp_count=0
miss_lis=[]
def cal_skill_mastery_from_rfid(job_need_skills, job_skill_index, df_rfid, day_class_overtime, cfg=cfg):
    global temp_count
    global miss_lis
    workers_data={}
    worker_entity_template={
        "class_name":None,
        "worker_name":None,
        "rfid_log":{},   # {day:{skills:[],day_points:0}}
        "skills_mastery":{} # {skill:mastery}
    }
    # for skill in job_need_skills.keys():
    #     worker_entity_template["skills_mastery"][skill]=0

    # scan data
    n,m = df_rfid.shape
    for i in range(0,n):
        line=df_rfid.loc[i].to_dict()
        # print(line)
        # print(line["员工姓名"])
        worker_name=line["员工姓名"]
        if worker_name not in workers_data:
            workers_data[worker_name]=copy.deepcopy(worker_entity_template)
            we=workers_data[worker_name]
            we["worker_name"]=worker_name
            we["class_name"]=line["部门名称"]
        
        we=workers_data[worker_name]
        if line["单据日期"] not in we["rfid_log"]:
            we["rfid_log"][line["单据日期"]]={
                "skills":[],
                "day_points":0.0,
                "day_mastery":0
            }

        # if line["工序名称"] not in job_skill_index:
        #     skill=process.extractOne(line["工序名称"],job_skill_index.keys())[0]
        #     temp_count+=1
        #     print(temp_count)
        #     if temp_count>100: break
        # else:
        #     skill=job_skill_index[line["工序名称"]]
        # if i>1000: break
        job_name=line["工序名称"]
        if job_name not in job_skill_index:
            while job_name[-2:]=="*2":job_name=job_name[:-2]
        if job_name not in job_skill_index:
            miss_lis.append(line["工序名称"])
        if job_name in job_skill_index:
            skill=job_skill_index[job_name]
            if skill not in we["rfid_log"][line["单据日期"]]["skills"]:
                we["rfid_log"][line["单据日期"]]["skills"].append(skill)
        we["rfid_log"][line["单据日期"]]["day_points"]+=line["数量"]*line["指数"]

        if i%1000==0: print("df_rfid line",i)

    miss_lis=list(set(miss_lis))
    print(miss_lis)
    print(len(miss_lis))

    # print(workers_data["高凤娇"])
    # with open("temp_json_高凤娇.json", "w") as fp:
    #     json.dump(workers_data["高凤娇"], fp, ensure_ascii=False)

    # process day mastery
    for we_name, we in workers_data.items():
        for day_name, day in we["rfid_log"].items():
            if day["day_points"]>0:
                day_time=8
                if (day_name, we["class_name"]) in day_class_overtime:
                    day_time+=day_class_overtime[(day_name, we["class_name"])]
                    # print("triger")
                day["day_mastery"]=day["day_points"]/(100/8*day_time)

    # calculate workers skill mastery
    for we_name, we in workers_data.items():
        for skill in job_need_skills.keys():
            if skill in cfg.skill_not_cal_from_rfid:
                we["skills_mastery"][skill]=1.0
                continue
            day_mastery_lis=[]
            for day_name, day in we["rfid_log"].items():
                if skill in day["skills"]:
                    day_mastery_lis.append(day["day_mastery"])

            avg_mastery=sum(day_mastery_lis)/len(day_mastery_lis) if day_mastery_lis else 0
            we["skills_mastery"][skill]=avg_mastery
    

    return workers_data

def save_workers_data_to_excel(workers_data, filename="员工能力表.xlsx"):
    for we_name, we in workers_data.items():
        skill_lis=list(we["skills_mastery"].keys())
        break
    df = pd.DataFrame(columns=["员工姓名","部门名称"]+skill_lis)

    workers_data_lis=list(workers_data.values())
    workers_data_lis.sort(key=lambda x: x["class_name"])

    for we in workers_data_lis:
        line=copy.deepcopy(we["skills_mastery"])
        line["员工姓名"]=we["worker_name"]
        line["部门名称"]=we["class_name"]
        df = df.append(line, ignore_index=True)
    
    writer=pd.ExcelWriter(filename)
    df.to_excel(writer,sheet_name='Sheet1',index=0)
    workbook  = writer.book
    worksheet1 = writer.sheets['Sheet1']

    fmt = writer.book.add_format({"font_name": "Arial"})
    worksheet1.set_column('A:Z', None, fmt)
    worksheet1.set_row(0, None, fmt)

    writer.save() 
    writer.close() 

def save_workers_day_mastery_to_excel(workers_data, filename="员工日效率.xlsx"):
    workers_data_lis=list(workers_data.values())
    workers_data_lis.sort(key=lambda x: x["class_name"])
    all_days_name=set()
    for we in workers_data_lis:
        days_name=we["rfid_log"].keys()
        all_days_name.update(set(days_name))
    all_days_name=list(all_days_name)
    all_days_name.sort()
    # print(all_days_name)


    df = pd.DataFrame(columns=["员工姓名","部门名称"]+all_days_name)
    
    for we in workers_data_lis:
        line={}
        for day_name in all_days_name:
            if day_name in we["rfid_log"]:
                line[day_name]=we["rfid_log"][day_name]["day_mastery"]
            else:
                line[day_name]=""
        line["员工姓名"]=we["worker_name"]
        line["部门名称"]=we["class_name"]
        df = df.append(line, ignore_index=True)
    
    writer=pd.ExcelWriter(filename)
    df.to_excel(writer,sheet_name='Sheet1',index=0)
    workbook  = writer.book
    worksheet1 = writer.sheets['Sheet1']

    fmt = writer.book.add_format({"font_name": "Arial"})
    worksheet1.set_column(0,200, None, fmt)
    worksheet1.set_row(0, None, fmt)

    writer.save() 
    writer.close() 