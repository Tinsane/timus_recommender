import datetime
import enum
from itertools import islice
from typing import Any, Callable, Iterator, List, Optional, cast

import requests
import yarl
from bs4 import BeautifulSoup
from pydantic import BaseModel, BaseSettings
from requests.adapters import HTTPAdapter


class Url(yarl.URL):
    @classmethod
    def __get_validators__(cls) -> Iterator[Callable[[Any], 'Url']]:
        yield lambda value: cls(value)

    def __truediv__(self, other: str) -> 'Url':
        return cast(Url, super().__truediv__(other))


class TimusClientSettings(BaseSettings):
    url: Url = Url('https://timus.online')

    max_retries: int = 3

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


class TimusAPIProblemInfo(BaseModel):
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


class ProblemModel(BaseModel):
    number: int
    title: str
    difficulty: int
    solutions: int
    limits: str
    text: str


class Verdict(str, enum.Enum):
    ACCEPTED = 'Accepted'
    CHECKER_FAILED = 'Checker failed'
    COMPILATION_ERROR = 'Compilation error'
    COMPILATION_ERROR_IDLENESS_LIMIT_EXCEEDED = 'Compilation error (idleness limit exceeded)'
    COMPILATION_ERROR_MEMORY_LIMIT_EXCEEDED = 'Compilation error (memory limit exceeded)'
    COMPILATION_ERROR_OUTPUT_LIMIT_EXCEEDED = 'Compilation error (output limit exceeded)'
    COMPILATION_ERROR_TIME_LIMIT_EXCEEDED = 'Compilation error (time limit exceeded)'
    IDLENESS_LIMIT_EXCEEDED = 'Idleness limit exceeded'
    MEMORY_LIMIT_EXCEEDED = 'Memory limit exceeded'
    OUTPUT_LIMIT_EXCEEDED = 'Output limit exceeded'
    RESTRICTED_FUNCTION = 'Restricted function'
    RUNTIME_ERROR = 'Runtime error'
    RUNTIME_ERROR_ACCESS_VIOLATION = 'Runtime error (access violation)'
    RUNTIME_ERROR_ARRAY_BOUNDS_EXCEEDED = 'Runtime error (array bounds exceeded)'
    RUNTIME_ERROR_FLOATING_POINT_DIVISION_BY_ZERO = 'Runtime error (floating-point division by zero)'
    RUNTIME_ERROR_FLOATING_POINT_INEXACT_RESULT = 'Runtime error (floating-point inexact result)'
    RUNTIME_ERROR_FLOATING_POINT_INVALID_OPERATION = 'Runtime error (floating-point invalid operation)'
    RUNTIME_ERROR_FLOATING_POINT_OVERFLOW = 'Runtime error (floating-point overflow)'
    RUNTIME_ERROR_ILLEGAL_INSTRUCTION = 'Runtime error (illegal instruction)'
    RUNTIME_ERROR_INTEGER_DIVISION_BY_ZERO = 'Runtime error (integer division by zero)'
    RUNTIME_ERROR_INTEGER_OVERFLOW = 'Runtime error (integer overflow)'
    RUNTIME_ERROR_NON_ZERO_EXIT_CODE = 'Runtime error (non-zero exit code)'
    RUNTIME_ERROR_PRIVILEGED_INSTRUCTION = 'Runtime error (privileged instruction)'
    RUNTIME_ERROR_STACK_OVERFLOW = 'Runtime error (stack overflow)'
    TIME_LIMIT_EXCEEDED = 'Time limit exceeded'
    WRONG_ANSWER = 'Wrong answer'


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


class TimusParser:
    def parse_problems(self, content: bytes) -> List[TimusAPIProblemInfo]:
        soup = BeautifulSoup(content, 'html.parser')
        table = soup.find(**{'class': 'problemset'})
        problems = []
        for table_content in islice(table.find_all(**{'class': 'content'}), 1, None):
            _, number, title, _, solutions, difficulty = [x.text for x in table_content.find_all('td')]
            problems.append(TimusAPIProblemInfo(number=number, title=title, difficulty=difficulty, solutions=solutions))
        return problems

    def parse_problem(self, content: bytes) -> TimusAPIProblem:
        soup = BeautifulSoup(content, 'html.parser')
        title = soup.find(**{'class': 'problem_title'}).text
        number, title = [x.strip() for x in title.split('.', maxsplit=1)]
        limits = '\n'.join(soup.find(**{'class': 'problem_limits'}).get_text('<br>').split('<br>'))
        text = soup.find(id='problem_text').prettify()
        return TimusAPIProblem(number=number, title=title, limits=limits, text=text)

    def parse_submits(self, content: str) -> List[TimusAPISubmit]:
        submits = []
        for line in islice(content.split('\r\n'), 1, None):
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


class TimusAPIClient:
    def __init__(self, settings: TimusClientSettings, session: requests.Session, parser: TimusParser):
        self._settings = settings
        self._session = session
        self._parser = parser

    @classmethod
    def from_settings(cls, settings: TimusClientSettings) -> 'TimusAPIClient':
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=settings.max_retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)

        return TimusAPIClient(
            settings=settings,
            session=session,
            parser=TimusParser(),
        )

    def get_problems(self) -> List[TimusAPIProblemInfo]:
        response = self._session.get(url=self._settings.problem_set_url, params={'page': 'all'})
        response.raise_for_status()
        return self._parser.parse_problems(response.content)

    def get_problem(self, number: int) -> TimusAPIProblem:
        response = self._session.get(url=self._settings.problem_url, params={'num': number})
        response.raise_for_status()
        return self._parser.parse_problem(response.content)

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

        return self._parser.parse_submits(response.text)
