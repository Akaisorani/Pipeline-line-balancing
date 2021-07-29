from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import os, sys
import re
import copy
import csv

o_path = os.getcwd()
sys.path.append(o_path)

import myconfig as cfg

def load_job_need_skills(filename):
    def parse_sheet(df):
        n,m = df.shape

        job_names=[]
        st=1
        for i in range(st,n):
            line=df.loc[i].values.tolist()
            job_name=line[0]
            if job_name not in job_names:
                job_names.append(job_name)

        return job_names

    df_lis = pd.read_excel(filename, sheet_name=None, keep_default_na=False, header=None)

    print(filename)
    job_need_skills={}
    job_skill_index={}
    for sheet_name, sheet in df_lis.items():
        # print(sheet_name)

        job_names = parse_sheet(sheet)
        job_need_skills[sheet_name]=[]
        for job_name in job_names:
            if job_name in job_skill_index:
                continue
            job_skill_index[job_name]=sheet_name
            job_need_skills[sheet_name].append(job_name)
    
    return job_need_skills, job_skill_index

def load_rfid(filename):
    # def parse_sheet(df):
    #     n,m = df.shape

    #     job_names=[]
    #     st=0
    #     for i in range(st,n):
    #         line=df.loc[i].to_dict()
    #         print(line)
    #         exit()
    #         job_name=line[0]
    #         job_names.append(job_name)

    #     return job_names

    df_lis = pd.read_excel(filename, sheet_name=None, keep_default_na=False, header=0, usecols='A, B, F, G, H, L')

    print(filename)
    df_rfid=pd.DataFrame()
    for sheet_name, sheet in df_lis.items():
        # print(sheet_name)

        # class_data = parse_sheet(sheet)
        df_rfid=pd.concat([df_rfid, sheet], ignore_index=True)
    
    return df_rfid

def load_rfid_work_overtime(filename):
    def parse_sheet(df):
        n,m = df.shape

        day_class_overtime_sheet={}
        st=0
        last_class_name="$$"
        last_work_overtime=-1
        for i in range(st,n):
            line=df.loc[i].to_dict()
            # print(line)
            
            class_name=line["うィン"]
            if not class_name: continue
            if not line["日期"]: continue
            day_str=line["日期"].strftime("%Y-%m-%d")
            
            work_overtime=line["加班時間"]
            if work_overtime=="" and class_name==last_class_name:
                work_overtime=last_work_overtime
            if work_overtime=="":
                work_overtime=0
            last_class_name=class_name
            last_work_overtime=work_overtime
            
            day_class_overtime_sheet[(day_str, class_name)]=work_overtime

        return day_class_overtime_sheet


    df_lis = pd.read_excel(filename, sheet_name=None, keep_default_na=False, header=1)

    day_class_overtime={}
    for sheet_name, sheet in df_lis.items():
        # print(sheet_name)
        day_class_overtime_sheet = parse_sheet(sheet)
        day_class_overtime.update(day_class_overtime_sheet)

    return day_class_overtime


def load_skills_mastery(filename):
    def parse_sheet(df):
        n,m = df.shape

        skills=df.columns.tolist()[2:]
        # print(skills)
        workers_data={}
        worker_entity_template={
            "class_name":None,
            "worker_name":None,
            "skills_mastery":{} # {skill:mastery}
        }

        for i in range(0,n):
            line=df.loc[i].to_dict()
            we=copy.deepcopy(worker_entity_template)
            we["class_name"]=line["部门名称"]
            we["worker_name"]=line["员工姓名"]
            for skill in skills:
                we["skills_mastery"][skill]=line[skill]
            workers_data[we["worker_name"]]=we

        return workers_data, skills

    df = pd.read_excel(filename, keep_default_na=False, header=0)
    
    print(filename)

    workers_data, skills = parse_sheet(df)

    return workers_data, skills

def load_pipeline(filename, cloth_name):
    def parse_sheet(df):
        n,m = df.shape

        pipeline=[]
        j_id=0
        for i in range(0,n):
            line=df.loc[i].to_dict()
            # print(line)
            if line['是否参与预平衡']=='N':continue
            j_id+=1
            je={
                "id":j_id,
                "component":line['部件'],
                "group":line['组'],
                "job":line['工序名称'],
                "need_skill":line['所需能力'],
                "need_machine":line['机器'],
                "std_time":line['SMV']*60.0
            }

            pipeline.append(je)

        return pipeline

    df = pd.read_excel(filename, sheet_name=cloth_name, keep_default_na=False, header=1)
    
    print(filename)

    pipeline = parse_sheet(df)

    return pipeline

if __name__=="__main__":
    # job_need_skills, job_skill_index=load_job_need_skills(cfg.job_need_skill_file)
    # print(job_need_skills.keys())

    # df_rfid=load_rfid(cfg.rfid_file)
    # print(df_rfid)

    # workers_data, skills=load_skills_mastery(cfg.worker_skills_mastery_table)
    # print(workers_data)

    # pipeline=load_pipeline(cfg.pipeline_file,"RCF214TW003")
    # print(pipeline)

    work_overtime=load_rfid_work_overtime(cfg.rfid_work_overtime_file)
    print(work_overtime)