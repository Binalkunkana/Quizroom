from django.db import transaction
from .models import SubmittedAnswer


@transaction.atomic
def grade_objective_answers(attempt):
    """Grade objective answers; written answers stay for faculty to grade."""
    score = 0
    has_written = False
    for answer in attempt.answers.select_related('question', 'selected_choice'):
        if answer.question.kind == 'WRITTEN':
            has_written = True
            continue
        if answer.question.kind == 'MULTI_SELECT':
            submitted = set(filter(None, answer.written_answer.split(',')))
            correct_ids = {str(pk) for pk in answer.question.choices.filter(is_correct=True).values_list('pk', flat=True)}
            correct = bool(correct_ids) and submitted == correct_ids
        elif answer.question.kind == 'BLANKS':
            expected = answer.selected_choice.text if answer.selected_choice else ''
            correct = answer.written_answer.strip().casefold() == expected.strip().casefold()
        else:
            correct = answer.selected_choice and answer.selected_choice.is_correct
        answer.awarded_points = answer.question.points if correct else 0
        answer.save(update_fields=['awarded_points'])
        score += answer.awarded_points

    attempt.score = score
    attempt.is_graded = not has_written
    attempt.save(update_fields=['score', 'is_graded'])
    return attempt
