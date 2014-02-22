# -*- coding: utf-8 *-*

from django.db import models
from django.utils.translation import ugettext_lazy as _


class Platform(models.Model):
    """
    Computer Platform
    """

    name = models.CharField(
        _("name"),
        max_length=50,
        null=True,
        blank=True,
        unique=True
    )

    def __unicode__(self):
        return self.name

    class Meta:
        app_label = 'server'
        verbose_name = _("Platform")
        verbose_name_plural = _("Platforms")
        permissions = (("can_save_platform", "Can save Platform"),)
