from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import json
import os, sys
import re
import copy
import requests
import urllib
from html import unescape
from lxml import html, etree
import csv



def load_worker_capability(filename):
    df=pd.read_excel(filename, sheet_name="员工技能表", keep_default_na=False, header=None)

    n, m = df.shape

    print(filename,n,m)

    # skip lines
    st=-1
    for i in range(n):
        line=df.loc[i].values.tolist()
        if line[0]=="姓名":
            st=i+1
            print("start line",st)
            break


    for i in range(st,n):
        line=df.loc[i].values.tolist()
        worker_name=line[0]
        position=line[4]
        # machine col 7~29, job col 30~
        
        end_time=line[2]
        session_id=int(line[3])
        zoom_account=line[9]
