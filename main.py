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
from tools.load_data import load_job_need_skills, load_rfid, load_skills_mastery, load_pipeline, load_rfid_work_overtime
from algorithms.skills_mastery import cal_skill_mastery_from_rfid, save_workers_data_to_excel, save_workers_day_mastery_to_excel
from tools.solve_MILP import MILP_solver_pulp


class Line_balancing(object):
    def __init__(self):
        self.skills=[]
        self.cfg=cfg
        self.worker_skills=None # list
        # self.worker_names=None
        self.pipeline=None  # list
        self.worker_results=None
        self.MILP_solver=MILP_solver_pulp()
        self.variable_tuples=None


    def calculate_and_save_skills_table(self):
        self.job_need_skills, self.job_skill_index=load_job_need_skills(self.cfg.job_need_skill_file)
        self.skills=list(self.job_need_skills.keys())
        # print(job_need_skills.keys())

        df_rfid=load_rfid(self.cfg.rfid_file)
        # print(df_rfid)
        day_class_overtime=load_rfid_work_overtime(self.cfg.rfid_work_overtime_file)

        self.workers_data=cal_skill_mastery_from_rfid(self.job_need_skills, self.job_skill_index, df_rfid, day_class_overtime, self.cfg)

        save_workers_data_to_excel(self.workers_data, self.cfg.worker_skills_mastery_table)
        save_workers_day_mastery_to_excel(self.workers_data, self.cfg.worker_days_mastery)

    def load_worker_skills(self, filename=None, filter=None):
        if filename is None:
            filename=self.cfg.worker_skills_mastery_table

        worker_skills, skills=load_skills_mastery(filename)   # {worker_name: {"class_name": str,"worker_name": str, "skills_mastery":{skill:mastery}}

        if filter is not None:
            del_list=[]
            for we_name, we in worker_skills.items():
                if not filter(we):
                    del_list.append(we_name)
            for we_name in del_list:
                del worker_skills[we_name]
        
        self.worker_skills=list(worker_skills.values())

        return self.worker_skills
        
    def load_pipeline(self, filename=None, cloth_name=None):
        if filename is None:
            filename=self.cfg.pipeline_file
        if cloth_name is None:
            cloth_name=self.cfg.default_cloth_name
        
        self.pipeline=load_pipeline(filename, cloth_name)   # [{"id":j_id, "component":line['部件'], "group":line['组'], "job":line['工序名称'], "need_skill":line['所需能力'], "need_machine":line['机器'], "std_time":line['SMV']*60.0}]

        return self.pipeline


    def calculate_worker_do_job_time(self):
        if self.worker_skills is None: self.load_worker_skills()
        if self.pipeline is None: self.load_pipeline()

        worker_do_job_time_table=[]
        for worker in self.worker_skills:
            new_row=[]
            worker_do_job_time_table.append(new_row)
            for job in self.pipeline:
                skill=job["need_skill"]
                if worker["skills_mastery"][skill]==0:
                    new_row.append(0.0)
                else:
                    new_row.append(job["std_time"]/worker["skills_mastery"][skill])

        # print(worker_do_job_time_table)
        self.worker_do_job_time_table=worker_do_job_time_table

        return self.worker_do_job_time_table

    def generate_and_save_constraint_matrix(self, save_constraint_file=False):

        n=len(self.pipeline)
        m=len(self.worker_skills)
        self.variable_tuples=[]
        self.variable_tuple_id_index={}
        for k in range(m):
            for i in range(0,n):
                for j in range(i,n):
                    tup=(k,i,j)
                    self.variable_tuples.append(tup)
        
        # self.variable_tuples.append("max")
        # self.variable_tuples.append("min")
        self.variable_tuples.append("avg")
        for k in range(m):
            self.variable_tuples.append(("min_self_avg", k))
            self.variable_tuples.append(("max_self_avg", k))

        
        nv=len(self.variable_tuples)  # +1 add other variable
        self.variable_tuple_id_index=dict(zip(self.variable_tuples,range(len(self.variable_tuples))))
        
 
        # follows set illegal variable to 0
        illegal_line=[0]*nv
        # # constraint 1: one person must within one component
        # for k in range(m):
        #     # line=[0.0]*nv
        #     for i in range(0,n):
        #         for j in range(i,n):
        #             tup=(k,i,j)
        #             pos=self.variable_tuple_id_index[tup]
        #             if self.pipeline[i]["component"]!=self.pipeline[j]["component"]:
        #                 illegal_line[pos]=1


        # constraint 2: group job must be assign to one person
        for k in range(m):
            # line=[0.0]*nv
            for i in range(0,n):
                for j in range(i,n):
                    tup=(k,i,j)
                    pos=self.variable_tuple_id_index[tup]
                    if (i>0 and self.pipeline[i]["group"]==self.pipeline[i-1]["group"]) or (j<n-1 and self.pipeline[j]["group"]==self.pipeline[j+1]["group"]):
                        illegal_line[pos]=1 

        # constraint 3: one person can not use more than 2 machines
        # constraint 4: one person can not do jobs with skills that he/she do not have
        for k in range(m):
            # line=[0.0]*nv
            for i in range(0,n):
                machine_set=set()
                flag=False
                for j in range(i,n):
                    tup=(k,i,j)
                    pos=self.variable_tuple_id_index[tup]

                    if flag:
                        illegal_line[pos]=1
                        continue
                    
                    if self.pipeline[j]["need_machine"] not in self.cfg.machine_not_a_machine:
                        machine_set.add(self.pipeline[j]["need_machine"])
                    if len(machine_set)>2:
                        illegal_line[pos]=1
                        flag=True
                        continue

                    if self.worker_do_job_time_table[k][j]==0:
                        illegal_line[pos]=1
                        flag=True
                        continue
        
        self.variable_tuples=[self.variable_tuples[i] for i in range(nv) if illegal_line[i]==0]
        self.variable_tuple_id_index=dict(zip(self.variable_tuples,range(len(self.variable_tuples))))
        nv=len(self.variable_tuples)

        A=[]
        b=[]
        Aeq=[]
        beq=[]

        # b_val=0
        # Aeq.append(illegal_line)
        # beq.append([b_val])

        # constraint 5: one person one range, no more than two range
        for k in range(m):
            line=[0]*nv
            for i in range(0,n):
                for j in range(i,n):
                    tup=(k,i,j)
                    if tup not in self.variable_tuple_id_index: continue
                    pos=self.variable_tuple_id_index[tup]
                    line[pos]=1
            b_val=1
            Aeq.append(line)
            beq.append([b_val])

        # constraint 6: every job has been assign to once and only once
        for job_id in range(n):
            line=[0]*nv
            for k in range(m):
                for i in range(0,job_id+1):
                    for j in range(job_id,n):
                        tup=(k,i,j)
                        if tup not in self.variable_tuple_id_index: continue
                        pos=self.variable_tuple_id_index[tup]
                        line[pos]=1
            b_val=1
            Aeq.append(line)
            beq.append([b_val])
        

        # a variable represent max work time of each person
        # aux_variable_pos=self.variable_tuple_id_index["max"]
        for k in range(m):
            line=[0.0]*nv
            # max than self and avg
            for i in range(0,n):
                temp_sum=0.0
                for j in range(i,n):
                    tup=(k,i,j)
                    temp_sum+=self.worker_do_job_time_table[k][j]
                    if tup not in self.variable_tuple_id_index: continue
                    pos=self.variable_tuple_id_index[tup]
                    line[pos]=temp_sum
            # line[self.variable_tuple_id_index["avg"]]=1
            line[self.variable_tuple_id_index[("max_self_avg", k)]]=-1
            b_val=0
            A.append(line)
            b.append([b_val])

            line=[0.0]*nv
            line[self.variable_tuple_id_index["avg"]]=1
            line[self.variable_tuple_id_index[("max_self_avg", k)]]=-1
            b_val=0
            A.append(line)
            b.append([b_val])


        # a variable represent min work time of all person
        # aux_variable_pos=self.variable_tuple_id_index["min"]
        for k in range(m):
            line=[0.0]*nv
            for i in range(0,n):
                temp_sum=0.0
                for j in range(i,n):
                    tup=(k,i,j)
                    temp_sum+=self.worker_do_job_time_table[k][j]
                    if tup not in self.variable_tuple_id_index: continue
                    pos=self.variable_tuple_id_index[tup]
                    line[pos]=-temp_sum
            # line[self.variable_tuple_id_index["avg"]]=-1
            line[self.variable_tuple_id_index[("min_self_avg", k)]]=1
            b_val=0
            A.append(line)
            b.append([b_val])

            line=[0.0]*nv
            line[self.variable_tuple_id_index["avg"]]=-1
            line[self.variable_tuple_id_index[("min_self_avg", k)]]=1
            b_val=0
            A.append(line)
            b.append([b_val])

        # a variable represent total work time of all person
        aux_variable_pos=self.variable_tuple_id_index["avg"]
        line=[0.0]*nv
        for k in range(m):
            for i in range(0,n):
                temp_sum=0.0
                for j in range(i,n):
                    tup=(k,i,j)
                    temp_sum+=self.worker_do_job_time_table[k][j]
                    if tup not in self.variable_tuple_id_index: continue
                    pos=self.variable_tuple_id_index[tup]
                    line[pos]=temp_sum/m
        line[aux_variable_pos]=-1
        b_val=0
        Aeq.append(line)
        beq.append([b_val])

        # f, optimization target
        avg_weight=0.2
        std_dev_weight=0.8
        f_line=[0.0]*nv
        f_line[self.variable_tuple_id_index["avg"]]=avg_weight
        for k in range(m):      
            f_line[self.variable_tuple_id_index[("max_self_avg",k)]]=std_dev_weight/m
            f_line[self.variable_tuple_id_index[("min_self_avg",k)]]=-std_dev_weight/m

        
        print("variable number", nv)

        if save_constraint_file:
            # save variable
            with open(self.cfg.variable_file, "w") as fp:
                json.dump(self.variable_tuples, fp)

            # save A, b, Aeq, Beq to csv
            with open(self.cfg.ILP_contraints_path+"/"+"A.csv" ,'w')as f:
                f_csv = csv.writer(f)
                f_csv.writerows(A)
            
            with open(self.cfg.ILP_contraints_path+"/"+"b.csv" ,'w')as f:
                f_csv = csv.writer(f)
                f_csv.writerows(b)

            with open(self.cfg.ILP_contraints_path+"/"+"Aeq.csv" ,'w')as f:
                f_csv = csv.writer(f)
                f_csv.writerows(Aeq)

            with open(self.cfg.ILP_contraints_path+"/"+"beq.csv" ,'w')as f:
                f_csv = csv.writer(f)
                f_csv.writerows(beq)
        
            with open(self.cfg.ILP_contraints_path+"/"+"f.csv" ,'w')as f:
                f_csv = csv.writer(f)
                f_csv.writerows([f_line])

        
        # label integer index
        self.variable_integer_label=[1 if isinstance(x, tuple) and len(x)==3 else 0 for x in self.variable_tuples]

        self.constraint=[f_line, A, b, Aeq, beq]

        return self.variable_tuples, self.variable_integer_label, self.constraint

    def load_solver_result(self, filename=None):
        if filename is None:
            filename=self.cfg.solver_result_file

        with open(filename,'r')as f:
            f_csv = csv.reader(f)
            result_mat=list(f_csv)

        result_vars=result_mat[0]
        
        result_vars=[round(float(x)) for x in result_vars]

        
        # print(len(result_vars))

        return result_vars

    
    def load_variable_tuples(self, filename=None):
        if filename is None:
            filename=self.cfg.variable_file

        with open(filename, "r") as fp:
            self.variable_tuples=json.load(fp)
        self.variable_tuples=[tuple(x) if isinstance(x, list) else x for x in self.variable_tuples]
        tot=0
        self.variable_tuple_id_index={}
        for tup in self.variable_tuples:
            self.variable_tuple_id_index[tup]=tot
            tot+=1

    def save_solution_to_excel(self, selected_tuples, filename=None):
        if filename is None:
            filename=self.cfg.line_balance_solution_file

        columns=["员工姓名","部件","机器","工序名称","工序序号","标准工时(s)", "所需能力","熟练度","预估工时(s)","个人总时间(s)","平均时间(s)","线平衡率"]

        df = pd.DataFrame(columns=columns)

        total_job_time_lis=[x["total_job_time"] for x in self.worker_results]
        avg_worker_time=sum(total_job_time_lis)/len(total_job_time_lis)
        line_balance_rate=avg_worker_time/max(total_job_time_lis)
        line={
            "平均时间(s)":avg_worker_time,
            "线平衡率":'{:.2%}'.format(line_balance_rate)
        }
        df = df.append(line, ignore_index=True)

        for k,i,j in selected_tuples:
            wr=self.worker_results[k]
            for x in range(i,j+1):
                job=self.pipeline[x]
                line={
                    "员工姓名":wr["worker_name"],
                    "部件":job["component"],
                    "机器":job["need_machine"],
                    "工序名称":job["job"],
                    "工序序号":job["id"],
                    "标准工时(s)":job["std_time"], 
                    "所需能力":job["need_skill"],
                    "熟练度":wr["skills_mastery"][job["need_skill"]],
                    "预估工时(s)":self.worker_do_job_time_table[k][x],
                    "个人总时间(s)":wr["total_job_time"] if x==i else ""
                }
                df = df.append(line, ignore_index=True)
        
        writer=pd.ExcelWriter(filename)
        df.to_excel(writer,sheet_name='Sheet1',index=0)
        workbook  = writer.book
        worksheet1 = writer.sheets['Sheet1']

        fmt = writer.book.add_format({"font_name": "Arial"})
        worksheet1.set_column(0, 100, None, fmt)
        worksheet1.set_row(0, None, fmt)

        writer.save() 
        writer.close()

    def load_context(self, worker_skills_mastery_file=None, pipeline_file=None, cloth_name=None):
        if worker_skills_mastery_file is None:
            worker_skills_mastery_file=self.cfg.worker_skills_mastery_table
        if pipeline_file is None:
            pipeline_file=self.cfg.pipeline_file
        if cloth_name is None:
            cloth_name=self.cfg.default_cloth_name

        self.load_worker_skills(worker_skills_mastery_file)
        self.load_pipeline(pipeline_file, cloth_name)

    def solve_MILP(self):
        self.result=self.MILP_solver.solve(self.variable_tuples, self.variable_integer_label, *self.constraint)

        return self.result

    def do_generate_constraint(self, save_constraint_file=False):
        self.calculate_worker_do_job_time()
        self.generate_and_save_constraint_matrix(save_constraint_file)

    def do_analyse_result(self, result_vars=None, result_filename=None, solution_filename=None):
        if result_vars is None and result_filename is None:
            result_filename=self.cfg.solver_result_file
        if solution_filename is None:
            solution_filename=self.cfg.line_balance_solution_file

        self.calculate_worker_do_job_time()

        if result_vars is None:
            result_vars=self.load_solver_result(result_filename)
        if self.variable_tuples is None:
            self.load_variable_tuples(self.cfg.variable_file)

        selected_tuples=[]
        for tup, x_var in zip(self.variable_tuples, result_vars):
            if isinstance(tup, tuple) and len(tup)==3 and x_var==1:
                selected_tuples.append(tup)
        self.selected_tuples=selected_tuples
        
        selected_tuples.sort(key=lambda x: x[1])

        print(selected_tuples)
        print(len(selected_tuples))

        self.worker_results=copy.deepcopy(self.worker_skills)
        for wr in self.worker_results:
            wr["assigned_jobs"]=[]
            wr["total_job_time"]=0.0

        for k,i,j in selected_tuples:
            wr=self.worker_results[k]
            for x in range(i,j+1):
                wr["assigned_jobs"].append(self.pipeline[x])
                wr["total_job_time"]+=self.worker_do_job_time_table[k][x]
        
        total_job_time_lis=[x["total_job_time"] for x in self.worker_results]

        line_balance_rate=(sum(total_job_time_lis)/len(total_job_time_lis))/max(total_job_time_lis)
        print("line balance rate:", line_balance_rate)

        self.save_solution_to_excel(selected_tuples, solution_filename)



    def get_line_balance(self, worker_skills_mastery_file, pipeline_file, cloth_name):
        lb.load_context(worker_skills_mastery_file, pipeline_file, cloth_name)

        lb.do_generate_constraint(save_constraint_file=True)

        # Method 1: use internal pulp solver
        lb.MILP_solver=MILP_solver_pulp()
        result=lb.solve_MILP()

        # Method 2: use matlab to solve the 0-1 ILP problem, with file A.csv, b.csv, Aeq.csv, bsq.csv, f.csv, variable.json
        # ...

        lb.do_analyse_result(result)

if __name__=="__main__":
    lb=Line_balancing()
    
    # lb.calculate_and_save_skills_table()

    lb.get_line_balance(worker_skills_mastery_file="./data/员工能力表-9班.xlsx", pipeline_file="./data/工程分析表.xlsx", cloth_name="ISC218OW010")





