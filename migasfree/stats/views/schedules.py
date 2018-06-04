# -*- coding: utf-8 -*-

import pygal

from datetime import timedelta, datetime

from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.utils.translation import ugettext as _

from migasfree.server.models import (
    Computer, Project, Deployment,
    Schedule, ScheduleDelay,
)
from migasfree.server.utils import time_horizon

from . import LABEL_ROTATION, DEFAULT_STYLE, JS_FILE, WIDTH, HEIGHT, BAR_STYLE


@login_required
def project_schedule_delays(request, project_name=None):
    title = _("Provided Computers / Delay")
    project_selection = Project.get_project_names()

    if project_name is None:
        return render(
            request,
            'lines.html',
            {
                'title': title,
                'project_selection': project_selection,
            }
        )

    project = get_object_or_404(Project, name=project_name)
    title += ' [{}]'.format(project.name)

    line_chart = pygal.Line(
        no_data_text=_('There are no synchronizations'),
        x_label_rotation=LABEL_ROTATION,
        legend_at_bottom=True,
        style=DEFAULT_STYLE,
        js=[JS_FILE],
        width=WIDTH,
        height=HEIGHT,
    )

    maximum_delay = 0
    for schedule in Schedule.objects.all():
        lst_attributes = []
        d = 1
        value = 0
        line = []

        delays = ScheduleDelay.objects.filter(
            schedule__name=schedule.name
        ).order_by("delay")
        for delay in delays:
            lst_att_delay = list(delay.attributes.values_list('id', flat=True))
            for i in range(d, delay.delay):
                line.append([i, value])
                d += 1

            for duration in range(0, delay.duration):
                value += Computer.productive.scope(request.user.userprofile).extra(
                    select={'deployment': 'id'},
                    where=[
                        "computer_id %% {} = {}".format(delay.duration, duration)
                    ]
                ).filter(
                    ~Q(sync_attributes__id__in=lst_attributes) &
                    Q(sync_attributes__id__in=lst_att_delay) &
                    Q(project__id=project.id)
                ).values('id').count()

                line.append([d, value])

                d += 1

            lst_attributes += lst_att_delay

        maximum_delay = max(maximum_delay, d)
        line_chart.add(schedule.name, [row[1] for row in line])

    labels = []
    for i in range(0, maximum_delay + 1):
        labels.append(_('%d days') % i)

    line_chart.x_labels = labels

    return render(
        request,
        'lines.html',
        {
            'title': title,
            'project_selection': project_selection,
            'current_project': project.name,
            'chart': line_chart.render_data_uri(),
            'tabular_data': line_chart.render_table(),
        }
    )


@login_required
def provided_computers_by_delay(request):
    deploy = get_object_or_404(Deployment, pk=request.GET.get('id'))
    rolling_date = deploy.start_date

    line_chart = pygal.Line(
        no_data_text=_('There are no data'),
        show_legend=False,
        x_label_rotation=LABEL_ROTATION,
        style=BAR_STYLE,
        js=[JS_FILE],
        width=WIDTH,
        height=HEIGHT,
    )

    available_data = []
    provided_data = []
    labels = []

    lst_attributes = []
    value = 0
    date_format = "%Y-%m-%d"
    now = datetime.now()

    delays = ScheduleDelay.objects.filter(
        schedule__id=deploy.schedule.id
    ).order_by("delay")
    len_delays = len(delays)

    for i, item in enumerate(delays):
        lst_att_delay = list(item.attributes.values_list('id', flat=True))

        start_horizon = datetime.strptime(
            str(time_horizon(rolling_date, 0)),
            date_format
        )
        if i < (len_delays - 1):
            end_horizon = datetime.strptime(
                str(time_horizon(rolling_date, delays[i + 1].delay - item.delay)),
                date_format
            )
        else:
            end_horizon = datetime.strptime(
                str(time_horizon(rolling_date, item.duration)),
                date_format
            )

        if deploy.domain:
            q_in_domain = ~Q(sync_attributes__id__in=deploy.domain.included_attributes.all())
            q_ex_domain = Q(sync_attributes__id__in=deploy.domain.excluded_attributes.all())
        else:
            q_in_domain = Q()
            q_ex_domain = Q()

        duration = 0
        for real_days in range(0, (end_horizon - start_horizon).days):
            loop_date = start_horizon + timedelta(days=real_days)
            weekday = int(loop_date.strftime("%w"))  # [0(Sunday), 6]
            if weekday not in [0, 6]:
                value += Computer.productive.scope(request.user.userprofile).extra(
                    select={'deployment': 'id'},
                    where=[
                        "computer_id %% {} = {}".format(item.duration, duration)
                    ]
                ).filter(
                    ~ Q(sync_attributes__id__in=lst_attributes) &
                    Q(sync_attributes__id__in=lst_att_delay) &
                    Q(project__id=deploy.project.id)
                ).exclude(
                    q_in_domain
                ).exclude(
                    q_ex_domain
                ).values('id').count()
                duration += 1

            labels.append(loop_date.strftime(date_format))
            provided_data.append(value)
            if loop_date <= now:
                available_data.append(value)

        lst_attributes += lst_att_delay
        rolling_date = end_horizon.date()

    line_chart.add(_('Provided'), provided_data)
    line_chart.add(_('Available'), available_data)
    line_chart.x_labels = labels

    return render(
        request,
        'includes/line_chart.html',
        {
            'chart': line_chart.render_data_uri(),
        }
    )