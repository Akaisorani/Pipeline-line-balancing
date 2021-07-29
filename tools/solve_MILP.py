from pulp import *

class MILP_solver_pulp(object):
    def __init__(self):
        pass

    def solve(self, variable_names, variable_binary_label, f, A, b, Aeq, beq):

        self.model=LpProblem("预平衡问题", LpMinimize)

        variable_names=[x if isinstance(x, str) else str(x) for x in variable_names]
        # print(sum(variable_binary_label))
        vars_all=[]
        for x, flag in zip(variable_names, variable_binary_label):
            if flag==1:
                new_var=LpVariable(x, lowBound=0, upBound=1, cat=LpBinary)
            else:
                new_var=LpVariable(x, lowBound=0, cat=LpContinuous)
            vars_all.append(new_var)

        # print(vars_all)

        self.model += lpSum([x * fc for x, fc in zip(vars_all, f) if fc!=0]), "总指标"

        t_id=0
        for line, b_val in zip(A,b):
            self.model += lpSum([x * c for x, c in zip(vars_all, line) if c!=0])<=b_val[0], "不等式约束"+str(t_id)
            t_id+=1

        t_id=0
        for line, b_val in zip(Aeq,beq):
            self.model += lpSum([x * c for x, c in zip(vars_all, line) if c!=0])==b_val[0], "等式约束"+str(t_id)
            t_id+=1

        
        # begin solve
        # solver=getSolver('PULP_CBC_CMD', timeLimit=1000, gapRel=0.05)
        # self.model.solve(solver)
        self.model.solve()

        print("求解状态:", LpStatus[self.model.status])
        # var_val_index={}
        # for v in self.model.variables():
        #     var_val_index[v.name]=v.varValue
            # print(v.name, "=", v.varValue)
        print("最优总指标 = ", value(self.model.objective))
        # print(var_val_index)
        # result=[var_val_index[var_name] for var_name in variable_names]
        result=[var.value() for var in vars_all]

        return result
        # print(self.model)
