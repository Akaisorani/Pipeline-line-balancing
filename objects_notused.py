import json

class Worker(object):
    def __init__(self, w_id, name="", skill_levels={}):
        self.id=w_id
        self.name=name
        self.skill_levels=skill_levels


class Job(object):
    def __init__(self, j_id, name="", std_time=0.0, need_machine=None, need_skill=None, count=1):
        self.id=j_id
        self.name=name
        self.std_time=std_time
        self.need_machine=need_machine
        self.need_skill=need_skill
        self.count=count


class Machine(object):
    def __init__(self, name):
        self.name=name
        self.job_list=[]

    def relate_to_job(self, job):
        self.job_list.append(job)


class Pipeline(object):
    def __init__(self, name=""):
        self.name=name

        self.components=[]

        self.machines={}

    def __str__(self):
        return str(self.to_dict())

    def __repr__(self):
        self.__str__()

    def append_components(self, component):
        self.components.append(component)

    def from_dict(self, pl):
        self.name=pl["name"]
        for component in pl["components"]:
            component_id=component["id"]
            new_component=Component(component_id, component["name"])
            for group in component["groups"]:
                group_id=group["id"]
                new_group=Group(group_id, group["name"])
                for job in group["jobs"]:
                    new_job=Job(job["id"],job["name"],job["std_time"],job["need_machine"],job["need_skill"],job["count"])
                    if job["need_machine"] not in self.machines:
                        self.machines[job["need_machine"]]=Machine(job["need_machine"])
                    self.machines[job["need_machine"]].relate_to_job(job)
                    new_group.append_job(new_job)
                new_component.append_group(new_group)
            self.append_components(new_component)


    def to_dict(self):
        pl={
            "name":self.name,
            "components":[]
        }
        for component in self.components:
            component_dic={
                "id":component.id,
                "name":component.name,
                "groups":[]
            }
            for group in component.groups:
                group_dic={
                    "id":group.id,
                    "name":group.name,
                    "jobs":[]
                }
                for job in group.jobs:
                    job_dic={
                        "id":job.id,
                        "name":job.name,
                        "count":job.count,
                        "std_time":job.std_time,
                        "need_machine":job.need_machine,
                        "need_skill":job.need_skill
                    }
                    group_dic["jobs"].append(job_dic)
                component_dic["groups"].append(group_dic)
            pl["components"].append(component_dic)
        return pl

    def to_json(self):
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_table(self):
        pass


class Component(object):
    def __init__(self, c_id, name, groups=[]):
        self.id=c_id
        self.name=name
        self.groups=groups
    
    def append_group(self, group):
        self.groups.append(group)


class Group(object):
    def __init__(self, g_id, name, jobs=[]):
        self.id=g_id
        self.name=name
        self.jobs=jobs
    
    def append_job(self, job):
        self.jobs.append(job)

        	
    

if __name__=="__main__":
    with open("pipeline_sample.json", "r") as fp:
        pl_dic=json.load(fp)
    pl=Pipeline(pl_dic["name"])
    pl.from_dict(pl_dic)
    print(pl)