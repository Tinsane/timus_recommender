# coding: utf-8
import requests
from html.parser import HTMLParser
class ComplexityParser(HTMLParser):
     def __init__(self):
         self._comp = None
         super().__init__()
     def handle_data(self, data):
         comp_str = 'Сложность: '
         if data.startswith(comp_str):
             self._comp = int(data[len(comp_str):])
             
page = requests.get('https://timus.online/problem.aspx?space=1&num=1000')
parser = ComplexityParser()
parser.feed(page.text)
parser._comp
class ComplexityParser(HTMLParser):
     def __init__(self):
         self._comp = None
         super().__init__()
     def handle_data(self, data):
         print(data)
         comp_str = 'Сложность: '
         if data.startswith(comp_str):
             self._comp = int(data[len(comp_str):])
             
parser = ComplexityParser()
parser.feed(page.text)
class ComplexityParser(HTMLParser):
     def __init__(self):
         self._comp = None
         super().__init__()
     def handle_data(self, data):
         comp_str = 'Difficulty: '
         if data.startswith(comp_str):
             self._comp = int(data[len(comp_str):])
             
parser = ComplexityParser()
parser.feed(page.text)
parser._comp
page = requests.get(f'https://timus.online/problem.aspx?space=1&num={num}&locale=en')
complexities = {}
import time
for num in range(1000, 2200):
    try:
        page = requests.get(f'https://timus.online/problem.aspx?space=1&num={num}&locale=en')
    except:
        continue
    parser = ComplexityParser()
    parser.feed(page.text)
    if parser._comp is not None:
        complexities[num] = parser._comp
        
complexities
len(complexities)
import csv
with open('compexities.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['problemid', 'compexity'])
    for (k, v) in complexities:
        writer.writerow([str(k), str(v)])
        
with open('compexities.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['problemid', 'compexity'])
    for k, v in complexities:
        writer.writerow([str(k), str(v)])
        
with open('compexities.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['problemid', 'compexity'])
    for k, v in complexities.items():
        writer.writerow([str(k), str(v)])
        
get_ipython().run_line_magic('ls', '')
