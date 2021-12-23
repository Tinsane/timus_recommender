import datetime
import enum
from itertools import islice
from typing import Any, Callable, Iterator, List, Optional, cast

import requests
import yarl
from bs4 import BeautifulSoup
from pydantic import BaseModel, BaseSettings


class Url(yarl.URL):
    @classmethod
    def __get_validators__(cls) -> Iterator[Callable[[Any], 'Url']]:
        yield lambda value: cls(value)

    def __truediv__(self, other: str) -> 'Url':
        return cast(Url, super().__truediv__(other))


class TimusLoaderSettings(BaseSettings):
    url: Url = Url('https://timus.online')
    problem_set_path: str = 'problemset.aspx'
    problem_path: str = 'print.aspx'
    submits_path: str = 'textstatus.aspx'

    @property
    def problem_url(self) -> Url:
        return self.url / self.problem_path

    @property
    def problem_set_url(self) -> Url:
        return self.url / self.problem_set_path

    @property
    def submits_url(self) -> Url:
        return self.url / self.submits_path

    class Config:
        env_prefix = 'TIMUS_LOADER_'


class ProblemInfo(BaseModel):
    number: int
    title: str
    difficulty: int
    solutions: int


class TimusAPIProblem(BaseModel):
    number: int
    title: str
    limits: str
    text: str

    class Config:
        frozen = True


class Verdict(str, enum.Enum):
    # Тут не полный список

    ACCEPTED = 'Accepted'
    WRONG_ANSWER = 'Wrong answer'
    MEMORY_LIMIT = 'Memory limit exceeded'
    COMPILATION_ERROR = 'Compilation error'
    TIME_LIMIT = 'Time limit exceeded'


class TimusAPISubmit(BaseModel):
    submit_id: int
    date: datetime.datetime
    author_id: int
    problem: int
    language: str
    verdict: str
    test: int
    runtime_ms: int
    memory_kb: int

    class Config:
        frozen = True


class TimusLoader:
    def __init__(self, settings: TimusLoaderSettings):
        self._settings = settings
        self._session = requests.Session()

    def get_problems(self) -> List[ProblemInfo]:
        response = self._session.get(url=self._settings.problem_set_url, params={'page': 'all'})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        table = soup.find(**{'class': 'problemset'})
        problems = []
        for content in islice(table.find_all(**{'class': 'content'}), 1, None):
            _, number, title, _, solutions, difficulty = [x.text for x in content.find_all('td')]
            problems.append(ProblemInfo(number=number, title=title, difficulty=difficulty, solutions=solutions))
        return problems

    def get_problem(self, number: int) -> TimusAPIProblem:
        response = self._session.get(url=self._settings.problem_url, params={'num': number})
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        title = soup.find(**{'class': 'problem_title'}).text
        limits = '\n'.join(soup.find(**{'class': 'problem_limits'}).get_text('<br>').split('<br>'))
        text = soup.find(id='problem_text').prettify()
        return TimusAPIProblem(number=number, title=title, limits=limits, text=text)

    def get_submits(
        self,
        *,
        author_id: Optional[int] = None,
        problem_number: Optional[int] = None,
        count: Optional[int] = None,
        from_submit_id: Optional[int] = None,
    ) -> List[TimusAPISubmit]:
        params = {}
        if from_submit_id is not None:
            params['from'] = from_submit_id
        if author_id is not None:
            params['author'] = author_id
        if problem_number is not None:
            params['num'] = problem_number
        if count is not None:
            params['count'] = count
        response = self._session.get(self._settings.submits_url, params=params)
        response.raise_for_status()
        submits = []
        for line in islice(response.text.split('\r\n'), 1, None):
            if not line:
                continue
            submit_id, date, submit_author_id, _, problem, language, verdict, test, runtime, memory = line.split('\t')
            submits.append(
                TimusAPISubmit(
                    submit_id=submit_id,
                    date=date,
                    author_id=submit_author_id,
                    problem=problem,
                    language=language,
                    verdict=verdict,
                    test=test,
                    runtime_ms=runtime,
                    memory_kb=memory,
                )
            )
        return submits
