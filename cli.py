import time
from typing import Iterable, Optional

import typer

from config import DBSettings
from loader import ProblemModel, TimusAPIClient, TimusAPISubmit, TimusClientSettings
from storage import DBSubmit, ProblemStorage, SubmitStorage

timus_loader = typer.Typer()


def load_problems() -> None:
    DBSettings().setup_db()
    timus_client = TimusAPIClient.from_settings(TimusClientSettings())
    storage = ProblemStorage()
    typer.echo("Start loading")
    with typer.progressbar(timus_client.get_problems()) as problem_meta_list:
        for problem_meta in problem_meta_list:
            problem = timus_client.get_problem(number=problem_meta.number)
            storage.create_or_update(
                ProblemModel(
                    number=problem.number,
                    title=problem_meta.title,
                    difficulty=problem_meta.difficulty,
                    solutions=problem_meta.solutions,
                    limits=problem.limits,
                    text=problem.text,
                )
            )
    typer.echo(f"Load {problem_meta_list.length} problems")


def _load_all(
    *,
    from_submit_id: Optional[int],
    batch_size: int,
    interval: float,
    last_submit: Optional[DBSubmit],
    timus_client: TimusAPIClient,
) -> Iterable[TimusAPISubmit]:
    while True:
        batch = timus_client.get_submits(from_submit_id=from_submit_id, count=batch_size)
        for submit in batch:
            if last_submit is not None and submit.submit_id == last_submit.submit_id:
                return
            yield submit
        from_submit_id = batch[-1].submit_id - 1
        if len(batch) == 0:
            return
        time.sleep(interval)


def load_submits(
    from_submit_id: Optional[int] = typer.Option(None),
    interval: float = typer.Option(0.5),
    batch_size: int = typer.Option(100),
) -> None:
    DBSettings().setup_db()

    timus_client = TimusAPIClient.from_settings(TimusClientSettings())
    storage = SubmitStorage()
    last_submit = storage.get_last_or_none()

    typer.echo("Start loading")
    total = 0
    saved = 0
    with typer.progressbar(
        _load_all(
            from_submit_id=from_submit_id,
            batch_size=batch_size,
            interval=interval,
            last_submit=last_submit,
            timus_client=timus_client,
        )
    ) as submits:
        current_batch = []
        for submit in submits:
            total += 1
            current_batch.append(submit)
            if len(current_batch) == batch_size:
                storage.batch_create(current_batch)
                saved += len(current_batch)
                submits.label = f"Last saved submit: {current_batch[-1].submit_id}"
                current_batch = []

        if current_batch:
            storage.batch_create(current_batch)
            saved += len(current_batch)
            submits.label = f"Last saved submit: {current_batch[-1].submit_id}"

    typer.echo()


if __name__ == "__main__":
    loader = typer.Typer(name='loader')
    loader.command()(load_problems)
    loader.command()(load_submits)

    timus_loader.add_typer(loader)
    timus_loader()
