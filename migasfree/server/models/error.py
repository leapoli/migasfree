# -*- coding: utf-8 -*-

from django.db import models
from django.utils.translation import ugettext_lazy as _

from . import Computer, Version, AutoCheckError

import re


class ErrorManager(models.Manager):
    def create(self, computer, version, error):
        error = Error()
        error.computer = computer
        error.version = version
        error.error = error
        error.save()

        return error


class Error(models.Model):
    computer = models.ForeignKey(
        Computer,
        verbose_name=_("computer")
    )

    date = models.DateTimeField(
        verbose_name=_("date"),
        auto_now_add=True
    )

    error = models.TextField(
        verbose_name=_("error"),
        null=True,
        blank=True
    )

    checked = models.BooleanField(
        verbose_name=_("checked"),
        default=False,
    )

    version = models.ForeignKey(
        Version,
        verbose_name=_("version")
    )

    objects = ErrorManager()

    def okay(self, *args, **kwargs):
        self.checked = True
        super(Error, self).save(*args, **kwargs)

    def truncated_error(self):
        if len(self.error) <= 250:
            return self.error
        else:
            return self.error[:250] + " ..."

    truncated_error.short_description = _("Truncated error")

    def auto_check(self):
        msg = self.error
        for ace in AutoCheckError.objects.all():
            if re.search(ace.message, msg):
                self.checked =True
                return

    def computer_link(self):
        return self.computer.link()

    computer_link.allow_tags = True
    computer_link.short_description = _("Computer")

    def save(self, *args, **kwargs):
        self.error = self.error.replace("\r\n", "\n")
        self.auto_check()
        super(Error, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'%s - %s - %s' % (
            str(self.id),
            self.computer.__unicode__(),
            str(self.date)
        )

    class Meta:
        app_label = 'server'
        verbose_name = _("Error")
        verbose_name_plural = _("Errors")
        permissions = (("can_save_error", "Can save Error"),)
