# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0030_4_17_computers'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExternalSource',
            fields=[
            ],
            options={
                'verbose_name': 'Deployment (external source)',
                'proxy': True,
                'verbose_name_plural': 'Deployments (external source)',
                'indexes': [],
            },
            bases=('server.deployment',),
        ),
        migrations.CreateModel(
            name='InternalSource',
            fields=[
            ],
            options={
                'verbose_name': 'Deployment (internal source)',
                'proxy': True,
                'verbose_name_plural': 'Deployments (internal source)',
                'indexes': [],
            },
            bases=('server.deployment',),
        ),
        migrations.AddField(
            model_name='deployment',
            name='source',
            field=models.CharField(
                choices=[(b'I', 'Internal'), (b'E', 'External')],
                default=b'I', max_length=1, verbose_name='source'
            ),
        ),
        migrations.AddField(
            model_name='deployment',
            name='base_url',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='base url'),
        ),
        migrations.AddField(
            model_name='deployment',
            name='components',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='components'),
        ),
        migrations.AddField(
            model_name='deployment',
            name='expire',
            field=models.IntegerField(
                default=1440,
                verbose_name='metadata cache minutes. Default 1440 minutes = 1 day'
            ),
        ),
        migrations.AddField(
            model_name='deployment',
            name='frozen',
            field=models.BooleanField(default=True, verbose_name='frozen'),
        ),
        migrations.AddField(
            model_name='deployment',
            name='options',
            field=models.CharField(blank=True, max_length=250, null=True, verbose_name='options'),
        ),
        migrations.AddField(
            model_name='deployment',
            name='suite',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='suite'),
        ),
    ]
