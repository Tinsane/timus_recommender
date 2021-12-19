# coding: utf-8
import requests
page = requests.get('https://timus.online/textstatus.aspx?space=1&num=1231&status=accepted')
page = requests.get('https://timus.online/textstatus.aspx?space=1&num=1000&status=accepted&count=1000')
page.text[:100]
import csv
dir(csv)
from io import StringIO
f = StringIO(page.text)
reader = csv.reader(f)
reader = csv.reader(f, delimiter='\t')
rows = [row for row in reader]
len(rows)
rows[0]
rows[1]
rows[2]
rows[-1]
def get_acs(from_=None):
    if from_ is None:
        url = f'https://timus.online/textstatus.aspx?space=1&status=accepted&count=1000'
    else:
        url = f'https://timus.online/textstatus.aspx?space=1&status=accepted&count=1000&from={from_}'
    result = requests.get(url)
    reader = csv.reader(StringIO(result.text), delimiter='\t')
    rows = [row for row in reader]
    rows = rows[1:]
    SUB_ID = 0
    AUTHOR = 2
    PROBLEM = 4
    acs = [(row[SUB_ID], row[AUTHOR], row[PROBLEM]) for row in rows]
    return acs
    
acs = get_acs()
len(acs)
acs[:10]
acs[-1]
acs2 = get_acs('9210238')
acs2[0]
acs2 = get_acs(9210237)
acs2[0]
def get_acs(from_=None):
    if from_ is None:
        url = f'https://timus.online/textstatus.aspx?space=1&status=accepted&count=1000'
    else:
        url = f'https://timus.online/textstatus.aspx?space=1&status=accepted&count=1000&from={from_}'
    result = requests.get(url)
    reader = csv.reader(StringIO(result.text), delimiter='\t')
    rows = [row for row in reader]
    rows = rows[1:]
    SUB_ID = 0
    AUTHOR = 2
    PROBLEM = 4
    acs = [(row[SUB_ID], row[AUTHOR], row[PROBLEM]) for row in rows]
    acs = list(map(int, acs))
    return acs
    
acs = get_acs()
def get_acs(from_=None):
    if from_ is None:
        url = f'https://timus.online/textstatus.aspx?space=1&status=accepted&count=1000'
    else:
        url = f'https://timus.online/textstatus.aspx?space=1&status=accepted&count=1000&from={from_}'
    result = requests.get(url)
    reader = csv.reader(StringIO(result.text), delimiter='\t')
    rows = [row for row in reader]
    rows = rows[1:]
    SUB_ID = 0
    AUTHOR = 2
    PROBLEM = 4
    acs = [tuple(map(int, (row[SUB_ID], row[AUTHOR], row[PROBLEM]))) for row in rows]
    return acs
    
acs=  get_acs()
acs[0]
acs[-1]
import json
with open('acs/1.txt', 'w') as f:
    json.dump(acs, f)
    
from_ = None
while False:
    acs = get_acs(from_)
    if len(acs) == 0:
        break
    from_ = acs[-1][0]-1
    with open(f'acs/{cnt}.txt', 'w') as f:
        json.dump(acs, f)
    
cnt = 0
while True:
    acs = get_acs(from_)
    if len(acs) == 0:
        break
    from_ = acs[-1][0]-1
    with open(f'acs/{cnt}.txt', 'w') as f:
        json.dump(acs, f)
    cnt += 1
    if cnt % 100 == 0:
        print('Processing cnt: ', cnt)
        
import time
from_
from_ = None
while True:
    acs = get_acs(from_)
    if len(acs) == 0:
        break
    from_ = acs[-1][0]-1
    with open(f'acs/{cnt}.txt', 'w') as f:
        json.dump(acs, f)
    cnt += 1
    if cnt % 100 == 0:
        print('Processing cnt: ', cnt)
    time.sleep(1)
    
cnt = 0
from_ = None
while True:
    acs = get_acs(from_)
    if len(acs) == 0:
        break
    from_ = acs[-1][0]-1
    with open(f'acs/{cnt}.txt', 'w') as f:
        json.dump(acs, f)
    cnt += 1
    if cnt % 100 == 0:
        print('Processing cnt: ', cnt)
    time.sleep(1)
    
cnt
with open('acls/1.txt', 'r') as f:
    data = json.load(f)
    
with open('acs/1.txt', 'r') as f:
    data = json.load(f)
    
data
all_acs = []
for i in range(cnt):
    with open(f'acs/{i}.txt', 'r') as f:
        acs = json.load(f)
    all_acs.extend(acs)
    
len(all_acs)
all_acs[:10]
dir(csv)
with open('joined.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['submitid', 'authorid', 'problemid'])
    writer.writerows(all_acs)
    
