from django.db import migrations, models
import django.db.models.deletion


def assign_questions_to_levels(apps, schema_editor):
    Question = apps.get_model("exams", "Question")
    questions = Question.objects.select_related("section__exam").order_by(
        "section__exam__level_id", "section__exam_id", "section_id", "order", "id"
    )
    next_order_by_level = {}
    for question in questions:
        level_id = question.section.exam.level_id if question.section_id else None
        if level_id is None:
            continue
        next_order_by_level[level_id] = next_order_by_level.get(level_id, 0) + 1
        question.level_id = level_id
        question.bank_order = next_order_by_level[level_id]
        question.save(update_fields=("level", "bank_order"))


class Migration(migrations.Migration):
    dependencies = [
        ("exams", "0006_exam_time_limit_minutes_alter_exam_status_question_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="bank_order",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="question",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="question",
            name="level",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="question_bank",
                to="exams.level",
            ),
        ),
        migrations.AlterField(
            model_name="question",
            name="section",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="questions",
                to="exams.examsection",
            ),
        ),
        migrations.RunPython(assign_questions_to_levels, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="question",
            constraint=models.UniqueConstraint(
                condition=models.Q(level__isnull=False, bank_order__isnull=False),
                fields=("level", "bank_order"),
                name="unique_level_question_bank_order",
            ),
        ),
    ]
