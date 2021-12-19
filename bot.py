#!/usr/bin/env python
# -*- coding: utf-8 -*-

import requests
import turicreate as tc
from html.parser import HTMLParser


class SubmitsParser(HTMLParser):
    def __init__(self, authorid):
        self._authorid = authorid
        self.submits = []
        self.start_parsing = False
        self.submit_row = False
        self.parse_id = False
        self.id = None
        self.parse_problem = False
        super().__init__()

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            dattrs = dict(attrs)
            if dattrs.get('class', '') == 'status':
                self.start_parsing = True
        elif not self.start_parsing:
            return

        if tag == 'tr':
            dattrs = dict(attrs)
            if dattrs.get('class', '') in {'even', 'odd'}:
                self.submit_row = True
        elif not self.submit_row:
            return

        if tag == 'td':
            dattrs = dict(attrs)
            if dattrs.get('class', '') == 'id':
                self.parse_id = True
            elif dattrs.get('class', '') == 'problem':
                self.parse_problem = True

    def handle_endtag(self, tag):
        if tag == 'table' and self.start_parsing:
            self.start_parsing = False
        if tag == 'tr' and self.submit_row:
            self.submit_row = False

    def handle_data(self, data):
        if self.parse_id:
            self.id = int(data)
            self.parse_id = False
            return
        if self.parse_problem:
            problem = int(data)
            self.submits.append((self.id, self._authorid, problem))
            self.parse_problem = False
            return


def load_author(authorid):
    from_ = None
    submits = []
    while True:
        if from_ is None:
            url = f'https://timus.online/status.aspx?author={authorid}&status=accepted&count=100'
        else:
            url = f'https://timus.online/status.aspx?author={authorid}&status=accepted&count=100&from={from_}'
        page = requests.get(url)
        parser = SubmitsParser(authorid)
        parser.feed(page.text)
        if len(parser.submits) == 0:
            return submits
        submits.extend(parser.submits)
        from_ = submits[-1][0]-1


def to_unique_submits_df(submits):
    problems = {}
    for submit in submits[::-1]:
        sub_id, author_id, problem_id = submit
        problems[problem_id] = (sub_id, author_id)
    sub_col = []
    prob_col = []
    auth_col = []
    for problem in problems:
        sub_id, author_id = problems[problem]
        sub_col.append(sub_id)
        prob_col.append(problem)
        auth_col.append(author_id)
    return tc.SFrame({'submitid': sub_col, 'authorid': auth_col, 'problemid': prob_col})


def main():
    submits = load_author(248409)
    submits.append((123123123, 248409, 1082))
    sub_df = to_unique_submits_df(submits)
    model = tc.load_model('prod_model')
    # print(model.recommend(users=[248409]))
    print(model.recommend_from_interactions(sub_df))


if __name__ == '__main__':
    main()
